import hashlib
import json
import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, getdate, nowdate

from costeo_yelke.api import item_api
from costeo_yelke.roles import puede_aprobar_documentos, puede_revisar_documentos
from costeo_yelke.utils import resolver_terminos

# UOM usada en Subcontracting BOM / Purchase Order cuando un servicio de maquila se
# cobra por lote (ej. $19 por 25 confecciones) en vez de por pieza -- creada por el
# patch v0_2_6.add_lote_uom.
LOTE_UOM = "Lote"


@frappe.whitelist()
def get_costeo_list(limit: int = 50) -> list:
    """Lista de costeos con campos para el pipeline."""
    return frappe.get_list(
        "Costeo",
        fields=["name", "titulo", "cliente", "fecha", "compañia", "costeo_status", "modified"],
        order_by="modified desc",
        limit_page_length=int(limit),
        ignore_permissions=False,
    )


@frappe.whitelist()
def get_company_defaults(company: str) -> dict:
    """Centro de costos y almacenes (materia prima / trabajo en proceso) que le
    corresponden a una compañía, para preseleccionarlos solos en el Costeo sin
    pedirle al usuario que los repita en cada registro. El centro de costos usa
    el 'Default Cost Center' ya configurado en la Compañía; los almacenes se
    detectan por su nombre (los que ERPNext crea por defecto al dar de alta una
    compañía: 'Materia Prima'/'Stores' y 'Trabajo en Proceso'/'Work In Progress')."""
    if not company:
        return {"centro_de_costos": "", "almacen_materias_primas": "", "almacen_trabajo_en_proceso": ""}

    def find_warehouse(exactos, patrones):
        # 1) Nombre exacto (los que crea ERPNext al dar de alta la compañía).
        for name in exactos:
            wh = frappe.db.get_value(
                "Warehouse",
                {"company": company, "warehouse_name": name, "is_group": 0, "disabled": 0},
                "name",
            )
            if wh:
                return wh
        # 2) Nombre que CONTENGA el término: una compañía puede llamarlos
        # "Almacén de Materias Primas", "MP Planta 2", "WIP", etc. Antes sólo se
        # buscaba el nombre exacto, así que con cualquier variante el costeo quedaba
        # sin almacenes y sin forma de guardarse.
        for pat in patrones:
            wh = frappe.db.get_value(
                "Warehouse",
                {"company": company, "warehouse_name": ["like", f"%{pat}%"], "is_group": 0, "disabled": 0},
                "name",
            )
            if wh:
                return wh
        # 3) El MISMO patrón contra el nombre del documento. El campo warehouse_name se
        # puede editar después de crear el almacén sin que el documento se renombre: en
        # producción hay un "Materia Prima - YT" cuyo warehouse_name quedó en "mp", así
        # que buscando sólo por ese campo no aparecía nunca -- y el nombre del documento,
        # que sí lo delata, estaba ahí desde el principio.
        for pat in patrones:
            wh = frappe.db.get_value(
                "Warehouse",
                {"company": company, "name": ["like", f"%{pat}%"], "is_group": 0, "disabled": 0},
                "name",
            )
            if wh:
                return wh
        # Si nada coincide se regresa vacío A PROPÓSITO (en vez de tomar el primer
        # almacén que aparezca): elegir mal el almacén mueve inventario al lugar
        # equivocado. El SPA muestra los campos para capturarlos a mano.
        return ""

    cost_center = frappe.db.get_value("Company", company, "cost_center") or ""
    if not cost_center:
        # La compañía puede no tener centro de costos por defecto configurado.
        cost_center = frappe.db.get_value(
            "Cost Center", {"company": company, "is_group": 0, "disabled": 0}, "name"
        ) or ""

    return {
        "centro_de_costos": cost_center,
        "almacen_materias_primas": find_warehouse(
            ["Materia Prima", "Materias Primas", "Stores"],
            ["Materia Prima", "Materias Primas", "Stores", "Insumo", "Almacén General", "Almacen General"],
        ),
        "almacen_trabajo_en_proceso": find_warehouse(
            ["Trabajo en Proceso", "Work In Progress"],
            ["Trabajo en Proceso", "Work In Progress", "WIP", "Proceso", "Producción", "Produccion"],
        ),
    }


@frappe.whitelist()
def set_costeo_status(costeo: str, status: str) -> dict:
    """Actualiza el estatus del pipeline."""
    allowed = {"Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado", "Cancelado"}
    if status not in allowed:
        frappe.throw(_(f"Estatus inválido: {status}"))
    frappe.db.set_value("Costeo", costeo, "costeo_status", status)
    return {"ok": True, "costeo": costeo, "status": status}


def _tallas_extra_para_producto(doc, finished_item):
    """Filas de tabla_tallas_costeo de este producto que llevan sobrecosto --
    las que no tienen sobrecosto ya quedan representadas por el precio base,
    no necesitan línea aparte en la cotización."""
    return [
        t for t in doc.get("tabla_tallas_costeo", [])
        if t.finished_item == finished_item and t.sobrecosto_tipo and t.sobrecosto_tipo != "Ninguno"
    ]


def _talla_label(talla_name):
    return frappe.db.get_value("Talla", talla_name, "talla") or talla_name or ""


def _tallas_label(tallas_field):
    """`tallas_field` puede traer VARIAS tallas agrupadas separadas por coma (ej.
    "2XL,3XL", ver pantalla de Costear) -- junta la etiqueta legible de cada una
    con '/' (ej. "2XL/3XL"). Una sola talla se ve exactamente igual que antes."""
    codes = [c.strip() for c in (tallas_field or "").split(",") if c.strip()]
    return "/".join(_talla_label(c) for c in codes)


def _es_talla_pendiente(t):
    return (t.get("estado_cantidad") or "Definida") == "Pendiente por cliente"


def _sobrecosto_titulo(sobrecosto_tipo, sobrecosto_valor, material_original=None, material_alterno=None):
    if sobrecosto_tipo == "Porcentaje":
        return f"Tallas extra (+{flt(sobrecosto_valor):g}%)"
    if sobrecosto_tipo == "Material":
        orig = frappe.db.get_value("Item", material_original, "item_name") or material_original or "material estándar"
        alt = frappe.db.get_value("Item", material_alterno, "item_name") or material_alterno or "artículo alterno"
        return f"Tallas extra (cambia {orig} por {alt}, +${flt(sobrecosto_valor):,.2f} c/u)"
    return f"Tallas extra (+${flt(sobrecosto_valor):,.2f} c/u)"


def _build_talla_extra_description(base_description, sobrecosto_tipo, sobrecosto_valor, rows, material_original=None, material_alterno=None):
    """Descripción autogenerada para la línea de tallas extra: mismo producto,
    listando qué tallas llevan el sobrecosto. No exige cantidad -- lo normal
    es que al cotizar no se sepa cuántas piezas serán tallas extra, solo que
    existe el ajuste de precio; si sí se capturó cantidad por talla, se
    incluye como referencia. Si alguna fila del grupo sigue 'Pendiente por
    cliente', se avisa al final -- esa cantidad todavía no es definitiva."""
    titulo = _sobrecosto_titulo(sobrecosto_tipo, sobrecosto_valor, material_original, material_alterno)
    lineas = []
    pendiente = False
    for t in rows:
        etiqueta = " ".join(filter(None, [t.genero, _tallas_label(t.talla)]))
        if _es_talla_pendiente(t):
            pendiente = True
            sufijo = " (cantidad por confirmar)"
        else:
            sufijo = f" × {cint(t.qty)} pza(s)" if flt(t.qty) > 0 else ""
        lineas.append(f"- {etiqueta}{sufijo}")
    bloque = f"{titulo}:\n" + "\n".join(lineas)
    if pendiente:
        bloque += "\n(cantidad total sujeta a confirmación del cliente)"
    base = (base_description or "").strip()
    return f"{base}\n\n{bloque}" if base else bloque


def _venta_items_para_producto(doc, p, extra_fields=None):
    """Arma las líneas de Item (Quotation o Sales Order, misma forma en ambos)
    para un Costeo Producto: la línea base con la descripción normal, más una
    línea aparte por cada grupo de sobrecosto de talla (agrupando las que
    comparten mismo tipo/valor/material), ya que en la práctica casi nunca se
    conoce el desglose exacto de piezas por talla extra al cotizar -- solo el
    % o monto de ajuste. Si sí se captura cantidad por talla y ya está
    'Definida', esa cantidad se resta de la línea base y se usa en la línea
    extra en vez del 1 de referencia -- una talla 'Pendiente por cliente'
    NUNCA resta de la base (no se sabe todavía si ya está incluida en el
    total o es aparte) y su línea extra siempre queda en 1, de referencia.
    `extra_fields` son claves adicionales que se copian tal cual a cada línea
    generada (ej. delivery_date en Sales Order)."""
    talla_rows = _tallas_extra_para_producto(doc, p.finished_item)
    extra_fields = extra_fields or {}

    # price_list_rate se fija IGUAL a rate en cada línea a propósito: si se deja
    # que Frappe lo autocomplete, toma el precio de lista del Item (el de la línea
    # base, sin el ajuste de talla) y calcula un "descuento" = price_list_rate -
    # rate para las líneas de talla extra -- como esas llevan un rate MAYOR (es un
    # sobrecosto, no una rebaja), ese descuento sale negativo y se imprime en la
    # cotización como algo confuso que en realidad no es un descuento real.
    if not talla_rows:
        rate = p.unit_sales_price or 0
        item = {"item_code": p.finished_item, "qty": p.qty, "rate": rate, "price_list_rate": rate, **extra_fields}
        if p.description:
            item["description"] = p.description
        return [item]

    grupos = {}
    for t in talla_rows:
        key = (t.sobrecosto_tipo, flt(t.sobrecosto_valor), t.get("sobrecosto_material_original"), t.get("sobrecosto_material_alterno"))
        grupos.setdefault(key, []).append(t)

    definidas = [t for t in talla_rows if not _es_talla_pendiente(t)]
    total_talla_qty = sum(flt(t.qty) for t in definidas)
    base_qty = flt(p.qty) - total_talla_qty if total_talla_qty > 0 else flt(p.qty)

    items = []
    if base_qty > 0:
        rate = p.unit_sales_price or 0
        item = {"item_code": p.finished_item, "qty": base_qty, "rate": rate, "price_list_rate": rate, **extra_fields}
        if p.description:
            item["description"] = p.description
        items.append(item)

    for (sobrecosto_tipo, sobrecosto_valor, mat_orig, mat_alt), rows in grupos.items():
        algun_pendiente = any(_es_talla_pendiente(t) for t in rows)
        qty_grupo = sum(flt(t.qty) for t in rows)
        qty = qty_grupo if (qty_grupo > 0 and not algun_pendiente) else 1
        rate = rows[0].precio_venta or p.unit_sales_price or 0
        items.append({
            "item_code": p.finished_item,
            "qty": qty,
            "rate": rate,
            "price_list_rate": rate,
            "description": _build_talla_extra_description(p.description, sobrecosto_tipo, sobrecosto_valor, rows, mat_orig, mat_alt),
            **extra_fields,
        })

    return items


def _asegurar_articulo_alterno(original: str, alterno: str):
    """Registra 'alterno' como Artículo Alterno de 'original' (bidireccional) si
    todavía no existe -- una sola vez por par, reutilizado siempre que se repita
    la misma combinación. Es el mecanismo NATIVO de Frappe/ERPNext (Item
    Alternative), no algo propio de esta app: así el envío de material al taller
    y el consumo en producción reconocen el artículo real que se compró, sin
    pisar el BOM estándar del producto (ver sub_transferir_material y
    crear_boms_spa).

    ERPNext exige que AMBOS artículos tengan 'Permitir artículo alterno' marcado
    antes de poder registrar el par (si no, Item Alternative.validate() lo
    rechaza) -- se asegura SIEMPRE, incluso si el par ya estaba registrado (por
    si alguien lo desmarcó a mano en el Artículo después; sin esto, la
    sustitución en la transferencia seguiría fallando aunque el par ya existiera)."""
    if not original or not alterno or original == alterno:
        return
    for item_code in (original, alterno):
        if not frappe.db.get_value("Item", item_code, "allow_alternative_item"):
            frappe.db.set_value("Item", item_code, "allow_alternative_item", 1, update_modified=False)
    if frappe.db.exists("Item Alternative", {"item_code": original, "alternative_item_code": alterno}):
        return
    ia = frappe.new_doc("Item Alternative")
    ia.item_code = original
    ia.alternative_item_code = alterno
    ia.two_way = 1
    ia.flags.ignore_permissions = True
    ia.insert()


@frappe.whitelist()
def actualizar_talla_cantidad(costeo: str, talla_row: str, qty: float = 0, estado_cantidad: str = "Definida") -> dict:
    """Confirma la cantidad real de una talla que estaba 'Pendiente por cliente'
    (o corrige una ya 'Definida'). Si ya existe una Cotización y/o una Orden de
    Venta en BORRADOR ligadas a este Costeo, les reconstruye las líneas de ese
    producto para que reflejen la cantidad nueva (ver _sync_venta_items_desde_tallas).
    Los documentos ya validados NO se tocan -- se listan en 'omitidos' para que se
    maneje aparte (ej. una enmienda), ya que no se puede reescribir libremente un
    documento ya validado."""
    if estado_cantidad not in ("Definida", "Pendiente por cliente"):
        frappe.throw(_("Estado de cantidad inválido."))

    doc = frappe.get_doc("Costeo", costeo)
    row = next((t for t in doc.tabla_tallas_costeo if t.name == talla_row), None)
    if not row:
        frappe.throw(_("No se encontró esa fila de talla en este costeo."))

    row.estado_cantidad = estado_cantidad
    row.qty = flt(qty) if estado_cantidad == "Definida" else 0
    row.costo_total = flt(row.costo_unitario) * flt(row.qty)

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.save()

    sync = _sync_venta_items_desde_tallas(doc, row.finished_item)
    return {"ok": True, "estado_cantidad": row.estado_cantidad, "qty": row.qty, **sync}


def _sync_venta_items_desde_tallas(doc, finished_item: str = None) -> dict:
    """Reconstruye, para los documentos de venta EN BORRADOR ligados a este
    Costeo (Cotización y/o Orden de Venta), las líneas del producto indicado (o
    de todos si no se especifica) según el estado actual de tabla_tallas_costeo
    -- misma lógica que al crearlos (_venta_items_para_producto), así que
    cotizar/vender y luego confirmar cantidades de talla no se desincroniza.
    Los ya validados se listan en 'omitidos' sin tocarlos."""
    actualizados, omitidos = [], []
    productos = [p for p in doc.costeo_producto if not finished_item or p.finished_item == finished_item]
    if not productos:
        return {"actualizados": actualizados, "omitidos": omitidos}

    for doctype in ("Quotation", "Sales Order"):
        if not frappe.db.has_column(doctype, "costeo"):
            continue
        for name in frappe.get_all(doctype, filters={"costeo": doc.name}, pluck="name"):
            vdoc = frappe.get_doc(doctype, name)
            if vdoc.docstatus != 0:
                omitidos.append({"doctype": doctype, "name": name})
                continue
            extra_fields = {"delivery_date": vdoc.get("delivery_date")} if doctype == "Sales Order" else {}
            for p in productos:
                nuevas = _venta_items_para_producto(doc, p, extra_fields=extra_fields)
                otras = [it for it in vdoc.items if it.item_code != p.finished_item]
                vdoc.set("items", otras)
                for it in nuevas:
                    vdoc.append("items", it)
            vdoc.flags.ignore_permissions = True
            vdoc.flags.ignore_mandatory = True
            vdoc.save()
            actualizados.append({"doctype": doctype, "name": vdoc.name})
    return {"actualizados": actualizados, "omitidos": omitidos}


@frappe.whitelist()
def crear_cotizacion(
    costeo: str, valid_till=None, payment_terms_template=None, tc_name=None, custom_tipo_formato=None,
    currency=None, selling_price_list=None, taxes_and_charges=None, contact_email=None, contact_mobile=None,
) -> dict:
    """Crea una Quotation en BORRADOR desde el Costeo con los datos manuales."""
    doc = frappe.get_doc("Costeo", costeo)

    quot = frappe.new_doc("Quotation")
    quot.quotation_to = "Customer"
    quot.party_name = doc.cliente
    quot.company = doc.compañia
    quot.transaction_date = nowdate()

    if valid_till:
        quot.valid_till = valid_till
    if payment_terms_template:
        quot.payment_terms_template = payment_terms_template
    if tc_name:
        quot.tc_name = tc_name
        quot.terms = resolver_terminos(tc_name)
    if currency:
        quot.currency = currency
    if selling_price_list:
        quot.selling_price_list = selling_price_list
    if contact_email:
        quot.contact_email = contact_email
    if contact_mobile:
        quot.contact_mobile = contact_mobile
    if frappe.db.has_column("Quotation", "custom_tipo_formato"):
        quot.custom_tipo_formato = custom_tipo_formato or "Normal"

    if frappe.db.has_column("Quotation", "costeo"):
        quot.costeo = costeo

    _aplicar_impuestos_venta(quot, taxes_and_charges or _get_sales_tax_template(doc.compañia))

    for p in doc.costeo_producto:
        for item in _venta_items_para_producto(doc, p):
            quot.append("items", item)

    quot.flags.ignore_permissions = True
    quot.insert()  # queda en borrador (docstatus 0)

    frappe.db.set_value("Costeo", costeo, "costeo_status", "Cotizado")

    return {"name": quot.name, "docstatus": quot.docstatus}


@frappe.whitelist()
def materializar_producto_terminado(
    costeo: str,
    old_finished_item: str,
    item_code: str,
    item_name: str,
    stock_uom: str,
    precio_venta=None,
    item_group: str = None,
    pricing_rules=None,
    uom_conversions=None,
    description: str = None,
    image: str = None,
) -> dict:
    """Materializa el Producto Terminado de un renglón de Costeo: crea el Item (si
    item_code todavía no existe) reutilizando item_api.create_item, con su precio
    de venta y reglas de precio opcionales, y reescribe el texto libre por el
    item_code final en las 3 tablas hijas que lo correlacionan por igualdad de
    texto (costeo_producto, costeo_producto_detalle, tabla_etapas_costeo) — deben
    quedar sincronizadas o Costeo.cleanup_orphan_children() borraría en el
    siguiente guardado las filas de materiales/etapas de ese producto."""
    if isinstance(pricing_rules, str):
        pricing_rules = json.loads(pricing_rules) if pricing_rules else None
    if isinstance(uom_conversions, str):
        uom_conversions = json.loads(uom_conversions) if uom_conversions else None

    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _guess_finished_goods_warehouse

    company = frappe.db.get_value("Costeo", costeo, "compañia")
    price_list = frappe.db.get_default("selling_price_list") or "Venta estándar"
    # Almacén de PRODUCTO TERMINADO. Sin esto el Item nacía sin almacén por defecto y
    # el recibo de la última etapa de maquila lo metía donde cayera -- en la práctica,
    # al almacén de materia prima. Materiales y sub-ensamblajes ya lo resolvían así
    # (ver materializar_articulo, con almacen_materias_primas / almacen_trabajo_en_proceso);
    # el terminado no tiene campo propio en el Costeo, así que se deduce por nombre,
    # igual que hace _build_stage_subcontracting_rows al fijar el almacén destino.
    fg_warehouse = _guess_finished_goods_warehouse(company)

    if not frappe.db.exists("Item", item_code):
        item_default = {"company": company, "default_price_list": price_list}
        if fg_warehouse:
            item_default["default_warehouse"] = fg_warehouse
        payload = {
            "item_code": item_code,
            "item_name": item_name,
            "item_group": item_group or "Productos Terminados",
            "stock_uom": stock_uom,
            "is_stock_item": 1,
            "is_sales_item": 1,
            "is_purchase_item": 0,
            "include_item_in_manufacturing": 1,
            "is_sub_contracted_item": 1,
            "item_defaults": [item_default],
        }
        if description:
            payload["description"] = description
        if image:
            payload["image"] = image
        if uom_conversions:
            payload["uom_conversions"] = uom_conversions
        if precio_venta:
            payload["item_prices"] = [{"price_list": price_list, "price_list_rate": precio_venta}]
            payload["standard_rate"] = precio_venta
        if pricing_rules:
            payload["pricing_rules"] = [
                {**r, "selling": 1, "company": company, "for_price_list": price_list}
                for r in pricing_rules
            ]
        item_api.create_item(json.dumps(payload), ignore_mandatory=True)
    elif precio_venta:
        existing = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list}, "name")
        if existing:
            frappe.db.set_value("Item Price", existing, "price_list_rate", precio_venta)
        else:
            price_doc = frappe.new_doc("Item Price")
            price_doc.item_code = item_code
            price_doc.item_name = item_name
            price_doc.price_list = price_list
            price_doc.uom = stock_uom
            price_doc.price_list_rate = precio_venta
            price_doc.currency = frappe.db.get_value("Price List", price_list, "currency") or "MXN"
            price_doc.flags.ignore_permissions = True
            price_doc.insert()

    # Item que ya existía (creado desde el catálogo, importado, o de un costeo previo):
    # se le completa el almacén de producto terminado SOLO si viene vacío -- si alguien
    # ya eligió uno a propósito, no se le pisa.
    if fg_warehouse and frappe.db.exists("Item", item_code):
        fila_default = frappe.db.get_value(
            "Item Default", {"parent": item_code, "company": company}, ["name", "default_warehouse"], as_dict=True
        )
        if fila_default and not fila_default.default_warehouse:
            frappe.db.set_value("Item Default", fila_default.name, "default_warehouse", fg_warehouse)
        elif not fila_default:
            item_doc = frappe.get_doc("Item", item_code)
            item_doc.append("item_defaults", {"company": company, "default_warehouse": fg_warehouse})
            item_doc.flags.ignore_permissions = True
            item_doc.flags.ignore_mandatory = True
            item_doc.save()

    if old_finished_item and old_finished_item != item_code:
        frappe.db.set_value(
            "Costeo Producto", {"parent": costeo, "finished_item": old_finished_item}, "finished_item", item_code
        )
        frappe.db.set_value(
            "Costeo Producto Detalle",
            {"parent": costeo, "finished_item": old_finished_item},
            "finished_item",
            item_code,
        )
        frappe.db.set_value(
            "Etapas Costeo",
            {"parent": costeo, "producto_terminado": old_finished_item},
            "producto_terminado",
            item_code,
        )
        frappe.db.set_value(
            "Costeo Producto Talla",
            {"parent": costeo, "finished_item": old_finished_item},
            "finished_item",
            item_code,
        )

    frappe.db.commit()
    return {"item_code": item_code}


@frappe.whitelist()
def actualizar_cotizacion(
    name: str, valid_till=None, payment_terms_template=None, tc_name=None, custom_tipo_formato=None,
    currency=None, selling_price_list=None, taxes_and_charges=None, contact_email=None, contact_mobile=None,
    items=None,
) -> dict:
    """Actualiza los datos manuales de una cotización en borrador.

    ``items``, si se manda, reemplaza por completo la tabla de artículos (cantidad,
    precio, o artículos nuevos que no vienen del Costeo) -- si se omite, la tabla de
    artículos no se toca (compatibilidad con llamadas que solo editan encabezado)."""
    doc = frappe.get_doc("Quotation", name)
    if doc.docstatus != 0:
        frappe.throw(_("La cotización ya está validada; no se puede editar."))
    doc.valid_till = valid_till or None
    doc.payment_terms_template = payment_terms_template or None
    doc.tc_name = tc_name or None
    doc.terms = resolver_terminos(tc_name)
    doc.currency = currency or doc.currency
    doc.selling_price_list = selling_price_list or doc.selling_price_list
    _aplicar_impuestos_venta(doc, taxes_and_charges or None)
    doc.contact_email = contact_email or None
    doc.contact_mobile = contact_mobile or None
    if frappe.db.has_column("Quotation", "custom_tipo_formato"):
        doc.custom_tipo_formato = custom_tipo_formato or "Normal"

    if items is not None:
        if isinstance(items, str):
            items = json.loads(items)
        doc.items = []
        for r in items:
            if not r.get("item_code"):
                continue
            row = doc.append("items", {})
            row.item_code = r["item_code"]
            row.item_name = r.get("item_name") or r["item_code"]
            row.description = r.get("description") or ""
            row.qty = flt(r.get("qty")) or 1
            row.rate = flt(r.get("rate"))
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.run_method("set_missing_values")
        doc.run_method("calculate_taxes_and_totals")

    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def get_articulos_pendientes(costeo: str) -> dict:
    """Checklist previo a preparar_produccion: agrupa por texto libre único los
    materiales/servicios/subensamblajes de etapas que todavía no resuelven a un
    Item real. Cada grupo se resuelve una sola vez (materializar_articulo) y
    aplica a todos los renglones que comparten ese mismo texto. Incluye pistas
    (precio, UOM del proveedor, factor de conversión) ya capturadas en el
    costeo, para pre-llenar el modal de creación sin pedirle al usuario que
    las vuelva a escribir."""
    doc = frappe.get_doc("Costeo", costeo)

    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    # Operaciones por producto -- fusiona los servicios del mismo proveedor en el
    # mismo punto del flujo (ver _resolve_production_operations). El resultado que
    # hay que materializar es op.output_item (sintético cuando fusiona varias), no
    # el subensamblaje de cada fila.
    ops_por_producto = {}
    for producto in doc.costeo_producto:
        fi = producto.finished_item
        if not fi:
            continue
        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == fi]
        ops_por_producto[fi] = _resolve_production_operations(etapas_prod, fi)

    candidatos = set()
    for d in doc.costeo_producto_detalle:
        if d.concept_type == "Materia Prima" and d.item:
            candidatos.add(d.item)
    for e in doc.tabla_etapas_costeo:
        if e.servicio:
            candidatos.add(e.servicio)
    for ops in ops_por_producto.values():
        for op in ops:
            if not op.is_terminal and op.output_item:
                candidatos.add(op.output_item)

    existentes = set()
    if candidatos:
        existentes = set(frappe.get_all("Item", filters={"name": ["in", list(candidatos)]}, pluck="name"))

    grupos = {}

    def add(row_type, texto, item_group_sugerido, supplier, producto_terminado,
            unit_price=None, supplier_uom=None, internal_uom=None, conversion_factor=None):
        if not texto or texto in existentes:
            return
        g = grupos.setdefault((row_type, texto), {
            "row_type": row_type, "texto": texto, "item_group_sugerido": item_group_sugerido,
            "supplier": None, "productos": [], "unit_price": None,
            "supplier_uom": None, "internal_uom": None, "conversion_factor": None,
        })
        if supplier and not g["supplier"]:
            g["supplier"] = supplier
        if producto_terminado and producto_terminado not in g["productos"]:
            g["productos"].append(producto_terminado)
        if unit_price and not g["unit_price"]:
            g["unit_price"] = flt(unit_price)
        if supplier_uom and not g["supplier_uom"]:
            g["supplier_uom"] = supplier_uom
        if internal_uom and not g["internal_uom"]:
            g["internal_uom"] = internal_uom
        if conversion_factor and not g["conversion_factor"]:
            g["conversion_factor"] = flt(conversion_factor)

    for d in doc.costeo_producto_detalle:
        if d.concept_type == "Materia Prima":
            add("material", d.item, "Materia prima", d.supplier, d.finished_item,
                unit_price=d.unit_price, supplier_uom=d.supplier_uom,
                internal_uom=d.internal_uom, conversion_factor=d.conversion_factor)

    # Servicios: cada fila de etapa aporta un servicio que debe existir como Item,
    # sin importar cómo se agrupen después las etapas en operaciones.
    advertencias = []
    for e in doc.tabla_etapas_costeo:
        lote_qty = flt(e.lote_qty) or 1
        add(
            "servicio_etapa", e.servicio, "Servicios", e.proveedor, e.producto_terminado,
            unit_price=e.precio_servicio,
            internal_uom=e.lote_uom,
            supplier_uom=LOTE_UOM if lote_qty > 1 else None,
            conversion_factor=lote_qty if lote_qty > 1 else None,
        )

    # Sub-ensamblajes: el resultado de cada operación NO terminal (op.output_item,
    # sintético cuando fusiona varios servicios del mismo proveedor). auto_materializar
    # _subensamblajes los crea sin intervención.
    for fi, ops in ops_por_producto.items():
        for op in ops:
            if op.is_terminal:
                continue
            # Etapa única sin subensamblaje capturado -> output_item cae al producto
            # terminado, lo cual es incorrecto para una etapa intermedia.
            if len(op.member_stage_keys) == 1 and len(op.servicios) == 1 and op.output_item == fi:
                advertencias.append(
                    f'La operación "{(op.servicios[0].get("service_item") if op.servicios else "?")}" de "{fi}" '
                    "todavía no tiene sub-ensamblaje que produce -- complétalo o los BOMs no se podrán crear."
                )
            add("subensamblaje_etapa", op.output_item, "Sub-Ensamblajes", None, fi)

    return {
        "grupos": list(grupos.values()),
        "advertencias": advertencias,
        "company": doc.compañia,
        "almacen_materias_primas": doc.almacen_materias_primas or "",
        "almacen_trabajo_en_proceso": doc.almacen_trabajo_en_proceso or "",
    }


@frappe.whitelist()
def materializar_articulo(costeo: str, row_type: str, texto: str, item_code: str, prefill=None, supplier: str = None, precio: float = None, solo_vincular: bool = False) -> dict:
    """Resuelve un grupo de renglones de material/servicio/subensamblaje en texto
    libre: si item_code ya existe, solo vincula (reescribe el texto libre por el
    item_code en todos los renglones que comparten ese mismo texto); si es nuevo,
    lo crea reutilizando item_api.create_item con el 'prefill' armado en el
    frontend (mismo patrón de ProductoNuevoPage.vue), inyectando el proveedor ya
    conocido del renglón en supplier_items antes de crear. Si el prefill no trae
    item_defaults/item_prices, se completan automáticamente con la compañía,
    almacén y precio de compra ya conocidos del costeo -- para no obligar al
    usuario a repetir configuración que ya existe en el renglón.

    ``solo_vincular=True`` -- usado por "Vincular existente" del checklist de Alta
    de Productos, que NUNCA debe crear un artículo nuevo (eso es lo que hace el
    botón separado "+ Crear", con su propio modal y datos completos). Si
    ``item_code`` no existe todavía, truena en vez de crear un Item a medias con
    lo que sea que el usuario llevaba escrito -- antes, buscar "vincular existente"
    podía crear (y de una vez vincular) un artículo real con un código truncado
    apenas tecleado, con solo un par de letras."""
    if isinstance(prefill, str):
        prefill = json.loads(prefill) if prefill else {}
    prefill = dict(prefill or {})
    if isinstance(solo_vincular, str):
        solo_vincular = solo_vincular.lower() in ("1", "true", "yes")

    if solo_vincular and not frappe.db.exists("Item", item_code):
        frappe.throw(_(
            'El artículo "{0}" todavía no existe -- créalo primero con el botón "+ Crear".'
        ).format(item_code))

    field_map = {
        "material": ("Costeo Producto Detalle", "item", {"concept_type": "Materia Prima"}),
        "servicio_etapa": ("Etapas Costeo", "servicio", {}),
        "subensamblaje_etapa": ("Etapas Costeo", "subensamblaje", {}),
    }
    if row_type not in field_map:
        frappe.throw(_("Tipo de renglón desconocido: {0}").format(row_type))
    child_doctype, fieldname, extra_filters = field_map[row_type]

    if not frappe.db.exists("Item", item_code):
        prefill["item_code"] = item_code
        if supplier and not prefill.get("supplier_items"):
            prefill["supplier_items"] = [{"supplier": supplier}]

        if not prefill.get("item_defaults"):
            doc = frappe.get_doc("Costeo", costeo)
            warehouse = ""
            if row_type == "material":
                warehouse = doc.almacen_materias_primas or ""
            elif row_type == "subensamblaje_etapa":
                warehouse = doc.almacen_trabajo_en_proceso or ""
            price_list = "Compra estandar" if row_type in ("material", "servicio_etapa") else ""
            prefill["item_defaults"] = [{
                "company": doc.compañia,
                "default_warehouse": warehouse,
                "default_price_list": price_list,
            }]

        if precio and not prefill.get("item_prices"):
            price_row = {"price_list": "Compra estandar", "price_list_rate": precio}
            if supplier:
                price_row["supplier"] = supplier
            prefill["item_prices"] = [price_row]
        if precio and not prefill.get("standard_rate"):
            prefill["standard_rate"] = precio

        # Si el artículo se compra en una unidad distinta a la interna (rollos, cajas, etc.),
        # casi nunca la cantidad exacta necesaria cae en un múltiplo entero de esa unidad --
        # se compra de más. Sin tolerancia, ERPNext bloquea la OC/recibo con OverAllowanceError
        # en cuanto se redondea hacia arriba. Se deja un margen razonable por defecto.
        if prefill.get("uom_conversions") and prefill.get("over_delivery_receipt_allowance") is None:
            prefill["over_delivery_receipt_allowance"] = 20
            prefill["over_billing_allowance"] = 20

        item_api.create_item(json.dumps(prefill), ignore_mandatory=True)

    filters = {"parent": costeo, fieldname: texto}
    filters.update(extra_filters)
    frappe.db.set_value(child_doctype, filters, fieldname, item_code)

    frappe.db.commit()
    return {"item_code": item_code}


@frappe.whitelist()
def auto_materializar_subensamblajes(costeo: str) -> dict:
    """Crea automáticamente (sin checklist ni modal) un Item para cada sub-ensamblaje
    de etapa que todavía es solo texto libre. A diferencia de materiales/servicios
    (que sí requieren revisión manual -- proveedor, precio, UDM del proveedor), un
    sub-ensamblaje es un artículo interno de proceso que siempre se maneja igual: se
    produce por subcontratación y se cuenta en piezas -- no vale la pena pedir
    confirmación uno por uno. El texto libre se usa tal cual como item_code."""
    pendientes = get_articulos_pendientes(costeo)["grupos"]
    creados = []
    for g in pendientes:
        if g["row_type"] != "subensamblaje_etapa":
            continue
        item_code = g["texto"]
        materializar_articulo(
            costeo=costeo,
            row_type="subensamblaje_etapa",
            texto=item_code,
            item_code=item_code,
            prefill=json.dumps({
                "item_group": g.get("item_group_sugerido") or "Sub-Ensamblajes",
                "stock_uom": "H87 - Pieza",
                "is_stock_item": 1,
                "is_sub_contracted_item": 1,
                # Un mismo sub-ensamblaje puede alimentar varias Subcontracting Orders
                # (una por cada etapa que lo consume) contra un solo lote real recibido,
                # así que el saldo en libro puede ir negativo temporalmente sin que sea
                # un error real de inventario.
                "allow_negative_stock": 1,
            }),
        )
        creados.append(item_code)
    return {"creados": creados}


@frappe.whitelist()
def get_flujo_operaciones(costeo: str) -> dict:
    """Vista del paso "Flujo de Producción": las operaciones ya resueltas y
    agrupadas (ver _resolve_production_operations) por producto, en orden. Es una
    vista de CONFIRMACIÓN -- el orden y el agrupado salen solos de las etapas del
    costeo; lo único editable es el nombre de la pieza que produce cada operación
    intermedia y, si de plano quedó mal, de qué operación recibe.

    Cada operación:
        op_key        id estable
        titulo        nombre corto (servicio, o "N servicios")
        supplier
        servicios     [{item, precio, stage_id, no_agrupar}]  -- cada uno se factura
                      por separado; stage_id/no_agrupar son para el control de
                      "separar este servicio" (ver toggle_no_agrupar)
        recibe_de     [op_key, ...]     -- operaciones upstream, TAL CUAL se
                      capturó (sin reducción transitiva -- ver
                      _resolve_production_operations: un paso puede recibir la
                      pieza completa de varios caminos en paralelo que además se
                      alimentan entre sí, ej. un corte que reparte piezas a bordado
                      y a colocación de cinta, y el paso final recibe de AMBOS más
                      una pieza directa del corte).
        recibe_texto  resumen legible ("Materia prima" / "Corte + Tejido")
        recibe_redundantes  subconjunto de recibe_de que también es alcanzable vía
                      otro de los mismos recibe_de -- informativo, para que la UI
                      pueda avisar ("ya te llega indirecto vía X") sin borrar nada
        produce       item que produce (editable si NO es terminal)
        es_terminal   produce el producto terminado
        editable_nombre / stage_ids   -- para persistir un rename
        candidatos_recibe  [{op_key, titulo}]  -- opciones válidas de upstream

    También regresa, por producto, "materiales": la materia prima de ese producto
    con el op_key de la operación a la que está asignada ("" = automática, se
    atribuye sola al/los paso(s) sin 'recibe de' -- ver crear_boms_spa). Asignar un
    material a una operación es lo único que le da a un paso, además de lo que
    reciba de un paso anterior, su propio insumo directo (ej. botones que le
    llegan al taller de confección aparte de la pieza ya bordada que recibe)."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    doc = frappe.get_doc("Costeo", costeo)
    stage_a_op = {}          # stage_id -> op_key (para escribir recibe_de)
    productos_out = []

    # material_id -> stage_id asignado explícitamente (ver tabla_materiales_etapa).
    # Sin fila aquí = "automática": se atribuye sola al/los paso(s) que arrancan de
    # materia prima directa (ver _split_materials_by_stage/crear_boms_spa) -- no
    # hace falta elegir nada a propósito en el caso normal de un solo arranque.
    stage_por_material = {
        r.get("material_id"): r.get("stage_id")
        for r in (doc.get("tabla_materiales_etapa") or []) if r.get("material_id") and r.get("stage_id")
    }

    for producto in doc.costeo_producto:
        fi = producto.finished_item
        if not fi:
            continue
        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == fi]
        if not etapas_prod:
            continue
        from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _op_slug

        ops = _resolve_production_operations(etapas_prod, fi)
        titulo_por_key = {}
        for op in ops:
            svcs = [s["service_item"] for s in op.servicios if s.get("service_item")]
            if not svcs:
                titulo = op.supplier or "Operación"
            elif len(svcs) == 1:
                # nombre bonito del Item si existe, si no el código
                titulo = frappe.db.get_value("Item", svcs[0], "item_name") or svcs[0]
            else:
                # varios servicios: la palabra que comparten ("Bordado", "Confección")
                titulo = _op_slug(op.servicios, op.supplier).capitalize()
            titulo_por_key[op.op_key] = titulo
            for sk in op.member_stage_keys:
                stage_a_op[sk] = op.op_key

        ops_out = []
        for op in ops:
            recibe = sorted(op.upstream_keys)
            recibe_texto = "Materia prima" if not recibe else " + ".join(titulo_por_key.get(k, "?") for k in recibe)
            # op_key de los upstream elegidos que TAMBIÉN son alcanzables vía otro
            # de los mismos upstream (ver _resolve_production_operations) -- ya no
            # se quitan solos, solo se señalan para que la tarjeta pueda avisar y la
            # persona decida si de verdad quiere las dos entradas completas (un
            # camino que se une aparte) o si fue una selección de más.
            redundantes = sorted(getattr(op, "upstream_redundantes", None) or [])
            # candidatos: cualquier otra operación que NO sea descendiente de ésta
            def _es_descendiente(cand_key, de_key, visto=None):
                visto = visto or set()
                for o in ops:
                    if o.op_key == cand_key and de_key in o.upstream_keys:
                        return True
                    if o.op_key == cand_key:
                        for u in o.upstream_keys:
                            if u not in visto:
                                visto.add(u)
                                if _es_descendiente(u, de_key, visto):
                                    return True
                return False
            candidatos = [
                {"op_key": o.op_key, "titulo": titulo_por_key[o.op_key]}
                for o in ops
                if o.op_key != op.op_key and not _es_descendiente(o.op_key, op.op_key)
            ]
            ops_out.append({
                "op_key": op.op_key,
                "titulo": titulo_por_key[op.op_key],
                "n_servicios": len([s for s in op.servicios if s.get("service_item")]),
                "supplier": op.supplier,
                "servicios": [
                    {"item": s["service_item"], "precio": flt(s["price"]),
                     "stage_id": s.get("stage_id"), "no_agrupar": bool(s.get("no_agrupar"))}
                    for s in op.servicios if s.get("service_item")
                ],
                "recibe_de": recibe,
                "recibe_texto": recibe_texto,
                "recibe_redundantes": redundantes,
                "produce": op.output_item,
                "es_terminal": bool(op.is_terminal),
                "stage_ids": sorted(op.member_stage_keys),
                "candidatos_recibe": candidatos,
            })
        # Materiales directos: qué materia prima se le manda a cada paso, además de
        # lo que reciba de un paso anterior (ver crear_boms_spa -- una operación
        # puede tener las dos cosas en el mismo BOM). "op_key": "" = automática
        # (arranca sola en el/los paso(s) sin 'recibe de').
        materiales_out = []
        for d in doc.costeo_producto_detalle:
            if d.finished_item != fi or d.concept_type != "Materia Prima" or not d.item:
                continue
            sid = stage_por_material.get(d.material_id)
            materiales_out.append({
                "material_id": d.material_id,
                "item": d.item,
                "op_key": stage_a_op.get(sid, "") if sid else "",
            })

        productos_out.append({
            "finished_item": fi,
            "qty": flt(producto.qty),
            "image": producto.get("image") or "",
            "operaciones": ops_out,
            "materiales": materiales_out,
        })

    return {"productos": productos_out}


@frappe.whitelist()
def guardar_flujo_operaciones(costeo: str, cambios, materiales=None) -> dict:
    """Persiste los (pocos) cambios que permite el paso "Flujo de Producción":
    el ORDEN de los pasos, de qué operación(es) recibe cada uno, y a qué operación
    se le manda cada materia prima. El nombre de la pieza intermedia ya NO se
    edita -- se genera solo. ``cambios`` es una lista de:
        {op_key: "...", orden: 1..N, recibe_op_keys: [op_key,...] | None}

    - orden -> nueva posición (1..N) de la operación; se renumera 'etapa' en sus
                 etapas para que el orden del frontend sea el orden real. Opcional.
    - recibe_op_keys -> se EXPANDE a todas las etapas de esas operaciones upstream y
                 se escribe como 'recibe_de' (CSV) en cada etapa de esta operación
                 -- así las operaciones fusionadas siguen siendo consumidas por
                 completo. None = no tocar; [] = pasa a arrancar de materia prima.

    ``materiales`` (opcional) es una lista de {material_id: "...", op_key: "..."} --
    a qué operación se le manda cada materia prima además de lo que reciba de un
    paso anterior. op_key = "" quita la asignación (vuelve a automática: se
    atribuye sola al/los paso(s) que arrancan de materia prima directa)."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    if isinstance(cambios, str):
        cambios = json.loads(cambios)
    if isinstance(materiales, str):
        materiales = json.loads(materiales) if materiales else None
    doc = frappe.get_doc("Costeo", costeo)
    por_stage = {e.get("stage_id"): e for e in doc.tabla_etapas_costeo if e.get("stage_id")}

    # op_key -> [stage_ids] de esa operación (para expandir 'recibe' y ubicar dónde escribir)
    op_stages = {}
    for producto in doc.costeo_producto:
        if not producto.finished_item:
            continue
        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == producto.finished_item]
        for op in _resolve_production_operations(etapas_prod, producto.finished_item):
            op_stages[op.op_key] = sorted(op.member_stage_keys)

    tocado = False
    # 'etapa' se renumera: todas las etapas de la operación en posición N toman "N".
    # (El orden REAL lo manda 'recibe_de' vía el orden topológico; esto solo mantiene
    # el número coherente con la vista y sirve de respaldo en modo lineal.)
    ordenados = sorted((c for c in (cambios or []) if c.get("orden")), key=lambda c: c["orden"])
    for pos, c in enumerate(ordenados, start=1):
        for sid in op_stages.get(c.get("op_key"), []):
            e = por_stage.get(sid)
            if e is not None and (e.etapa or "") != str(pos):
                e.etapa = str(pos)
                tocado = True

    for c in cambios or []:
        sids = op_stages.get(c.get("op_key"), [])
        recibe = c.get("recibe_op_keys")
        recibe_expandido = None
        if recibe is not None:
            expand = []
            for k in recibe:
                expand += op_stages.get(k, [k])
            recibe_expandido = ",".join(dict.fromkeys(expand))
        for sid in sids:
            e = por_stage.get(sid)
            if not e:
                continue
            if recibe_expandido is not None and (e.recibe_de or "") != recibe_expandido:
                e.recibe_de = recibe_expandido
                tocado = True

    if materiales is not None:
        mat_qty = {d.material_id: flt(d.internal_qty) for d in doc.costeo_producto_detalle if d.material_id}
        existentes = {r.material_id: r for r in doc.tabla_materiales_etapa if r.material_id}
        for m in materiales:
            mid = m.get("material_id")
            if not mid:
                continue
            op_key = m.get("op_key") or None
            # Cualquier etapa miembro de la operación sirve -- _split_materials_by_stage
            # solo necesita que el stage_id caiga dentro de member_stage_keys de esa
            # operación para que crear_boms_spa la incluya en su BOM.
            sids = op_stages.get(op_key, []) if op_key else []
            target_sid = sids[0] if sids else None
            row = existentes.get(mid)
            if not target_sid:
                if row:
                    doc.tabla_materiales_etapa.remove(row)
                    tocado = True
            elif row:
                if row.stage_id != target_sid or flt(row.qty) != mat_qty.get(mid, 0):
                    row.stage_id = target_sid
                    row.qty = mat_qty.get(mid, 0)
                    tocado = True
            else:
                doc.append("tabla_materiales_etapa", {"material_id": mid, "stage_id": target_sid, "qty": mat_qty.get(mid, 0)})
                tocado = True

    if tocado:
        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()
    return {"ok": True, "guardado": tocado}


@frappe.whitelist()
def toggle_no_agrupar(costeo: str, stage_id: str, no_agrupar) -> dict:
    """Marca/desmarca 'no_agrupar' (ver doctype Etapas Costeo) en UNA etapa
    específica, identificada por su stage_id -- y regresa el flujo ya recalculado
    para que el SPA solo tenga que reemplazar lo que tenía en pantalla.

    Por default, dos servicios del mismo proveedor que reciben exactamente del
    mismo origen se fusionan solos en un único bloque (ver
    _resolve_production_operations, "paralelas: mismo proveedor + mismo origen").
    Esto le da a la persona una salida directa desde Flujo de Producción para
    decidir, caso por caso, que UN servicio en particular no se fusione con sus
    hermanos -- por ejemplo, si al planear el costeo no se sabía todavía que ese
    servicio en la práctica se entrega por separado. Los demás servicios del
    mismo proveedor, si siguen sin marcar, se acomodan solos entre ellos como
    siempre -- esto no apaga la fusión automática en general, solo saca a este
    servicio de ella."""
    if not frappe.db.exists("Etapas Costeo", {"parent": costeo, "stage_id": stage_id}):
        frappe.throw(_("No se encontró esa etapa en el costeo."))
    frappe.db.set_value(
        "Etapas Costeo", {"parent": costeo, "stage_id": stage_id},
        "no_agrupar", 1 if cint(no_agrupar) else 0, update_modified=False,
    )
    frappe.db.commit()
    return get_flujo_operaciones(costeo)


@frappe.whitelist()
def set_tipo_formato_cotizacion(name: str, custom_tipo_formato: str) -> dict:
    """Cambia solo la vista de impresión (Normal/Volumen) de una cotización en
    borrador, sin tocar el resto de sus campos -- para refrescar la vista previa
    al instante sin exigir guardar primero el resto de los cambios pendientes."""
    if frappe.db.get_value("Quotation", name, "docstatus") != 0:
        frappe.throw(_("La cotización ya está validada; no se puede editar."))
    if frappe.db.has_column("Quotation", "custom_tipo_formato"):
        frappe.db.set_value("Quotation", name, "custom_tipo_formato", custom_tipo_formato or "Normal")
        frappe.db.commit()
    return {"name": name}


@frappe.whitelist()
def validar_documento(doctype: str, name: str) -> dict:
    """Valida (submit) un documento en borrador.

    - Costeo (esquema Simple: Enviar -> Aprobador): exige el rol 'Aprobador de
      Documentos Yelke' (o System Manager).
    - Purchase Order (esquema Doble: Enviar -> Revisor -> Aprobador -- aplica
      igual a materia prima y a subcontratada, ambas son este mismo doctype):
      exige el mismo rol de Aprobador Y que ya se haya marcado la revisión
      intermedia (ver marcar_revisado_documento).
    - Los demás doctypes que también pasan por aquí (Production Plan, Sales
      Invoice, Purchase Receipt, etc.) siguen con la validación normal, sin
      gating por rol."""
    if doctype == "Costeo" and not puede_aprobar_documentos():
        frappe.throw(
            _("No tienes permiso para validar este Costeo -- se requiere el rol 'Aprobador de Documentos Yelke'."),
            frappe.PermissionError,
        )
    if doctype == "Purchase Order":
        if not puede_aprobar_documentos():
            frappe.throw(
                _("No tienes permiso para validar esta Orden de Compra -- se requiere el rol 'Aprobador de Documentos Yelke'."),
                frappe.PermissionError,
            )
        if not frappe.db.get_value("Purchase Order", name, "revisado_yelke"):
            frappe.throw(
                _("Esta Orden de Compra necesita revisión antes de poder validarse -- pide a alguien con el rol 'Revisor de Documentos Yelke' que la revise primero.")
            )
    doc = frappe.get_doc(doctype, name)
    doc.flags.ignore_permissions = True
    doc.submit()
    if doctype == "Sales Invoice" and frappe.db.has_column("Sales Invoice", "overhead_journal_entry"):
        _contabilizar_overhead_factura(doc)
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def marcar_revisado_documento(doctype: str, name: str) -> dict:
    """Marca la verificación intermedia del esquema Doble (hoy solo Purchase
    Order -- materia prima y subcontratada) -- paso previo obligatorio a
    validar_documento para los doctypes que lo requieren."""
    if not frappe.get_meta(doctype).has_field("revisado_yelke"):
        frappe.throw(_("Este tipo de documento no usa doble validación."))
    if not puede_revisar_documentos():
        frappe.throw(
            _("No tienes permiso para revisar este documento -- se requiere el rol 'Revisor de Documentos Yelke'."),
            frappe.PermissionError,
        )
    docstatus = frappe.db.get_value(doctype, name, "docstatus")
    if docstatus != 0:
        frappe.throw(_("El documento ya está validado o cancelado; no se puede revisar."))
    frappe.db.set_value(doctype, name, {
        "revisado_yelke": 1,
        "revisado_por_yelke": frappe.session.user,
        "revisado_en_yelke": frappe.utils.now(),
    }, update_modified=False)
    return {"ok": True, "revisado_por_yelke": frappe.session.user}


@frappe.whitelist()
def puede_validar_costeo():
    """Si el usuario actual puede validar un Costeo (rol 'Aprobador de Documentos
    Yelke' o System Manager) -- el SPA lo usa para deshabilitar el botón 'Validar'
    con una explicación en vez de dejar que truene al hacer clic."""
    return {"puede": puede_aprobar_documentos()}


@frappe.whitelist()
def get_permisos_validacion_yelke():
    """Roles del usuario actual frente al motor de validación (Simple y Doble) --
    para que el SPA deshabilite/explique los botones de Revisar/Validar antes de
    que el backend los rechace."""
    return {"puede_revisar": puede_revisar_documentos(), "puede_aprobar": puede_aprobar_documentos()}


def _contabilizar_overhead_factura(si_doc):
    """Al validar la factura de venta, registra el overhead absorbido como póliza
    contable (ver _crear_poliza_overhead_venta) -- una sola vez por factura."""
    if si_doc.get("overhead_journal_entry"):
        return
    so_name = next((it.sales_order for it in si_doc.items if it.get("sales_order")), None)
    costeo = frappe.db.get_value("Sales Order", so_name, "costeo") if so_name else None
    if not costeo:
        return
    je_name = _crear_poliza_overhead_venta(si_doc, costeo)
    if je_name:
        frappe.db.set_value("Sales Invoice", si_doc.name, "overhead_journal_entry", je_name)


@frappe.whitelist()
def get_default_print_format(doctype: str) -> dict:
    """Formato de impresión PREDETERMINADO configurado para el doctype (o 'Standard')."""
    fmt = frappe.get_meta(doctype).default_print_format
    return {"format": fmt or "Standard"}


def _marcar_costeo_cancelado_si_aplica(quotation_doc):
    """Al cancelar de verdad una cotización (docstatus 1 -> 2), el proyecto se da por
    terminado -- refleja esto en costeo_status sin tocar el docstatus del Costeo (sigue
    validado; "Editar Costeo" es lo que después lo revive vía crear_revision_costeo, que
    ya deja costeo_status='Borrador'). No aplica si el Costeo ya no está vivo (docstatus
    != 1) -- por ejemplo si ya se reemplazó por una revisión."""
    costeo = quotation_doc.get("costeo")
    if not costeo:
        return
    if frappe.db.get_value("Costeo", costeo, "docstatus") == 1:
        frappe.db.set_value("Costeo", costeo, "costeo_status", "Cancelado", update_modified=False)


@frappe.whitelist()
def cancelar_documento(doctype: str, name: str) -> dict:
    """Cancela un documento validado (docstatus 1 -> 2). Paso previo para poder eliminarlo."""
    doc = frappe.get_doc(doctype, name)
    if doc.docstatus == 1:
        doc.flags.ignore_permissions = True
        doc.cancel()
        if doctype == "Quotation":
            _marcar_costeo_cancelado_si_aplica(doc)
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def crear_revision_costeo(costeo: str, motivo: str = None) -> dict:
    """Crea una nueva revisión (borrador) de un Costeo ya validado o cancelado, enlazada
    a través de amended_from -- el original queda intacto como historial, igual que el
    amend nativo de Frappe. Necesario porque un Costeo validado (docstatus=1) queda
    bloqueado para edición directa; esta es la vía para ajustarlo tras un rechazo."""
    doc = frappe.get_doc("Costeo", costeo)
    if doc.docstatus == 1:
        doc.flags.ignore_permissions = True
        # Quotation/Sales Order que ya se generaron desde este costeo deben SEGUIR
        # apuntando a él aunque quede cancelado -- así el historial de trazabilidad
        # (quién generó qué) no se pierde. Sin esto, Frappe bloquea el cancel con
        # LinkExistsError en cuanto existe una cotización u orden de venta enlazada.
        doc.ignore_linked_doctypes = ["Quotation", "Sales Order"]
        doc.cancel()
    elif doc.docstatus != 2:
        frappe.throw(_("Solo se puede crear una revisión de un costeo validado o cancelado."))

    nuevo = frappe.copy_doc(doc)
    nuevo.amended_from = doc.name
    nuevo.docstatus = 0
    nuevo.costeo_status = "Borrador"
    nuevo.motivo_revision = motivo or None
    nuevo.flags.ignore_permissions = True
    nuevo.insert()
    frappe.db.commit()
    return {"name": nuevo.name}


@frappe.whitelist()
def get_revisiones_costeo(costeo: str) -> dict:
    """Devuelve la cadena de revisiones de un Costeo: la anterior (si esto es una
    revisión) y la siguiente (si ya se creó una revisión posterior de este)."""
    doc = frappe.db.get_value("Costeo", costeo, ["amended_from", "motivo_revision"], as_dict=True)
    siguiente = frappe.db.get_value("Costeo", {"amended_from": costeo}, "name")
    return {
        "anterior": doc.amended_from if doc else None,
        "motivo_revision": doc.motivo_revision if doc else None,
        "siguiente": siguiente,
    }


@frappe.whitelist()
def asignar_documento(doctype: str, name: str, assign_to: str, description: str = None) -> dict:
    """Asigna un documento a uno o más usuarios (ToDo), como en ERPNext."""
    from frappe.desk.form.assign_to import add

    users = [u.strip() for u in (assign_to or "").replace(";", ",").split(",") if u.strip()]
    if not users:
        frappe.throw(_("Indica al menos un usuario."))

    add({
        "assign_to": users,
        "doctype": doctype,
        "name": name,
        "description": description or f"{doctype} {name}",
    })
    return {"ok": True, "assigned_to": users}


@frappe.whitelist()
def get_cotizacion_defaults(company: str = None) -> dict:
    """Opciones para los campos manuales de la cotización/orden de venta."""
    payment_terms = frappe.get_all("Payment Terms Template", fields=["name"], order_by="name asc")
    terms = frappe.get_all("Terms and Conditions", fields=["name"], order_by="name asc")
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit=50,
    )
    price_lists = frappe.get_all(
        "Price List", fields=["name", "currency"], filters={"selling": 1, "enabled": 1}, order_by="name asc"
    )
    currencies = frappe.get_all("Currency", fields=["name"], filters={"enabled": 1}, order_by="name asc", limit=50)
    tax_filters = {}
    if company:
        tax_filters["company"] = company
    tax_templates = frappe.get_all(
        "Sales Taxes and Charges Template", fields=["name"], filters=tax_filters, order_by="name asc"
    )
    return {
        "payment_terms_templates": payment_terms, "terms": terms, "users": users,
        "price_lists": price_lists, "currencies": currencies, "tax_templates": tax_templates,
    }


@frappe.whitelist()
def crear_orden_venta(
    costeo: str, delivery_date=None, payment_terms_template=None, tc_name=None,
    po_no=None, currency=None, selling_price_list=None, taxes_and_charges=None,
    contact_email=None, contact_mobile=None,
) -> dict:
    """Crea una Sales Order en BORRADOR desde el Costeo con los datos manuales."""
    doc = frappe.get_doc("Costeo", costeo)

    deliv = delivery_date or nowdate()

    so = frappe.new_doc("Sales Order")
    so.customer = doc.cliente
    so.company = doc.compañia
    so.delivery_date = deliv
    if payment_terms_template:
        so.payment_terms_template = payment_terms_template
    if tc_name:
        so.tc_name = tc_name
        so.terms = resolver_terminos(tc_name)
    if po_no:
        so.po_no = po_no
    if currency:
        so.currency = currency
    if selling_price_list:
        so.selling_price_list = selling_price_list
    if contact_email:
        so.contact_email = contact_email
    if contact_mobile:
        so.contact_mobile = contact_mobile

    if frappe.db.has_column("Sales Order", "costeo"):
        so.costeo = costeo

    _aplicar_impuestos_venta(so, taxes_and_charges or _get_sales_tax_template(doc.compañia))

    for p in doc.costeo_producto:
        for item in _venta_items_para_producto(doc, p, extra_fields={"delivery_date": deliv}):
            so.append("items", item)

    so.flags.ignore_permissions = True
    so.insert()  # queda en borrador (docstatus 0)

    frappe.db.set_value("Costeo", costeo, "costeo_status", "Orden de Venta")

    return {"name": so.name, "docstatus": so.docstatus}


@frappe.whitelist()
def actualizar_orden_venta(
    name: str, delivery_date=None, payment_terms_template=None, tc_name=None,
    po_no=None, currency=None, selling_price_list=None, taxes_and_charges=None,
    contact_email=None, contact_mobile=None,
) -> dict:
    """Actualiza los datos manuales de una orden de venta en borrador."""
    doc = frappe.get_doc("Sales Order", name)
    if doc.docstatus != 0:
        frappe.throw(_("La orden de venta ya está validada; no se puede editar."))
    if delivery_date:
        doc.delivery_date = delivery_date
        for it in doc.items:
            it.delivery_date = delivery_date
    doc.payment_terms_template = payment_terms_template or None
    doc.tc_name = tc_name or None
    doc.terms = resolver_terminos(tc_name)
    doc.po_no = po_no or None
    doc.currency = currency or doc.currency
    doc.selling_price_list = selling_price_list or doc.selling_price_list
    _aplicar_impuestos_venta(doc, taxes_and_charges or None)
    doc.contact_email = contact_email or None
    doc.contact_mobile = contact_mobile or None
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def produccion_completa(costeo: str, sales_order: str = None) -> dict:
    """True si TODAS las OC de subcontratación del costeo (o de la OV activa, si se
    manda ``sales_order``) están 100% cubiertas por Subcontracting Order(es) validadas
    -- puede haber VARIAS por OC (una por lote, producción escalonada) -- y CADA una de
    esas SCO ya tiene su Subcontracting Receipt validado (producto terminado recibido).
    Desbloquea la facturación solo al terminar TODOS los lotes, no solo el primero.

    ``sales_order``, si se manda, filtra a solo las OC de maquila etiquetadas con esa
    OV (ver plan_crear_subcontratacion) -- así "Ir a facturar" para una OV específica no
    espera a que termine la producción de OTRA OV del mismo costeo.

    Además de `total`/`recibidas` (a nivel de OC, para compatibilidad), devuelve
    `lotes_total`/`lotes_recibidos` (a nivel de SCO/lote individual, para mostrar
    avance parcial en el frontend, ej. "2 de 3 lotes recibidos") y `pct_recibido`:
    el % de avance real de la maquila, ponderado por el IMPORTE de cada etapa
    (`grand_total` de su OC) y por la CANTIDAD efectivamente recibida en cada una
    (no por "OCs completas" ni por "lotes creados") -- así una etapa cara pesa más
    que una barata, un producto con 2+ etapas subcontratadas no marca 100% en
    cuanto la ÚLTIMA etapa recibe si las anteriores representan la mayor parte del
    costo, y el avance sube suave lote a lote conforme se reciben (escalonado),
    igual que `materiaPrimaPct` en el frontend."""
    out = {"complete": False, "total": 0, "recibidas": 0, "lotes_total": 0, "lotes_recibidos": 0, "pct_recibido": 0}
    if not frappe.db.has_column("Purchase Order", "costeo"):
        return out
    po_filters = {"costeo": costeo, "is_subcontracted": 1, "docstatus": ["<", 2]}
    if sales_order:
        so_po_names = list(dict.fromkeys(frappe.get_all(
            "Purchase Order Item", filters={"sales_order": sales_order}, pluck="parent"
        )))
        po_filters["name"] = ["in", so_po_names or [""]]
    sub_pos = frappe.get_all(
        "Purchase Order",
        filters=po_filters,
        fields=["name", "docstatus", "grand_total"],
    )
    out["total"] = len(sub_pos)
    if not sub_pos:
        return out
    recibidas = 0
    valor_total = sum(flt(po.grand_total) for po in sub_pos)
    valor_recibido = 0.0
    for po in sub_pos:
        if po.docstatus != 1:
            continue  # OC de subcontratación sin validar → esa etapa no está lista

        # Una OC agrupa varias etapas del mismo proveedor en líneas separadas (ver
        # _create_subcontracting_pos_from_stages). Se agrupan por fg_item: líneas con
        # el MISMO fg_item son la misma pieza repartida entre varios servicios (sus
        # cantidades se SUMAN); fg_item DISTINTO son piezas distintas (se toma el
        # MÍNIMO entre ellas -- un lote combinado no puede pasar de la más corta).
        po_items = frappe.get_all(
            "Purchase Order Item", filters={"parent": po.name}, fields=["name", "fg_item", "fg_item_qty", "qty"]
        )
        if not po_items:
            continue
        # fg_item -> {po_item_names, qty_total}
        fg_grupos = {}
        poi_a_fg = {}
        for r in po_items:
            fg = r.fg_item or r.name
            poi_a_fg[r.name] = fg
            g = fg_grupos.setdefault(fg, {"pois": set(), "qty": 0.0})
            g["pois"].add(r.name)
            g["qty"] += flt(r.fg_item_qty) or flt(r.qty)
        po_qty = min((g["qty"] for g in fg_grupos.values()), default=0)

        scos = frappe.get_all(
            "Subcontracting Order", filters={"purchase_order": po.name, "docstatus": 1}, fields=["name"]
        )
        if not scos:
            continue
        out["lotes_total"] += len(scos)
        sco_names = [s.name for s in scos]

        sco_qty_por_fg = {fg: 0.0 for fg in fg_grupos}
        for r in frappe.get_all(
            "Subcontracting Order Item", filters={"parent": ["in", sco_names]}, fields=["purchase_order_item", "qty"]
        ):
            fg = poi_a_fg.get(r.purchase_order_item)
            if fg in sco_qty_por_fg:
                sco_qty_por_fg[fg] += flt(r.qty)
        sco_qty_total = min(sco_qty_por_fg.values(), default=0)

        scr_rows = frappe.db.sql(
            """select sri.subcontracting_order as sco, sri.purchase_order_item as poi, sum(sri.qty) as qty
               from `tabSubcontracting Receipt Item` sri
               inner join `tabSubcontracting Receipt` sr on sr.name = sri.parent
               where sri.subcontracting_order in %(scos)s and sr.docstatus = 1
               group by sri.subcontracting_order, sri.purchase_order_item""",
            {"scos": sco_names},
            as_dict=True,
        )
        recibido_por_sco = {}
        for r in scr_rows:
            fg = poi_a_fg.get(r.poi)
            if fg is None:
                continue
            recibido_por_sco.setdefault(r.sco, {}).setdefault(fg, 0.0)
            recibido_por_sco[r.sco][fg] += flt(r.qty)

        # Un LOTE (SCO) cuenta como "recibido" solo si TODAS sus piezas ya tienen
        # recibo -- un recibo parcial no debe marcar ese lote como completo.
        todas_recibidas = True
        qty_recibida = 0.0
        for sco in scos:
            por_fg = recibido_por_sco.get(sco.name, {})
            recibido_de_este_sco = min((por_fg.get(fg, 0.0) for fg in fg_grupos), default=0.0)
            if recibido_de_este_sco > 0:
                out["lotes_recibidos"] += 1
                qty_recibida += recibido_de_este_sco
            else:
                todas_recibidas = False

        if po_qty:
            valor_recibido += flt(po.grand_total) * min(qty_recibida / po_qty, 1.0)

        # Solo cuenta como OC "recibida" si YA se crearon todos los lotes que cubren el
        # 100% de la cantidad Y todos tienen su recibo -- si aún falta crear un lote no
        # debe reportarse como completa aunque los que existen ya estén recibidos.
        if todas_recibidas and sco_qty_total + 0.001 >= po_qty:
            recibidas += 1
    out["recibidas"] = recibidas
    out["complete"] = out["total"] > 0 and recibidas == out["total"]
    out["pct_recibido"] = round((valor_recibido / valor_total) * 100) if valor_total else 0
    return out


@frappe.whitelist()
def crear_factura_venta(costeo: str, posting_date=None, payment_terms_template=None, tc_name=None, due_date=None, sales_order=None) -> dict:
    """Crea una Factura de Venta (Sales Invoice) en BORRADOR desde la Orden de Venta del costeo.

    ``sales_order``, si se manda, es la OV activa elegida en el SPA -- si un Costeo
    tiene varias OV validadas (réplicas de un pedido recurrente), sin esto se elegía
    una de forma ambigua (sin orden definido)."""
    so_name = None
    if sales_order and frappe.db.get_value("Sales Order", sales_order, "docstatus") == 1 and frappe.db.get_value("Sales Order", sales_order, "costeo") == costeo:
        so_name = sales_order
    elif frappe.db.has_column("Sales Order", "costeo"):
        so_name = frappe.db.get_value("Sales Order", {"costeo": costeo, "docstatus": 1}, "name")
    if not so_name:
        frappe.throw(_("No hay una orden de venta validada para facturar."))

    existing = frappe.db.get_value(
        "Sales Invoice Item", {"sales_order": so_name, "docstatus": ["<", 2]}, "parent"
    )
    if existing:
        return {"name": existing}

    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
    si = make_sales_invoice(so_name)
    if posting_date:
        si.set_posting_time = 1
        si.posting_date = posting_date
    if due_date:
        si.due_date = due_date
    if payment_terms_template:
        si.payment_terms_template = payment_terms_template
    if tc_name:
        si.tc_name = tc_name
        si.terms = resolver_terminos(tc_name)
    if frappe.db.has_column("Sales Invoice", "costeo"):
        si.costeo = costeo
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    frappe.db.set_value("Costeo", costeo, "costeo_status", "Completado")
    return {"name": si.name, "docstatus": si.docstatus}


@frappe.whitelist()
def actualizar_factura_venta(name: str, posting_date=None, payment_terms_template=None, tc_name=None, due_date=None) -> dict:
    """Actualiza los datos manuales de una factura de venta en borrador."""
    doc = frappe.get_doc("Sales Invoice", name)
    if doc.docstatus != 0:
        frappe.throw(_("La factura ya está validada; no se puede editar."))
    if posting_date:
        doc.set_posting_time = 1
        doc.posting_date = posting_date
    if due_date:
        doc.due_date = due_date
    doc.payment_terms_template = payment_terms_template or None
    doc.tc_name = tc_name or None
    doc.terms = resolver_terminos(tc_name)
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


# =============================================================================
# NOTA DE REMISIÓN (Delivery Note): entrega física al cliente. Obligatoria antes de
# facturar: libera el inventario y genera el Costo de Ventas real de la venta.
# =============================================================================

def _stock_warehouse_for(item_code, company):
    """Almacén con más existencia disponible para un ítem (para pre-llenar la remisión
    con el almacén donde realmente está el producto terminado)."""
    row = frappe.db.get_value(
        "Bin", {"item_code": item_code, "actual_qty": [">", 0]},
        ["warehouse", "actual_qty"], order_by="actual_qty desc", as_dict=True,
    )
    return row.warehouse if row else None


@frappe.whitelist()
def crear_remision(costeo: str, posting_date=None, shipping_address_name=None, items=None, sales_order=None) -> dict:
    """Crea una Nota de Remisión (Delivery Note) en BORRADOR desde la Orden de Venta
    validada del costeo, por el SALDO PENDIENTE de entrega (o una porción de él si se
    pasa `items`). Se puede llamar varias veces mientras quede saldo -- para dividir el
    envío entre varias ubicaciones del cliente, cada remisión con su propia dirección.

    `items` (opcional): lista de {"item_code", "qty"} con la cantidad a incluir en ESTA
    remisión por producto (<= saldo pendiente de esa línea); si se omite, se remisiona
    todo el saldo pendiente (comportamiento nativo de ERPNext).

    ``sales_order``, si se manda, es la OV activa elegida en el SPA -- ver misma nota
    en crear_factura_venta."""
    so_name = None
    if sales_order and frappe.db.get_value("Sales Order", sales_order, "docstatus") == 1 and frappe.db.get_value("Sales Order", sales_order, "costeo") == costeo:
        so_name = sales_order
    elif frappe.db.has_column("Sales Order", "costeo"):
        so_name = frappe.db.get_value("Sales Order", {"costeo": costeo, "docstatus": 1}, "name")
    if not so_name:
        frappe.throw(_("No hay una orden de venta validada para remisionar."))

    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
    dn = make_delivery_note(so_name)
    if not dn.get("items"):
        frappe.throw(_("La orden de venta ya está completamente remisionada."))

    if items:
        rows = json.loads(items) if isinstance(items, str) else items
        qty_by_item = {r.get("item_code"): flt(r.get("qty")) for r in rows if r.get("item_code")}
        kept = []
        for it in dn.items:
            if it.item_code not in qty_by_item:
                continue
            solicitado = qty_by_item[it.item_code]
            if solicitado <= 0:
                continue
            if solicitado > flt(it.qty) + 0.001:
                frappe.throw(_(
                    "La cantidad para {0} ({1}) excede el saldo pendiente de entrega ({2})."
                ).format(it.item_code, solicitado, it.qty))
            it.qty = solicitado
            kept.append(it)
        if not kept:
            frappe.throw(_("Indica al menos una cantidad a remisionar."))
        dn.set("items", kept)

    if posting_date:
        dn.set_posting_time = 1
        dn.posting_date = posting_date
    if shipping_address_name:
        dn.shipping_address_name = shipping_address_name
    for it in dn.items:
        if not it.warehouse or flt(frappe.db.get_value("Bin", {"item_code": it.item_code, "warehouse": it.warehouse}, "actual_qty")) < flt(it.qty):
            wh = _stock_warehouse_for(it.item_code, dn.company)
            if wh:
                it.warehouse = wh
    # Respaldo: si la plantilla de impuestos copiada no trae 'mexico_tax_type' (obligatorio
    # para CFDI), lo infiere del nombre de la cuenta/tipo (IVA/ISR/IEPS).
    if frappe.db.has_column("Sales Taxes and Charges", "mexico_tax_type"):
        tax_types = set(frappe.get_all("Tax Type", pluck="name"))
        for t in dn.get("taxes") or []:
            if not t.get("mexico_tax_type") and tax_types:
                text = f"{t.account_head or ''} {t.description or ''}".upper()
                match = next((tt for tt in tax_types if tt.upper() in text), None)
                if match:
                    t.mexico_tax_type = match
    if frappe.db.has_column("Delivery Note", "costeo"):
        dn.costeo = costeo
    dn.flags.ignore_permissions = True
    dn.flags.ignore_mandatory = True
    dn.insert()
    return {"name": dn.name, "docstatus": dn.docstatus}


@frappe.whitelist()
def get_remision(name: str) -> dict:
    """Detalle de la remisión para la vista editable (almacén y cantidad por línea,
    dirección de envío/facturación)."""
    doc = frappe.get_doc("Delivery Note", name)
    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.status,
        "customer": doc.customer,
        "customer_name": frappe.db.get_value("Customer", doc.customer, "nombre_comercial") or doc.customer_name,
        "posting_date": str(doc.posting_date) if doc.posting_date else "",
        "grand_total": doc.grand_total,
        "customer_address": doc.customer_address or "",
        "shipping_address_name": doc.shipping_address_name or "",
        "shipping_address": doc.shipping_address or "",
        "contact_email": doc.get("contact_email") or "",
        "contact_mobile": doc.get("contact_mobile") or "",
        "flete_proveedor": doc.get("flete_proveedor") or "",
        "flete_costo": doc.get("flete_costo") or 0,
        "flete_journal_entry": doc.get("flete_journal_entry") or "",
        "address_options": _party_links("Address", doc.customer, link_doctype="Customer"),
        "items": [
            {
                "name": r.name, "item_code": r.item_code, "item_name": r.item_name,
                "qty": r.qty, "uom": r.uom, "warehouse": r.warehouse,
                "available": flt(frappe.db.get_value("Bin", {"item_code": r.item_code, "warehouse": r.warehouse}, "actual_qty")),
            }
            for r in (doc.items or [])
        ],
        "warehouses": frappe.get_all(
            "Warehouse", filters={"company": doc.company, "is_group": 0, "disabled": 0},
            fields=["name", "warehouse_name"], order_by="name asc",
        ),
    }


@frappe.whitelist()
def actualizar_remision(name: str, posting_date=None, items=None, shipping_address_name=None, customer_address=None,
                         flete_proveedor=None, flete_costo=None) -> dict:
    """Actualiza fecha, almacén y cantidad de las líneas, y direcciones de envío/facturación
    de una remisión en borrador -- el cliente a veces recibe en una dirección distinta a la
    de facturación."""
    doc = frappe.get_doc("Delivery Note", name)
    if doc.docstatus != 0:
        frappe.throw(_("La remisión ya está validada; no se puede editar."))
    if posting_date:
        doc.set_posting_time = 1
        doc.posting_date = posting_date
    if shipping_address_name is not None:
        doc.shipping_address_name = shipping_address_name or None
    if customer_address is not None:
        doc.customer_address = customer_address or None
    if flete_proveedor is not None:
        doc.flete_proveedor = flete_proveedor or None
    if flete_costo is not None:
        doc.flete_costo = flt(flete_costo)
    if items is not None:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows}
        for it in doc.items:
            r = by_name.get(it.name)
            if not r:
                continue
            if r.get("qty") is not None:
                it.qty = flt(r.get("qty"))
            if r.get("warehouse"):
                it.warehouse = r.get("warehouse")
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


def _payable_account_para_proveedor(company, proveedor):
    """Cuenta por pagar a usar en la póliza de flete: primero la cuenta específica del
    proveedor si la tiene configurada (Párty Account); si no, la cuenta genérica de
    'Cuentas por pagar proveedores' del catálogo -- a propósito NO se usa
    Company.default_payable_account como último recurso porque en este sitio esa
    default apunta a una cuenta ajena (pólizas de seguro, de otro negocio que comparte
    el mismo Frappe) y sería contablemente incorrecto usarla aquí."""
    specific = frappe.db.get_value(
        "Party Account", {"parenttype": "Supplier", "parent": proveedor, "company": company}, "account"
    )
    if specific:
        return specific
    generic = frappe.get_cached_value(
        "Account", {"account_name": "CUENTAS POR PAGAR PROVEEDORES", "company": company}, "name"
    )
    if generic:
        return generic
    frappe.throw(_(
        "No se encontró una cuenta por pagar para {0} ni la cuenta genérica de proveedores "
        "para {1}. Configura la cuenta del proveedor o la cuenta 'Cuentas por pagar proveedores'."
    ).format(proveedor, company))


def _crear_poliza_flete_remision(doc):
    """Registra el costo de envío al cliente como póliza contable: cargo a Fletes y
    Transportes (gasto de distribución) contra la cuenta por pagar del proveedor de
    transporte. No se puede meter el flete a la tabla de impuestos de la remisión porque
    la app de CFDI exige clasificar cada renglón como IVA/ISR/IEPS (mexico_tax_type
    obligatorio) y un flete no es un impuesto."""
    monto = flt(doc.get("flete_costo"))
    proveedor = doc.get("flete_proveedor")
    if monto <= 0 or not proveedor:
        return None

    flete_account = frappe.get_cached_value(
        "Account", {"account_name": "TRANSPORTE Y FLETES", "company": doc.company}, "name"
    )
    if not flete_account:
        frappe.throw(_("No se encontró la cuenta 'TRANSPORTE Y FLETES' para la compañía {0}.").format(doc.company))
    payable_account = _payable_account_para_proveedor(doc.company, proveedor)
    cost_center = frappe.get_cached_value("Company", doc.company, "cost_center")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = doc.company
    je.posting_date = doc.posting_date
    je.user_remark = _("Flete de envío al cliente — Remisión {0}").format(doc.name)
    je.append("accounts", {
        "account": flete_account,
        "debit_in_account_currency": monto,
        "cost_center": cost_center,
    })
    je.append("accounts", {
        "account": payable_account,
        "credit_in_account_currency": monto,
        "party_type": "Supplier",
        "party": proveedor,
        "cost_center": cost_center,
    })
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    return je.name


def _overhead_pct_promedio(doc):
    """% de overhead FIJO promedio (ponderado por costo) capturado en el paso Costear --
    misma fórmula que usa get_reporte_final para el estimado; si se toca una, tocar la otra."""
    est_costo_total = 0.0
    est_overhead_total = 0.0
    for p in doc.costeo_producto:
        qty = flt(p.qty)
        est_costo_total += flt(p.total_unit_cost) * qty
        est_overhead_total += flt(p.overhead_amt) * qty
    base_sin_overhead = est_costo_total - est_overhead_total
    return (est_overhead_total / base_sin_overhead * 100) if base_sin_overhead > 0 else 0


def _costo_directo_real(costeo):
    """Suma de todo el costo real ya validado del costeo: OC de materiales (+ su flete),
    OC/SCO de subcontratación (+ fletes ida/regreso al taller), flete de entrega al
    cliente -- misma fórmula que usa get_reporte_final para 'costo_directo'; si se toca
    una, tocar la otra."""
    material_directo_real = 0.0
    flete_materiales_real = 0.0
    for po in frappe.get_all("Purchase Order", filters={"costeo": costeo, "is_subcontracted": 0, "docstatus": 1}, pluck="name"):
        po_doc = frappe.get_doc("Purchase Order", po)
        flete_materiales_real += _get_shipping_row_amount(po_doc)
        for it in po_doc.items:
            material_directo_real += flt(it.amount)

    servicio_directo_real = 0.0
    flete_taller_ida_real = 0.0
    flete_taller_regreso_real = 0.0
    for po in frappe.get_all("Purchase Order", filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": 1}, pluck="name"):
        po_doc = frappe.get_doc("Purchase Order", po)
        for it in po_doc.items:
            servicio_directo_real += flt(it.amount)
        for sco in frappe.get_all("Subcontracting Order", filters={"purchase_order": po, "docstatus": 1}, pluck="name"):
            sco_doc = frappe.get_doc("Subcontracting Order", sco)
            for c in sco_doc.additional_costs:
                flete_taller_ida_real += flt(c.amount)
            for se in frappe.get_all(
                "Stock Entry",
                filters={"subcontracting_order": sco, "purpose": "Send to Subcontractor", "docstatus": 1},
                pluck="name",
            ):
                se_doc = frappe.get_doc("Stock Entry", se)
                for c in se_doc.additional_costs:
                    flete_taller_ida_real += flt(c.amount)
            scr_names = list(dict.fromkeys(
                frappe.get_all("Subcontracting Receipt Item", filters={"subcontracting_order": sco}, pluck="parent")
            ))
            for scr_name in scr_names:
                if frappe.db.get_value("Subcontracting Receipt", scr_name, "docstatus") != 1:
                    continue
                scr_doc = frappe.get_doc("Subcontracting Receipt", scr_name)
                for c in scr_doc.additional_costs:
                    flete_taller_regreso_real += flt(c.amount)

    flete_cliente_real = flt(frappe.db.sql(
        "select coalesce(sum(flete_costo), 0) from `tabDelivery Note` where costeo=%s and docstatus=1", costeo,
    )[0][0])

    return (
        material_directo_real + flete_materiales_real
        + servicio_directo_real + flete_taller_ida_real + flete_taller_regreso_real
        + flete_cliente_real
    )


def _crear_poliza_overhead_venta(si_doc, costeo):
    """Registra el overhead (nóminas, luz, internet, renta -- indirectos que contabilidad
    fija como % aparte, ver Costeo Producto.overhead_pct) absorbido por esta venta como
    póliza contable: cargo a Costo de Ventas, abono a Gastos Indirectos Absorbidos. El
    gasto real de nómina/luz/renta ya se registra aparte por sus propias pólizas/facturas
    de compra -- esta póliza solo reclasifica, como costo de venta, la porción que le
    corresponde a ESTA venta según el mismo % y costo real que ya se muestran en el
    Reporte final (ver _overhead_pct_promedio/_costo_directo_real)."""
    doc = frappe.get_doc("Costeo", costeo)
    overhead_pct = _overhead_pct_promedio(doc)
    if not overhead_pct:
        return None
    monto = flt(_costo_directo_real(costeo) * (overhead_pct / 100))
    if monto <= 0:
        return None

    # La cuenta de costo de ventas de cada compañía no siempre se llama igual
    # (ej. "COSTO DE VENTAS" en SUS INDUSTRIAL vs "Costo sobre ventas" en YELKE
    # TEXTILES) -- se usa la que la propia Compañía ya tiene configurada como su
    # cuenta de gastos default, en vez de buscar un nombre literal fijo que solo
    # coincidía por casualidad con el catálogo de una compañía en particular.
    costo_venta_account = frappe.get_cached_value("Company", si_doc.company, "default_expense_account") or \
        frappe.get_cached_value("Account", {"account_name": "COSTO DE VENTAS", "company": si_doc.company}, "name")
    if not costo_venta_account:
        frappe.throw(_(
            "No hay una cuenta de costo de ventas configurada para la compañía {0} "
            "(revisa 'Cuenta de gastos default' en la Compañía)."
        ).format(si_doc.company))
    overhead_account = frappe.get_cached_value(
        "Account", {"account_name": "GASTOS INDIRECTOS ABSORBIDOS", "company": si_doc.company}, "name"
    )
    if not overhead_account:
        frappe.throw(_(
            "No se encontró la cuenta 'GASTOS INDIRECTOS ABSORBIDOS' para la compañía {0}. "
            "Créala en el catálogo de cuentas (tipo Gasto, de preferencia bajo el mismo grupo "
            "que 'COSTO DE VENTAS') para poder registrar el overhead de esta factura."
        ).format(si_doc.company))
    cost_center = frappe.get_cached_value("Company", si_doc.company, "cost_center")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = si_doc.company
    je.posting_date = si_doc.posting_date
    je.user_remark = _("Overhead absorbido — Factura de venta {0} ({1}% de costo directo real)").format(
        si_doc.name, round(overhead_pct, 1)
    )
    je.append("accounts", {
        "account": costo_venta_account,
        "debit_in_account_currency": monto,
        "cost_center": cost_center,
    })
    je.append("accounts", {
        "account": overhead_account,
        "credit_in_account_currency": monto,
        "cost_center": cost_center,
    })
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    return je.name


@frappe.whitelist()
def validar_remision(name: str) -> dict:
    """Valida (submit) la remisión: libera el producto terminado del inventario, genera
    el costo de venta real, registra el flete al cliente (si se capturó) como póliza
    contable, y -- solo si la Orden de Venta queda completamente entregada (puede haber
    varias remisiones parciales) -- marca el costeo como 'Entregado'."""
    doc = frappe.get_doc("Delivery Note", name)
    doc.flags.ignore_permissions = True
    doc.submit()
    je_name = _crear_poliza_flete_remision(doc)
    if je_name:
        frappe.db.set_value("Delivery Note", doc.name, "flete_journal_entry", je_name)
    costeo = doc.get("costeo")
    if costeo and frappe.db.exists("Costeo", costeo):
        so_name = doc.items[0].against_sales_order if doc.items else None
        per_delivered = flt(frappe.db.get_value("Sales Order", so_name, "per_delivered")) if so_name else 100
        if per_delivered >= 99.99:
            frappe.db.set_value("Costeo", costeo, "costeo_status", "Entregado")
    return {"name": doc.name, "docstatus": doc.docstatus, "flete_journal_entry": je_name}


# =============================================================================
# FACTURAS DE COMPRA (cuentas por pagar): materiales (desde Recibo) y maquila (desde OC)
# =============================================================================

def _pinv_for(field, value):
    """Factura de compra (no cancelada) ligada a un documento origen vía Purchase Invoice Item."""
    parent = frappe.db.get_value("Purchase Invoice Item", {field: value, "docstatus": ["<", 2]}, "parent")
    if not parent:
        return None
    return frappe.db.get_value(
        "Purchase Invoice", parent,
        ["name", "docstatus", "status", "base_net_total", "grand_total", "currency", "bill_no"],
        as_dict=True,
    )


@frappe.whitelist()
def get_facturas_compra(costeo: str) -> dict:
    """Fuentes facturables de compra del costeo, con su factura si ya existe.
    Materiales → desde el Recibo de compra. Maquila → desde la OC de subcontratación."""
    materiales, maquila = [], []
    if not frappe.db.has_column("Purchase Order", "costeo"):
        return {"materiales": materiales, "maquila": maquila}

    mat_pos = frappe.get_all(
        "Purchase Order", filters={"costeo": costeo, "is_subcontracted": 0, "docstatus": 1}, pluck="name"
    )
    rec_names = list(dict.fromkeys(
        frappe.get_all("Purchase Receipt Item", filters={"purchase_order": ["in", mat_pos]}, pluck="parent")
    )) if mat_pos else []
    for r in rec_names:
        rd = frappe.db.get_value(
            "Purchase Receipt", r,
            ["name", "supplier", "supplier_name", "base_net_total", "grand_total", "docstatus", "status"],
            as_dict=True,
        )
        if not rd or rd.docstatus != 1:
            continue
        rd["source_doctype"] = "Purchase Receipt"
        rd["invoice"] = _pinv_for("purchase_receipt", r)
        materiales.append(rd)

    sub_pos = frappe.get_all(
        "Purchase Order",
        filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": 1},
        fields=["name", "supplier", "supplier_name", "base_net_total", "grand_total", "status"],
        order_by="creation asc",
    )
    for p in sub_pos:
        p["source_doctype"] = "Purchase Order"
        p["invoice"] = _pinv_for("purchase_order", p["name"])
        maquila.append(p)

    return {"materiales": materiales, "maquila": maquila}


@frappe.whitelist()
def crear_factura_compra(source_doctype: str, source_name: str) -> dict:
    """Crea una Factura de Compra (Purchase Invoice) en borrador desde un Recibo de compra
    (materiales) o una OC de subcontratación (maquila)."""
    field = "purchase_receipt" if source_doctype == "Purchase Receipt" else "purchase_order"
    existing = frappe.db.get_value("Purchase Invoice Item", {field: source_name, "docstatus": ["<", 2]}, "parent")
    if existing:
        return {"name": existing}

    if source_doctype == "Purchase Receipt":
        from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
    else:
        from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

    pinv = make_purchase_invoice(source_name)
    pinv.flags.ignore_permissions = True
    pinv.flags.ignore_mandatory = True
    pinv.insert()
    return {"name": pinv.name, "docstatus": pinv.docstatus}


@frappe.whitelist()
def get_factura_compra(name: str) -> dict:
    """Detalle de una factura de compra para la vista editable."""
    doc = frappe.get_doc("Purchase Invoice", name)
    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.status,
        "supplier": doc.supplier,
        "supplier_name": doc.supplier_name,
        "posting_date": str(doc.posting_date) if doc.posting_date else "",
        "due_date": str(doc.due_date) if doc.due_date else "",
        "bill_no": doc.bill_no or "",
        "bill_date": str(doc.bill_date) if doc.bill_date else "",
        "payment_terms_template": doc.payment_terms_template,
        "tc_name": doc.tc_name,
        "base_net_total": doc.base_net_total,
        "grand_total": doc.grand_total,
        "currency": doc.currency,
        "items": [
            {"item_code": r.item_code, "item_name": r.item_name, "qty": r.qty, "uom": r.uom, "rate": r.rate, "amount": r.amount}
            for r in (doc.items or [])
        ],
    }


@frappe.whitelist()
def actualizar_factura_compra(name: str, posting_date=None, due_date=None, bill_no=None, bill_date=None,
                              payment_terms_template=None, tc_name=None) -> dict:
    """Actualiza los datos manuales de una factura de compra en borrador."""
    doc = frappe.get_doc("Purchase Invoice", name)
    if doc.docstatus != 0:
        frappe.throw(_("La factura ya está validada; no se puede editar."))
    if posting_date:
        doc.set_posting_time = 1
        doc.posting_date = posting_date
    if due_date:
        doc.due_date = due_date
    if bill_no is not None:
        doc.bill_no = bill_no or None
    if bill_date:
        doc.bill_date = bill_date
    doc.payment_terms_template = payment_terms_template or None
    doc.tc_name = tc_name or None
    doc.terms = resolver_terminos(tc_name)
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def dashboard_metrics(company=None) -> dict:
    """Métricas del flujo de costeo → venta → producción subcontratada → facturación.
    `company`: filtro del selector global del navbar -- None = todas las compañías."""
    from frappe.utils import add_months

    # Todas las métricas monetarias usan el NETO (sin IVA): el impuesto es trasladado,
    # no es ingreso ni costo real. base_net_total = neto en moneda de la compañía.
    def suma(dt, field="base_net_total", filters=None):
        f = dict(filters or {})
        f["docstatus"] = ["<", 2]
        if company:
            f["company"] = company
        rows = frappe.get_all(dt, filters=f, fields=[f"sum({field}) as t"])
        return flt(rows[0].t) if rows and rows[0].t else 0.0

    # ── Costeos por estado (pipeline) ────────────────────────────────────────
    # Costeo usa "compañia" (con ñ) como campo real -- "company" en este doctype
    # no se mantiene sincronizado, no filtrar por él.
    estados = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado"]
    por_estado = {e: 0 for e in estados}
    costeo_filters = {"compañia": company} if company else {}
    for r in frappe.get_all(
        "Costeo", filters=costeo_filters, fields=["costeo_status", "count(name) as n"], group_by="costeo_status"
    ):
        st = r.get("costeo_status") or "Borrador"
        por_estado[st] = por_estado.get(st, 0) + (r.n or 0)
    total_costeos = sum(por_estado.values())

    # ── Embudo de valor ──────────────────────────────────────────────────────
    valor_cotizado = suma("Quotation")
    valor_vendido = suma("Sales Order")
    valor_facturado = suma("Sales Invoice")
    compras_mp = suma("Purchase Order", filters={"is_subcontracted": 0})
    gasto_maquila = suma("Purchase Order", filters={"is_subcontracted": 1})

    # Cobrado: no existe un campo neto de "pagado" en Sales Invoice (paid_amount
    # ya trae IVA mezclado), así que se prorratea -- de lo neto facturado
    # (base_net_total), solo la proporción que ya está saldada según
    # (base_grand_total - outstanding_amount) / base_grand_total.
    valor_cobrado = frappe.db.sql(
        f"""SELECT SUM(
                CASE WHEN base_grand_total > 0
                    THEN base_net_total * (base_grand_total - outstanding_amount) / base_grand_total
                    ELSE 0
                END
            ) FROM `tabSales Invoice`
            WHERE docstatus = 1 {"AND company = %s" if company else ""}""",
        (company,) if company else (),
    )
    valor_cobrado = flt(valor_cobrado[0][0]) if valor_cobrado and valor_cobrado[0][0] else 0.0

    # ── Prendas ──────────────────────────────────────────────────────────────
    prendas_vendidas = suma("Sales Order", field="total_qty")

    # ── Margen promedio (del costeo) ─────────────────────────────────────────
    margen_prom = 0.0
    cp = frappe.get_meta("Costeo").get_field("costeo_producto")
    cp_dt = cp.options if cp else None
    if cp_dt and frappe.db.has_column(cp_dt, "margin_pct"):
        if company:
            r = frappe.db.sql(
                f"""SELECT AVG(margin_pct) FROM `tab{cp_dt}` cp
                    WHERE margin_pct > 0 AND cp.parent IN (
                        SELECT name FROM `tabCosteo` WHERE compañia = %s
                    )""",
                (company,),
            )
        else:
            r = frappe.db.sql(f"SELECT AVG(margin_pct) FROM `tab{cp_dt}` WHERE margin_pct > 0")
        margen_prom = flt(r[0][0]) if r and r[0][0] else 0.0

    # ── Producción subcontratada (avance) ────────────────────────────────────
    sub_po_filters = {"is_subcontracted": 1, "docstatus": 1}
    if company:
        sub_po_filters["company"] = company
    sub_pos = frappe.get_all("Purchase Order", filters=sub_po_filters, pluck="name")
    recibidas = 0
    for po in sub_pos:
        sco = frappe.db.get_value("Subcontracting Order", {"purchase_order": po, "docstatus": 1}, "name")
        if sco and frappe.db.get_value("Subcontracting Receipt Item", {"subcontracting_order": sco, "docstatus": 1}, "parent"):
            recibidas += 1
    total_sub = len(sub_pos)

    # ── Top clientes (por valor de OV) ───────────────────────────────────────
    top_clientes_filters = {"docstatus": ["<", 2]}
    if company:
        top_clientes_filters["company"] = company
    top_clientes = frappe.get_all(
        "Sales Order",
        filters=top_clientes_filters,
        fields=["customer", "sum(base_net_total) as monto", "sum(total_qty) as prendas", "count(name) as ordenes"],
        group_by="customer", order_by="monto desc", limit=6,
    )

    # ── Talleres (gasto de maquila por proveedor) ────────────────────────────
    talleres_filters = {"is_subcontracted": 1, "docstatus": ["<", 2]}
    if company:
        talleres_filters["company"] = company
    talleres = frappe.get_all(
        "Purchase Order",
        filters=talleres_filters,
        fields=["supplier", "supplier_name", "sum(base_net_total) as monto", "count(name) as ordenes"],
        group_by="supplier", order_by="monto desc", limit=6,
    )

    # ── Facturado por mes (últimos 6) ────────────────────────────────────────
    facturado_mes = frappe.db.sql(
        f"""SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS mes, SUM(base_net_total) AS monto
           FROM `tabSales Invoice`
           WHERE docstatus < 2 AND posting_date >= %s
           {"AND company = %s" if company else ""}
           GROUP BY mes ORDER BY mes""",
        (add_months(nowdate(), -5), *([company] if company else [])), as_dict=True,
    )

    return {
        "total_costeos": total_costeos,
        "costeos_por_estado": por_estado,
        "valor_cotizado": valor_cotizado,
        "valor_vendido": valor_vendido,
        "valor_facturado": valor_facturado,
        "valor_cobrado": valor_cobrado,
        "compras_mp": compras_mp,
        "gasto_maquila": gasto_maquila,
        "prendas_vendidas": prendas_vendidas,
        "margen_prom": margen_prom,
        "produccion": {"total": total_sub, "recibidas": recibidas, "pendientes": total_sub - recibidas},
        "top_clientes": top_clientes,
        "talleres": talleres,
        "facturado_mes": facturado_mes,
        "moneda": frappe.db.get_default("currency") or "MXN",
        "usuario": frappe.utils.get_fullname(frappe.session.user),
    }


@frappe.whitelist()
def crear_boms(costeo: str) -> dict:
    """Wrapper para la creación de BOMs server-side (llama a la lógica existente)."""
    # La lógica completa de BOMs vive en costeo.py; aquí se expone como endpoint del SPA.
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import (
        _build_stage_subcontracting_rows,
        _as_dict,
    )
    # Por ahora solo confirmamos que el documento existe.
    frappe.get_doc("Costeo", costeo)
    return {"ok": True, "message": "Usa los botones del formulario Costeo en el Desk para crear BOMs."}


@frappe.whitelist()
def delete_costeo(name: str) -> dict:
    """Elimina un Costeo (y sus tablas hijas en cascada)."""
    frappe.delete_doc("Costeo", name, force=True, ignore_permissions=False)
    return {"ok": True, "deleted": name}


@frappe.whitelist()
def delete_quotation(name: str) -> dict:
    """Elimina una cotización -- mismo mecanismo estándar de Frappe que usa el botón
    Eliminar de ERPNext Desk (frappe.delete_doc), así que hereda automáticamente los
    mismos permisos y validaciones: truena igual que en Desk si el usuario no tiene
    permiso de borrado o si la cotización está validada (submitted) y no se puede
    eliminar sin cancelarla primero."""
    frappe.delete_doc("Quotation", name, force=True, ignore_permissions=False)
    return {"ok": True, "deleted": name}


@frappe.whitelist()
def delete_sales_order(name: str) -> dict:
    """Elimina una Orden de Venta -- mismo mecanismo estándar de Frappe que usa el
    botón Eliminar de ERPNext Desk, con los mismos permisos y validaciones heredados
    (truena si está validada/tiene documentos ligados sin cancelar primero)."""
    frappe.delete_doc("Sales Order", name, force=True, ignore_permissions=False)
    return {"ok": True, "deleted": name}


def _precio_acordado_price_list():
    return frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"


def _precio_acordado_vigente(item_code, customer):
    """Precio acordado (Item Price con cliente) más reciente para ese artículo, y si
    sigue vigente hoy -- fijado desde "Fijar Precio" en la Cotización
    (item_api.crear_precio_acordado). Solo cuenta si ya lo validó un CEO -- mientras
    esté en borrador (recién capturado o editado, pendiente de aprobación) se trata
    igual que si no existiera ningún precio acordado."""
    filters = {"item_code": item_code, "customer": customer, "price_list": _precio_acordado_price_list()}
    if frappe.db.has_column("Item Price", "precio_acordado_validado"):
        filters["precio_acordado_validado"] = 1
    row = frappe.db.get_value(
        "Item Price", filters, ["price_list_rate", "valid_upto"], as_dict=True, order_by="valid_upto desc",
    )
    if not row:
        return None
    row["vigente"] = not row.valid_upto or getdate(row.valid_upto) >= getdate(nowdate())
    return row


@frappe.whitelist()
def get_precio_acordado_status(sales_order: str) -> dict:
    """Estado del precio acordado de cada artículo de la OV -- para habilitar o
    bloquear "Generar réplica" en el SPA antes de intentarlo (mismo criterio que
    generar_replica_ov revalida del lado servidor)."""
    so = frappe.get_doc("Sales Order", sales_order)
    items = []
    for it in so.items:
        row = _precio_acordado_vigente(it.item_code, so.customer)
        items.append({
            "item_code": it.item_code,
            "item_name": it.item_name,
            "qty": flt(it.qty),
            "rate": flt(row.price_list_rate) if row else flt(it.rate),
            "tiene_precio_acordado": bool(row),
            "vigente": bool(row and row.vigente),
            "valid_upto": row.valid_upto if row else None,
        })
    puede_generar = bool(items) and all(i["tiene_precio_acordado"] and i["vigente"] for i in items)
    vencido = bool(items) and all(i["tiene_precio_acordado"] for i in items) and not puede_generar
    return {
        "items": items,
        "puede_generar": puede_generar,
        "vencido": vencido,
        "es_ceo": "CEO" in frappe.get_roles(),
    }


@frappe.whitelist()
def generar_replica_ov(sales_order: str, items) -> dict:
    """Crea una Orden de Venta nueva reusando los mismos artículos y precios
    acordados de una OV existente del mismo cliente -- salta Costear/Cotizar por
    completo para un pedido recurrente que ya conoce el precio. Bloqueada si el
    precio acordado ya venció, salvo para el rol "CEO" (validación de permisos: no
    se borra ni se modifica el precio acordado, solo se autoriza generar con él)."""
    if isinstance(items, str):
        items = json.loads(items)
    if not items:
        frappe.throw(_("Agrega al menos un artículo."))

    so = frappe.get_doc("Sales Order", sales_order)
    es_ceo = "CEO" in frappe.get_roles()

    for it in items:
        row = _precio_acordado_vigente(it["item_code"], so.customer)
        if not row:
            frappe.throw(_('{0} no tiene precio acordado -- usa "Fijar Precio" desde la cotización primero.').format(it["item_code"]))
        if not row.vigente and not es_ceo:
            frappe.throw(_(
                "El precio acordado de {0} venció el {1}. Un usuario con rol CEO debe generar esta réplica para desbloquearlo."
            ).format(it["item_code"], formatdate(row.valid_upto)))

    new_so = frappe.new_doc("Sales Order")
    new_so.customer = so.customer
    new_so.company = so.company
    new_so.transaction_date = nowdate()
    new_so.delivery_date = add_days(nowdate(), 15)
    if frappe.db.has_column("Sales Order", "costeo"):
        new_so.costeo = so.get("costeo")
    for it in items:
        new_so.append("items", {
            "item_code": it["item_code"],
            "qty": flt(it.get("qty")) or 1,
            "rate": flt(it.get("rate")),
        })
    new_so.flags.ignore_permissions = True
    new_so.insert()
    frappe.db.commit()
    return {"name": new_so.name}


@frappe.whitelist()
def eliminar_orden_y_costeo(orden_venta_id: str) -> dict:
    """Elimina una Orden de Venta ya cancelada junto con su Costeo relacionado.

    Usado por el botón "Eliminar por Costeo" del Client Script en Sales Order,
    que solo se muestra cuando la orden ya está cancelada — se revalida aquí
    porque nunca hay que confiar en el estado que reporta el cliente.
    """
    so = frappe.get_doc("Sales Order", orden_venta_id)
    if so.docstatus != 2:
        frappe.throw(_("Solo se puede eliminar una Orden de Venta que ya esté cancelada."))

    costeo_name = so.get("costeo")

    frappe.delete_doc("Sales Order", orden_venta_id, force=True, ignore_permissions=False)

    if costeo_name and frappe.db.exists("Costeo", costeo_name):
        frappe.delete_doc("Costeo", costeo_name, force=True, ignore_permissions=False)

    frappe.db.commit()
    return {"ok": True, "deleted_sales_order": orden_venta_id, "deleted_costeo": costeo_name}


@frappe.whitelist()
def duplicate_costeo(name: str) -> dict:
    """Crea una copia del Costeo con estatus Borrador."""
    original = frappe.get_doc("Costeo", name)
    copy = frappe.copy_doc(original)
    copy.costeo_status = "Borrador"
    copy.insert(ignore_permissions=False)
    frappe.db.commit()
    return {"ok": True, "name": copy.name}


@frappe.whitelist()
def get_item_price(item_code, price_list=None):
    """Returns price of an item from a given (or default) price list."""
    if not price_list:
        price_list = frappe.db.get_default("buying_price_list") or "Compra estandar"
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list},
        "price_list_rate",
    )
    currency = frappe.db.get_value("Price List", price_list, "currency") or "MXN"
    return {"price": float(price or 0), "currency": currency, "price_list": price_list}


@frappe.whitelist()
def proveedores_para_item(item_code):
    """Proveedores que tienen este ítem en su lista de precios de COMPRA (Item Price buying),
    con su precio. Sirve para filtrar el proveedor y auto-rellenar el precio en el costeo."""
    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "buying": 1, "supplier": ["is", "set"]},
        fields=["supplier", "price_list_rate", "price_list", "currency", "valid_from", "modified"],
        order_by="valid_from desc, modified desc",
    )
    out = {}
    for r in rows:
        if r.supplier in out:
            continue  # nos quedamos con el más reciente por proveedor
        out[r.supplier] = {
            "supplier": r.supplier,
            "supplier_name": frappe.db.get_value("Supplier", r.supplier, "supplier_name") or r.supplier,
            "rate": float(r.price_list_rate or 0),
            "price_list": r.price_list,
            "currency": r.currency or "MXN",
        }
    return list(out.values())


def _stage_sort_key_int(e):
    """Sort stage rows numerically when possible, then alphabetically."""
    try:
        return (0, int(e.etapa or 0))
    except (ValueError, TypeError):
        return (1, str(e.etapa or ""))


def _match_material_stage(mat_etapa_value, etapas_of_product):
    """A qué etapa corresponde un material, dado el valor libre que trae en su
    campo 'etapa' -- puede ser un stage_id (dato nuevo, capturado desde el
    selector de 'Preparar Manufactura') o un número de etapa legado (dato de
    antes de que existiera stage_id). Se intenta primero como stage_id porque es
    inequívoco; el número solo sirve de respaldo para costeos viejos."""
    if not mat_etapa_value:
        return None
    for e in etapas_of_product:
        if e.get("stage_id") and e.get("stage_id") == mat_etapa_value:
            return e
    for e in etapas_of_product:
        if str(e.get("etapa") or "") == str(mat_etapa_value):
            return e
    return None


def _split_materials_by_stage(mats, etapas_of_product, splits_all):
    """Reparte cada materia prima entre las etapas que la consumen.

    ``splits_all`` es Costeo.tabla_materiales_etapa completa (filas cuyo stage_id no
    corresponda a ninguna de ``etapas_of_product`` se ignoran, así que es seguro
    mandarla sin filtrar por producto). Regresa (por_etapa, sin_etapa) donde cada
    elemento es una tupla ``(fila_de_material, qty_por_pieza)``:

    - por_etapa: {stage_id: [(mat, qty), ...]} -- lo que consume esa etapa física.
    - sin_etapa: [(mat, qty), ...] -- material que no quedó atribuido a ninguna
      etapa; el caller lo mete en la(s) etapa(s) raíz, como siempre.

    Un material con filas propias en ``splits_all`` usa ESAS cantidades (puede
    aparecer en varias etapas a la vez, ej. 4 de cinta reflejante = 2 en la manga +
    2 en el frente). Un material SIN filas ahí -- o cuyas filas quedaron todas
    inválidas (cantidad 0, o etapa borrada) -- cae al comportamiento de siempre:
    se atribuye COMPLETO a la única etapa de su campo escalar 'etapa'. Por eso los
    costeos ya capturados dan exactamente el mismo BOM que antes de este cambio."""
    splits_by_material = {}
    for row in splits_all or []:
        mid = row.get("material_id")
        sid = row.get("stage_id")
        if mid and sid:
            splits_by_material.setdefault(mid, []).append(row)

    stage_keys = {e.get("stage_id") for e in etapas_of_product if e.get("stage_id")}

    por_etapa, sin_etapa = {}, []
    for mat in mats:
        # supplier_qty es el total a comprar (consumo x piezas); solo sirve de
        # respaldo para costeos viejos que nunca capturaron internal_qty.
        base_qty = float(mat.internal_qty or mat.supplier_qty or 1)

        asignado = [
            (row.get("stage_id"), float(row.get("qty") or 0))
            for row in splits_by_material.get(mat.get("material_id") or "", [])
            if row.get("stage_id") in stage_keys and float(row.get("qty") or 0) > 0
        ]
        if asignado:
            for stage_id, qty in asignado:
                por_etapa.setdefault(stage_id, []).append((mat, qty))
            continue

        matched = _match_material_stage(mat.etapa, etapas_of_product)
        if matched:
            mk = matched.get("stage_id") or matched.get("name") or matched.get("etapa")
            por_etapa.setdefault(mk, []).append((mat, base_qty))
        else:
            sin_etapa.append((mat, base_qty))
    return por_etapa, sin_etapa


def _repair_stale_bom_no(bom_name, company, mantener_vacio=None):
    """Si este BOM ya existía de un intento anterior que falló A MEDIAS (ej. el BOM
    de la pieza que recibe como insumo no se había podido crear todavía), su fila
    de esa pieza quedó con 'bom_no' vacío -- crear_boms_spa solo lo llena al
    momento de armar el BOM, y si esa pieza aún no existía, se queda así para
    siempre aunque su BOM se termine creando después en un reintento posterior.

    Consecuencia real (no cosmética): la explosión multinivel de materiales del
    Production Plan (y por lo tanto la Solicitud de Materiales) se corta justo en
    esa fila -- cualquier materia prima que esté MÁS ARRIBA en la cadena nunca se
    cuenta, sin ningún aviso.

    Esta función se llama cada vez que crear_boms_spa encuentra un BOM que YA
    existe (se iba a saltar sin más): completa la(s) fila(s) que ahora sí tienen
    su BOM disponible y recalcula la explosión. Como las operaciones se procesan
    en orden topológico (raíz primero), una sola corrida repara toda la cadena de
    abajo hacia arriba.

    ``mantener_vacio`` (set de item_code, opcional): filas que NO hay que tocar
    aunque su BOM ya exista -- son las que crear_boms_spa dejó sin bom_no A
    PROPÓSITO por ser un vínculo "recibe de" redundante (ver
    _resolve_production_operations, upstream_redundantes): si esta función las
    "reparara", volvería a contar de más la materia prima compartida entre varios
    caminos en paralelo, justo lo que ese diseño evita."""
    bom = frappe.get_doc("BOM", bom_name)
    tocado = False
    for row in bom.items:
        if row.bom_no or not row.item_code or row.do_not_explode:
            continue
        if mantener_vacio and row.item_code in mantener_vacio:
            continue
        up_bom = frappe.db.get_value(
            "BOM", {"item": row.item_code, "is_active": 1, "docstatus": 1, "company": company}, "name",
        )
        if up_bom:
            row.db_set("bom_no", up_bom, update_modified=False)
            tocado = True
    if tocado:
        bom.update_exploded_items(save=True)
        frappe.db.commit()


@frappe.whitelist()
def crear_boms_spa(costeo: str) -> dict:
    """Crea BOMs siguiendo exactamente la lógica del botón del doctype antiguo:

    - Un BOM por ETAPA (no uno por producto).
    - Etapas no-últimas → BOM para el subensamblaje de esa etapa.
    - Etapa final → BOM para el finished_item.
    - Ítems del BOM: subensamblaje de la etapa anterior (si existe) +
      materias primas de costeo_producto_detalle filtradas por número de etapa.
    - Cantidad siempre = 1 (no la qty del producto).
    - Usa internal_qty / internal_uom para las cantidades.
    - Omite si ya existe un BOM (enviado o borrador) para ese ítem.
    - Configuración: rm_cost_as_per="Price List", buying_price_list="Compra estandar".
    """
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    doc     = frappe.get_doc("Costeo", costeo)
    company = doc.compañia
    created, errors, skipped = [], [], []

    # ── 1. Agrupar etapas por producto ───────────────────────────────────────
    etapas_por_producto: dict = {}
    for e in doc.tabla_etapas_costeo:
        if e.producto_terminado:
            etapas_por_producto.setdefault(e.producto_terminado, []).append(e)

    if not etapas_por_producto:
        frappe.throw("No hay etapas configuradas en el costeo.")

    # ── 2. Agrupar materias primas por producto ──────────────────────────────
    mats_por_producto: dict = {}
    for d in doc.costeo_producto_detalle:
        if d.finished_item and d.concept_type == "Materia Prima" and d.item:
            mats_por_producto.setdefault(d.finished_item, []).append(d)

    # ── 2b. Sustituciones de material por talla (sobrecosto_tipo = "Material") ──
    # El BOM se queda tal cual (sigue costeando con el material estándar) -- solo
    # se marca esa línea como "permite artículo alterno" y se registra el par en
    # Item Alternative, así el envío de material al taller de un lote específico
    # de esa talla puede usar el artículo real sin que el sistema marque "sin
    # stock" (ver sub_transferir_material)."""
    alternos_por_producto: dict = {}
    for t in doc.tabla_tallas_costeo:
        if t.finished_item and t.sobrecosto_tipo == "Material" and t.sobrecosto_material_original and t.sobrecosto_material_alterno:
            alternos_por_producto.setdefault(t.finished_item, {})[t.sobrecosto_material_original] = t.sobrecosto_material_alterno

    # ── 3. Procesar cada producto ─────────────────────────────────────────────
    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        if not finished_item or float(producto.qty or 0) <= 0:
            continue

        etapas = etapas_por_producto.get(finished_item, [])
        if not etapas:
            errors.append(f"{finished_item}: sin etapas configuradas")
            continue

        # Operaciones ya vienen en orden topológico -- procesa primero las raíz, así
        # el BOM que una operación referencia como upstream ya existe cuando le toca.
        # _resolve_production_operations fusiona las etapas del mismo proveedor que
        # están en el mismo punto del flujo en UNA operación con varios servicios y
        # UN resultado; si nada se fusiona hay una operación por nodo, idéntico al
        # comportamiento lineal de siempre.
        operaciones = _resolve_production_operations(etapas, finished_item)
        op_por_key = {op.op_key: op for op in operaciones}
        # Cada entrada es (fila_de_material, qty_por_pieza): la cantidad ya viene
        # repartida por etapa cuando el costeo declaró el reparto explícito (ver
        # _split_materials_by_stage), en vez de asumir que la etapa consume el
        # material completo.
        mats_by_key, mats_sin_etapa = _split_materials_by_stage(
            mats_por_producto.get(finished_item, []), etapas, doc.get("tabla_materiales_etapa")
        )

        for op in operaciones:
            bom_item = op.output_item
            if not bom_item:
                errors.append(
                    f"{finished_item} ({op.supplier or '?'}): falta el sub-ensamblaje que "
                    "produce esta operación. Complétalo antes de crear los BOMs."
                )
                continue

            # ── Ítems del BOM ────────────────────────────────────────────────
            items_bom = []

            # Resultados de las operaciones de las que ESTA recibe -- puede ser más
            # de una (procesos en paralelo que convergen), cada una aportando la
            # pieza COMPLETA (qty 1) -- ver _resolve_production_operations, "sin
            # reducción transitiva".
            for up_key in op.upstream_keys:
                up = op_por_key.get(up_key)
                up_sub = up.output_item if up else None
                if not up_sub:
                    continue
                up_uom = frappe.db.get_value("Item", up_sub, "stock_uom") or "Nos"
                es_redundante = up_key in (op.upstream_redundantes or set())
                # Referencia explícita al BOM previo, para que la explosión
                # multinivel del Production Plan recurra correctamente -- SALVO en
                # un vínculo redundante (ya alcanzable vía otro upstream de esta
                # misma operación, ver upstream_redundantes): ahí se marca
                # do_not_explode. La pieza se sigue listando (así se refleja que el
                # taller la recibe), pero NO se re-explora su receta -- si se
                # explorara por las dos rutas, la materia prima compartida (ej. la
                # tela de un corte que reparte piezas a bordado Y a colocación de
                # cinta, y el paso final recibe de ambos MÁS una pieza directa del
                # corte) se contaría de más en el desglose multinivel del BOM/Plan
                # de Producción -- aunque físicamente se cortó una sola vez.
                #
                # OJO: dejar bom_no vacío NO BASTA -- BOM.set_bom_material_details()
                # (ERPNext nativo, corre en cada validate()) rellena cualquier
                # bom_no vacío con el default_bom del ítem si lo tiene, así que un
                # vínculo "en blanco a propósito" se re-conectaba solo en cuanto se
                # guardaba/enviaba el BOM. do_not_explode es el único mecanismo
                # nativo que de verdad evita ese refill (ver get_bom_material_detail:
                # "if args.get('do_not_explode'): ret_item['bom_no'] = ''").
                up_bom = "" if es_redundante else (
                    frappe.db.get_value(
                        "BOM", {"item": up_sub, "is_active": 1, "docstatus": ["in", [0, 1]], "company": company}, "name"
                    ) or ""
                )
                items_bom.append({
                    "item_code": up_sub,
                    "qty":       1,
                    "uom":       up_uom,
                    "stock_uom": up_uom,
                    "rate":      0,
                    "bom_no":    up_bom,
                    "do_not_explode": 1 if es_redundante else 0,
                })

            # Materias primas de TODAS las etapas fusionadas en esta operación. Las
            # que no quedaron atribuidas a ninguna etapa se incluyen en la(s)
            # operación(es) RAÍZ (sin upstream) -- ahí arranca la producción. Un mismo
            # material repartido entre varias etapas de la operación (ej. hilo de
            # bordado 0.5 en cada bordado) se SUMA en un solo renglón del BOM.
            stage_mats = []
            for sk in op.member_stage_keys:
                stage_mats += mats_by_key.get(sk, [])
            if not op.upstream_keys:
                stage_mats += mats_sin_etapa

            mats_agrupados = {}
            mat_uom = {}
            for mat, mat_qty in stage_mats:
                mat_uom[mat.item] = (mat.internal_uom
                                     or frappe.db.get_value("Item", mat.item, "stock_uom")
                                     or "Nos")
                mats_agrupados[mat.item] = mats_agrupados.get(mat.item, 0) + mat_qty
            for item_code, qty in mats_agrupados.items():
                items_bom.append({
                    "item_code": item_code,
                    "qty":       qty,
                    "uom":       mat_uom[item_code],
                    "stock_uom": mat_uom[item_code],
                    "rate":      0,
                })

            if not items_bom:
                errors.append(
                    f"{bom_item} ({op.supplier or '?'}): no tiene materiales ni resultado "
                    "de entrada asignados — no se puede armar su BOM."
                )
                continue

            # ── Verificar si ya existe BOM ───────────────────────────────────
            # SIEMPRE acotado a la compañía: el BOM es por compañía en ERPNext, así que
            # el de otra empresa no sirve aquí -- sin este filtro, un costeo de la
            # compañía B se saltaba la creación porque A ya tenía un BOM de ese ítem, y
            # después la producción de B se quedaba sin BOM propio.
            existing = frappe.db.get_value(
                "BOM",
                {"item": bom_item, "docstatus": ["in", [0, 1]], "company": company},
                "name",
            )
            if existing:
                redundantes_items = {
                    op_por_key[uk].output_item
                    for uk in (op.upstream_redundantes or set())
                    if uk in op_por_key and op_por_key[uk].output_item
                }
                _repair_stale_bom_no(existing, company, mantener_vacio=redundantes_items)
                skipped.append(f"{bom_item}: BOM ya existe ({existing})")
                continue

            # ── Crear y enviar BOM ───────────────────────────────────────────
            try:
                bom = frappe.new_doc("BOM")
                bom.item               = bom_item
                bom.quantity           = 1
                bom.company            = company
                bom.is_active          = 1
                bom.is_default         = 1
                bom.with_operations    = 0
                bom.rm_cost_as_per     = "Price List"
                bom.buying_price_list  = "Compra estandar"
                if frappe.db.has_column("BOM", "costeo"):
                    bom.costeo = costeo
                for it in items_bom:
                    bom.append("items", it)

                # Marcar líneas con sustitución de material por talla (ver 2b) --
                # el BOM sigue costeando con el material estándar, solo se habilita
                # para que un lote de esa talla pueda usar el alterno al transferir.
                alternos = alternos_por_producto.get(finished_item, {})
                if alternos:
                    for row in bom.items:
                        alterno = alternos.get(row.item_code)
                        if not alterno:
                            continue
                        row.allow_alternative_item = 1
                        bom.allow_alternative_item = 1
                        _asegurar_articulo_alterno(row.item_code, alterno)

                bom.flags.ignore_permissions = True
                bom.flags.ignore_links       = True
                bom.insert()
                bom.submit()
                created.append(bom.name)
            except Exception as exc:
                errors.append(f"{bom_item} ({op.supplier or '?'}): {exc}")

    frappe.db.commit()
    return {"created": created, "errors": errors, "skipped": skipped}


@frappe.whitelist()
def crear_solicitud_material(costeo: str) -> dict:
    """Creates a Material Request (Purchase) from raw-material rows."""
    doc = frappe.get_doc("Costeo", costeo)
    company = doc.compañia

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.transaction_date = nowdate()
    mr.company  = company
    mr.status   = "Draft"
    if frappe.db.has_column("Material Request", "costeo"):
        mr.costeo = costeo

    added = 0
    for d in doc.costeo_producto_detalle:
        if d.concept_type == "Materia Prima" and d.item and float(d.supplier_qty or 0) > 0:
            uom = d.supplier_uom or frappe.db.get_value("Item", d.item, "stock_uom") or "Nos"
            row = {
                "item_code":     d.item,
                "qty":           float(d.supplier_qty),
                "uom":           uom,
                "schedule_date": nowdate(),
                "warehouse":     doc.almacen_materias_primas or "",
            }
            if d.supplier:
                row["supplier"] = d.supplier
            mr.append("items", row)
            added += 1

    if not added:
        frappe.throw("No hay materias primas con cantidad > 0 en este costeo.")

    mr.flags.ignore_permissions = True
    mr.flags.ignore_links       = True
    mr.flags.ignore_mandatory   = True
    mr.insert()
    frappe.db.commit()
    return {"name": mr.name}


@frappe.whitelist()
def crear_ordenes_trabajo(costeo: str) -> dict:
    """Creates Work Orders for each finished item (requires an active BOM)."""
    doc = frappe.get_doc("Costeo", costeo)
    company = doc.compañia
    created, errors = [], []

    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        qty = float(producto.qty or 1)
        if not finished_item or qty <= 0:
            continue

        bom = frappe.db.get_value(
            "BOM",
            {"item": finished_item, "is_active": 1, "is_default": 1, "docstatus": 1, "company": company},
            "name",
        ) or frappe.db.get_value(
            # Respaldo por si el BOM no está marcado como predeterminado -- pero SIN
            # salirse de la compañía: usar el BOM de otra empresa haría que la orden
            # de trabajo apunte a estructuras y almacenes que no son suyos.
            "BOM",
            {"item": finished_item, "is_active": 1, "docstatus": 1, "company": company},
            "name",
        )
        if not bom:
            errors.append(f"{finished_item}: sin BOM activo — crea el BOM primero")
            continue

        try:
            wo = frappe.new_doc("Work Order")
            wo.production_item = finished_item
            wo.bom_no  = bom
            wo.qty     = qty
            wo.company = company
            if frappe.db.has_column("Work Order", "costeo"):
                wo.costeo = costeo
            wo.wip_warehouse = doc.almacen_trabajo_en_proceso or ""
            wo.fg_warehouse  = frappe.db.get_value(
                "Item Default",
                {"parent": finished_item, "company": company},
                "default_warehouse",
            ) or ""
            wo.flags.ignore_permissions = True
            wo.flags.ignore_links       = True
            wo.insert()
            created.append(wo.name)
        except Exception as exc:
            errors.append(f"{finished_item}: {exc}")

    frappe.db.commit()
    return {"created": created, "errors": errors}


@frappe.whitelist()
def crear_pos_subcontratacion(costeo: str) -> dict:
    """Creates Subcontracting Purchase Orders from stage (etapa) rows."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import (
        _as_dict,
        _build_stage_subcontracting_rows,
        _create_subcontracting_pos_from_stages,
    )
    doc = frappe.get_doc("Costeo", costeo)
    source = doc.as_dict()
    stage_rows = _build_stage_subcontracting_rows(source)
    if not stage_rows:
        frappe.throw(
            "No hay etapas de subcontratación con proveedor y servicio. "
            "Configúralas en la pestaña 'Etapas de Manufactura'."
        )
    result = _create_subcontracting_pos_from_stages(source, stage_rows)
    if frappe.db.has_column("Purchase Order", "costeo"):
        for po_name in result.get("purchase_orders", []):
            frappe.db.set_value("Purchase Order", po_name, "costeo", costeo, update_modified=False)
        frappe.db.commit()
    return result


@frappe.whitelist()
def crear_subcontracting_bom(costeo: str) -> dict:
    """Crea un Subcontracting BOM por OPERACIÓN (ver _resolve_production_operations):
    - Operación no terminal → finished_good = su resultado (sintético si fusiona varias)
    - Operación terminal     → finished_good = el producto terminado
    Cuando la operación agrupa varios servicios del mismo proveedor, el Subcontracting
    BOM se crea con el servicio PRIMARIO y conversion_factor = nº de servicios, para
    que la OC reparta la pieza entre los k renglones y el total producido sea UNO.
    Se salta si ya existe un Subcontracting BOM para ese finished_good."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    doc     = frappe.get_doc("Costeo", costeo)
    created, errors, skipped = [], [], []

    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        if not finished_item:
            continue

        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == finished_item]
        if not etapas_prod:
            continue
        operaciones = _resolve_production_operations(etapas_prod, finished_item)

        for op in operaciones:
            servicios = [s for s in op.servicios if s.get("service_item")]
            if not servicios:
                continue
            servicio      = servicios[0]["service_item"]
            k             = len(servicios)
            finished_good = op.output_item

            if not finished_good or not servicio:
                continue

            # Subcontracting BOM NO tiene campo de compañía (es un mapeo global
            # producto→servicio en ERPNext), así que se acota por la compañía del BOM
            # que referencia: si el que existe es de OTRA empresa, saltarlo en silencio
            # dejaría a ésta apuntando a la estructura equivocada, así que se avisa.
            existentes = frappe.get_all(
                "Subcontracting BOM", filters={"finished_good": finished_good},
                fields=["name", "finished_good_bom"],
            )
            propio = next(
                (e for e in existentes
                 if frappe.db.get_value("BOM", e.finished_good_bom, "company") == doc.compañia),
                None,
            )
            if propio:
                skipped.append(f"{finished_good} (ya existe: {propio.name})")
                continue
            if existentes:
                errors.append(
                    f"{finished_good}: ya hay un BOM de subcontratación ({existentes[0].name}) "
                    f"de otra compañía. Revísalo antes de producirlo en {doc.compañia}."
                )
                continue

            # Require a submitted BOM for the finished_good (de ESTA compañía)
            bom_name = frappe.db.get_value(
                "BOM",
                {"item": finished_good, "is_active": 1, "is_default": 1, "docstatus": 1, "company": doc.compañia},
                "name",
            )
            if not bom_name:
                errors.append(
                    f"{finished_good}: no existe BOM activo y enviado. "
                    "Crea los BOMs normales primero."
                )
                continue

            lote_qty = flt(servicios[0].get("lote_qty")) or 1
            if k > 1:
                # Operación con varios servicios sobre una pieza: el SubBOM se crea con
                # el servicio primario y conversion_factor = k. En la OC, fg_qty de cada
                # renglón es 1/k de la pieza y service_qty = fg_qty x k = pieza entera,
                # así los k renglones producen UNA pieza y cada servicio se factura
                # completo (ver _create_subcontracting_pos_from_stages).
                finished_good_uom = frappe.db.get_value("Item", finished_good, "stock_uom") or "Nos"
                svc_uom = frappe.db.get_value("Item", servicio, "stock_uom") or "Nos"
                finished_good_qty = 1
                service_item_qty = k
            elif lote_qty > 1:
                # Si el proveedor cobra por lote (ej. $19 por 25 confecciones), el
                # Subcontracting BOM refleja "1 Lote de servicio produce lote_qty
                # [lote_uom] de producto" -- no "1 servicio = 1 pieza".
                finished_good_uom = servicios[0].get("lote_uom") or frappe.db.get_value("Item", finished_good, "stock_uom") or "Nos"
                svc_uom = LOTE_UOM
                finished_good_qty = lote_qty
                service_item_qty = 1
            else:
                finished_good_uom = frappe.db.get_value("Item", finished_good, "stock_uom") or "Nos"
                svc_uom = frappe.db.get_value("Item", servicio, "stock_uom") or "Nos"
                finished_good_qty = 1
                service_item_qty = 1

            try:
                subc = frappe.new_doc("Subcontracting BOM")
                subc.finished_good     = finished_good
                subc.finished_good_qty = finished_good_qty
                subc.finished_good_uom = finished_good_uom
                subc.finished_good_bom = bom_name
                subc.is_active         = 1
                subc.service_item      = servicio
                subc.service_item_qty  = service_item_qty
                subc.service_item_uom  = svc_uom
                subc.conversion_factor = service_item_qty / finished_good_qty
                subc.flags.ignore_permissions = True
                subc.flags.ignore_links       = True
                subc.flags.ignore_mandatory   = True
                if frappe.db.has_column("Subcontracting BOM", "costeo"):
                    subc.costeo = costeo
                subc.insert()
                subc.submit()
                created.append(subc.name)
            except Exception as exc:
                errors.append(f"{finished_good} / {servicio}: {exc}")

    frappe.db.commit()
    return {"created": created, "errors": errors, "skipped": skipped}


def _get_plan_for_so(costeo: str, sales_order: str):
    """Nombre del Production Plan (no cancelado) que ya está ligado a esa OV específica,
    vía la tabla hija nativa 'Production Plan Sales Order' -- o None si no existe todavía.
    Es la base de "un plan por OV" en vez de "un plan por costeo": cada OV bajo un mismo
    Costeo (réplicas de pedidos recurrentes incluidas) necesita poder tener su propio plan
    sin que el de otra OV lo bloquee."""
    if not sales_order:
        return None
    plan_names = frappe.get_all(
        "Production Plan", filters={"costeo": costeo, "docstatus": ["!=", 2]}, pluck="name"
    )
    if not plan_names:
        return None
    return frappe.db.get_value(
        "Production Plan Sales Order",
        {"parent": ["in", plan_names], "sales_order": sales_order},
        "parent",
    )


@frappe.whitelist()
def desbloquear_plan_produccion(costeo: str, sales_order: str = None) -> dict:
    """Crea un Production Plan LIGADO a una Orden de Venta específica del Costeo.

    ``sales_order``, si se manda, es la OV activa elegida en el SPA -- se valida que
    pertenezca a este costeo y esté validada, y el plan se construye DESDE ella
    (get_items_from='Sales Order' + get_items()), de modo que los po_items arrastren
    sales_order / sales_order_item y se conserve la trazabilidad OV -> plan -> MR/WO.
    Sin ``sales_order`` cae al comportamiento anterior (la OV validada más reciente del
    costeo, o la primera si ninguna está validada) -- para no romper costeos con una sola OV.
    Si no hay OV en absoluto, cae a construir los po_items directamente del costeo.
    """
    doc     = frappe.get_doc("Costeo", costeo)
    company = doc.compañia

    so_name = None
    if sales_order:
        so_name = frappe.db.get_value(
            "Sales Order", {"name": sales_order, "costeo": costeo, "docstatus": 1}, "name"
        )
        if not so_name:
            frappe.throw(_(
                "La Orden de Venta {0} no existe, no pertenece a este Costeo o no está validada."
            ).format(sales_order))
    elif frappe.db.has_column("Sales Order", "costeo"):
        so_name = (
            frappe.db.get_value("Sales Order", {"costeo": costeo, "docstatus": 1}, "name")
            or frappe.db.get_value("Sales Order", {"costeo": costeo}, "name")
        )

    pp = frappe.new_doc("Production Plan")
    pp.company          = company
    pp.transaction_date = nowdate()
    pp.status           = "Draft"
    if frappe.db.has_column("Production Plan", "costeo"):
        pp.costeo = costeo

    linked_so = None
    if so_name:
        try:
            so = frappe.get_doc("Sales Order", so_name)
            pp.get_items_from = "Sales Order"
            pp.append("sales_orders", {
                "sales_order":      so.name,
                "sales_order_date": so.transaction_date,
                "customer":         so.customer,
                "grand_total":      so.grand_total,
            })
            pp.get_items()  # llena po_items con referencia a la OV
            for row in pp.get("po_items") or []:
                if not row.bom_no:
                    row.bom_no = frappe.db.get_value(
                        "BOM",
                        {"item": row.item_code, "is_active": 1, "docstatus": 1, "company": doc.compañia},
                        "name",
                    ) or ""
            if pp.get("po_items"):
                linked_so = so.name
        except Exception:
            pp.set("po_items", [])
            pp.set("sales_orders", [])
            pp.get_items_from = ""

    if not pp.get("po_items"):
        _fill_po_items_from_costeo(pp, doc, company)

    # Almacén de materias primas (el del costeo) + "Obtener materias primas para comprar"
    # (netea contra el inventario del almacén).
    if doc.almacen_materias_primas:
        pp.for_warehouse = doc.almacen_materias_primas
        try:
            pp.get_sub_assembly_items()
        except Exception:
            pass
        _fill_mr_items_from_inventory(pp, doc.almacen_materias_primas)

    # Guarda la cantidad EXACTA requerida (antes de que alguien la edite) -- es la
    # base contra la que se valida el margen de "hasta 5% más" al guardar el plan.
    if frappe.db.has_column("Production Plan Item", "planned_qty_original"):
        for row in pp.get("po_items") or []:
            row.planned_qty_original = row.planned_qty

    pp.flags.ignore_permissions = True
    pp.flags.ignore_links       = True
    pp.flags.ignore_mandatory   = True
    pp.insert()
    frappe.db.commit()
    return {"name": pp.name, "sales_order": linked_so}


def _fill_mr_items_from_inventory(pp, warehouse):
    """Ejecuta 'Obtener materias primas para comprar' del Production Plan neteando
    contra el inventario del almacén dado, y llena mr_items."""
    if not warehouse:
        return
    from erpnext.manufacturing.doctype.production_plan.production_plan import (
        get_items_for_material_requests,
    )
    try:
        rows = get_items_for_material_requests(pp.as_dict(), warehouses=[{"warehouse": warehouse}])
    except Exception:
        rows = []
    pp.set("mr_items", [])
    skip = {"name", "idx", "parent", "parenttype", "parentfield", "docstatus", "doctype",
            "creation", "modified", "modified_by", "owner"}
    for row in (rows or []):
        clean = {k: v for k, v in dict(row).items() if not str(k).startswith("__") and k not in skip}
        # Los sub-ensamblajes (grupo "Sub-Ensamblajes", ver auto_materializar_subensamblajes)
        # NUNCA se compran -- crear_pos_subcontratacion los produce por subcontratación
        # directo desde las etapas del costeo, sin pasar por esta Solicitud de Material.
        # Si el explode multi-nivel de ERPNext los mete aquí de todos modos, mr_crear_oc
        # ya no puede armar NINGUNA OC (ni la del proveedor real): la MR queda con
        # renglones con proveedor (materia prima) mezclados con renglones sin proveedor
        # (sub-ensamblaje), y make_purchase_order se rinde en cuanto ve la mezcla. Se
        # descartan aquí, antes de que lleguen a la MR, para no depender de que cada
        # botón que genera OC sepa filtrarlos por su cuenta.
        item_group = frappe.db.get_value("Item", clean.get("item_code"), "item_group")
        if item_group == "Sub-Ensamblajes":
            continue
        clean["warehouse"] = warehouse
        # Redondear SIEMPRE hacia arriba -- para compra y control es mejor pedir de
        # más (aunque quede una merma pequeña) que quedarse corto de materia prima
        # a medio proceso. flt() por seguridad (get_items_for_material_requests
        # puede regresar Decimal/str según la versión de ERPNext).
        if clean.get("quantity") is not None:
            clean["quantity"] = math.ceil(flt(clean["quantity"]) - 1e-6)
        pp.append("mr_items", clean)


def _fill_po_items_from_costeo(pp, doc, company):
    """Fallback: arma po_items directamente de los productos del costeo (sin OV)."""
    added = 0
    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        qty           = float(producto.qty or 1)
        if not finished_item or qty <= 0:
            continue
        bom_name = (
            frappe.db.get_value("BOM", {"item": finished_item, "is_active": 1,
                                        "is_default": 1, "docstatus": 1, "company": company}, "name")
            # Respaldo sin "is_default", pero SIEMPRE dentro de la compañía del costeo.
            or frappe.db.get_value("BOM", {"item": finished_item, "is_active": 1,
                                           "docstatus": 1, "company": company}, "name")
            or ""
        )
        pp.append("po_items", {
            "item_code":   finished_item,
            "planned_qty": qty,
            "bom_no":      bom_name,
        })
        added += 1
    if not added:
        frappe.throw("No hay productos con cantidad en el costeo.")


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_sales_tax_template(company: str):
    if not company:
        return None
    row = frappe.db.get_value(
        "Sales Taxes and Charges Template",
        {"company": company, "disabled": 0, "is_default": 1},
        "name",
    )
    if row:
        return row
    rows = frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={"company": company, "disabled": 0},
        fields=["name"],
        limit=1,
    )
    return rows[0].name if rows else None


def _aplicar_impuestos_venta(doc, template):
    """Aplica una plantilla de impuestos de venta (IVA) poblando doc.taxes -- fijar
    solo taxes_and_charges no llena la tabla hija (mismo patrón que _aplicar_impuestos_doc,
    versión venta)."""
    doc.taxes = []
    doc.taxes_and_charges = template
    if not template:
        return
    from erpnext.controllers.accounts_controller import get_taxes_and_charges
    for t in get_taxes_and_charges("Sales Taxes and Charges Template", template):
        doc.append("taxes", t)


# ── Documentos ligados y envío ────────────────────────────────────────────────

@frappe.whitelist()
def get_costeo_related(costeo: str, sales_order: str = None) -> dict:
    """Documentos generados a partir del Costeo (cotización, orden de venta, remisión, factura).

    ``sales_order``, si se manda, es la "OV activa" elegida en el SPA -- remisiones y
    factura se filtran por ESA orden en vez de adivinar "la más reciente" (puede haber
    varias OV bajo un mismo Costeo por réplicas de pedidos recurrentes)."""
    out = {"quotation": None, "quotations": [], "sales_order": None, "sales_orders": [], "delivery_notes": [], "delivery_per_delivered": 0, "sales_invoice": None}

    if frappe.db.has_column("Quotation", "costeo"):
        # Un Costeo puede tener varias cotizaciones a lo largo del tiempo (rechazada +
        # nueva, "Cotizar de nuevo", etc.) -- se regresan todas para el acordeón del
        # SPA; "quotation" (singular) se queda como la más reciente, para no romper la
        # lógica de otras fases (Vender, etc.) que asumen "la" cotización vigente.
        rows = frappe.get_all(
            "Quotation",
            filters={"costeo": costeo},
            fields=["name", "status", "docstatus", "grand_total", "currency", "contact_email",
                    "contact_mobile", "selling_price_list", "taxes_and_charges",
                    "valid_till", "payment_terms_template", "tc_name", "custom_tipo_formato",
                    "order_lost_reason", "transaction_date", "creation"],
            order_by="creation desc",
        )
        out["quotations"] = rows
        if rows:
            out["quotation"] = rows[0]

    if frappe.db.has_column("Sales Order", "costeo"):
        # Igual que con Quotation: puede haber varias OV bajo un mismo Costeo (réplicas
        # de un pedido recurrente) -- se regresan todas para el acordeón del SPA;
        # "sales_order" (singular) se queda como la más reciente.
        rows = frappe.get_all(
            "Sales Order",
            filters={"costeo": costeo},
            fields=["name", "status", "docstatus", "grand_total", "currency",
                    "delivery_date", "payment_terms_template", "tc_name", "contact_email",
                    "contact_mobile", "selling_price_list", "taxes_and_charges", "po_no"],
            order_by="creation desc",
        )
        out["sales_orders"] = rows
        if rows:
            out["sales_order"] = rows[0]

    # OV activa para remisiones/factura: la que mandó el SPA si de verdad pertenece a
    # este Costeo, si no la más reciente (mismo comportamiento que antes de existir
    # selección explícita).
    active_so = None
    if sales_order and any(r["name"] == sales_order for r in out["sales_orders"]):
        active_so = sales_order
    elif out["sales_order"]:
        active_so = out["sales_order"]["name"]

    # Notas de remisión ligadas a la OV activa (vía Delivery Note Item.against_sales_order) --
    # puede haber VARIAS (remisiones parciales a distintas direcciones del cliente).
    if active_so:
        dn_parents = list(dict.fromkeys(frappe.get_all(
            "Delivery Note Item",
            filters={"against_sales_order": active_so, "docstatus": ["<", 2]},
            pluck="parent",
        )))
        out["delivery_notes"] = sorted([
            frappe.db.get_value(
                "Delivery Note", p,
                ["name", "status", "docstatus", "posting_date", "grand_total", "shipping_address_name"],
                as_dict=True,
            )
            for p in dn_parents
        ], key=lambda d: d["name"])
        out["delivery_per_delivered"] = flt(
            frappe.db.get_value("Sales Order", active_so, "per_delivered")
        )

    # Factura de venta ligada a la OV activa (vía Sales Invoice Item.sales_order)
    if active_so:
        si_parent = frappe.db.get_value(
            "Sales Invoice Item",
            {"sales_order": active_so, "docstatus": ["<", 2]},
            "parent",
        )
        if si_parent:
            out["sales_invoice"] = frappe.db.get_value(
                "Sales Invoice", si_parent,
                ["name", "status", "docstatus", "grand_total", "currency", "posting_date",
                 "due_date", "payment_terms_template", "tc_name", "contact_email", "contact_mobile"],
                as_dict=True,
            )

    # Reconcilia el estado del costeo con los documentos que EXISTEN realmente:
    # si borraron la cotización/OV desde ERPNext, baja el estado para no dejar
    # el SPA apuntando a un paso cuyo documento ya no existe.
    status = frappe.db.get_value("Costeo", costeo, "costeo_status") or "Borrador"
    new_status = status
    if status == "Cotizado" and not out["quotation"]:
        new_status = "Borrador"
    elif status == "Orden de Venta" and not out["sales_order"]:
        new_status = "Cotizado" if out["quotation"] else "Borrador"
    if new_status != status:
        frappe.db.set_value("Costeo", costeo, "costeo_status", new_status, update_modified=False)
    out["costeo_status"] = new_status

    return out


def _get_cadena_costeo(costeo: str) -> list:
    """Camina el campo amended_from en ambos sentidos -- Costeo funciona como una lista
    enlazada (cada revisión apunta a la anterior), así que no hace falta un doctype
    padre para reconstruir el historial completo, de la primera versión a la última."""
    chain_before = []
    current = costeo
    seen = {costeo}
    while True:
        amended_from = frappe.db.get_value("Costeo", current, "amended_from")
        if not amended_from or amended_from in seen:
            break
        seen.add(amended_from)
        chain_before.insert(0, amended_from)
        current = amended_from

    chain_after = []
    current = costeo
    while True:
        nxt = frappe.db.get_value("Costeo", {"amended_from": current}, "name")
        if not nxt or nxt in seen:
            break
        seen.add(nxt)
        chain_after.append(nxt)
        current = nxt

    all_names = chain_before + [costeo] + chain_after
    rows = frappe.get_all(
        "Costeo",
        filters={"name": ["in", all_names]},
        fields=["name", "docstatus", "motivo_revision", "amended_from", "creation", "costeo_status", "cliente"],
    )
    rows_by_name = {r.name: r for r in rows}
    return [rows_by_name[n] for n in all_names if n in rows_by_name]


@frappe.whitelist()
def get_historial_costeo(costeo: str) -> dict:
    """Historial completo para trazabilidad: todas las revisiones del costeo (de la
    primera a la última) y todas las cotizaciones generadas por cualquiera de esas
    revisiones -- así se ve de un vistazo cómo se llegó al estado actual, aunque haya
    habido rechazos y ajustes en el camino."""
    cadena = _get_cadena_costeo(costeo)
    names = [c["name"] for c in cadena] or [costeo]

    cotizaciones = []
    if frappe.db.has_column("Quotation", "costeo"):
        cotizaciones = frappe.get_all(
            "Quotation",
            filters={"costeo": ["in", names]},
            fields=["name", "status", "docstatus", "order_lost_reason", "creation", "grand_total", "costeo"],
            order_by="creation asc",
        )

    return {"cadena": cadena, "cotizaciones": cotizaciones}


@frappe.whitelist()
def preparar_produccion(costeo: str, sales_order: str = None) -> dict:
    """Ejecuta toda la preparación de producción en un paso (idempotente por OV):
    BOMs → Subcontracting BOMs → Plan → Solicitud de material → OC de subcontratación → Work Orders.

    BOMs/Subcontracting BOMs son por producto, no por OV, así que se comparten entre
    todas las OV de un mismo costeo. El Plan sí es por OV: solo se salta si YA existe un
    plan para esta OV específica (no basta con que exista alguno para el costeo -- otra
    OV pudo haber creado el suyo antes)."""
    existing = get_produccion_docs(costeo, sales_order)
    steps = []

    def run(label, fn, skip=False):
        if skip:
            steps.append({"label": label, "ok": True, "skipped": True, "detail": "Ya existía"})
            return
        try:
            r = fn() or {}
            created = r.get("created") or r.get("purchase_orders") or ([r.get("name")] if r.get("name") else [])
            errors = r.get("errors") or []
            detail = f"{len(created)} creado(s)"
            if errors:
                detail += f", {len(errors)} con aviso"
            steps.append({"label": label, "ok": not errors, "skipped": False, "detail": detail, "errors": errors})
        except Exception as e:
            steps.append({"label": label, "ok": False, "skipped": False, "detail": str(e), "errors": [str(e)]})

    # La automatización llega SOLO hasta el Production Plan. Los demás documentos
    # (solicitud de material, órdenes de trabajo, subcontratación) se generan DESDE
    # el plan, después de validarlo, para que queden asociados a él.
    # Los sub-ensamblajes (resultado de cada operación intermedia, sintético cuando
    # fusiona varios servicios) tienen que existir como Item antes de armar sus BOMs.
    # Es idempotente -- el frontend ya lo llama, esto cubre la llamada directa.
    run("Sub-ensamblajes", lambda: auto_materializar_subensamblajes(costeo))
    run("BOMs", lambda: crear_boms_spa(costeo))
    run("Subcontracting BOMs", lambda: crear_subcontracting_bom(costeo))
    run(
        "Plan de producción",
        lambda: desbloquear_plan_produccion(costeo, sales_order),
        skip=bool(existing.get("plan")),
    )

    # Solo se marca "En Producción" si de verdad se lograron crear (o ya existían)
    # los documentos base -- si algún paso falló (ver step["ok"]), avanzar el
    # estatus igual daría la falsa impresión de que la producción ya quedó
    # preparada cuando en realidad no hay BOMs/plan reales detrás.
    ok = all(s["ok"] for s in steps)
    if ok:
        frappe.db.set_value("Costeo", costeo, "costeo_status", "En Producción")
    return {"steps": steps, "ok": ok}


@frappe.whitelist()
def get_produccion_docs(costeo: str, sales_order: str = None) -> dict:
    """Documentos de producción ligados al costeo, agrupados para el panel.

    ``sales_order``, si se manda, es la OV activa elegida en el SPA -- el plan, las
    solicitudes de material y las OC (materiales y maquila) se filtran a SOLO lo que
    corresponde a esa OV en vez de mostrar todo lo del costeo mezclado (puede haber
    varias OV -- réplicas de pedidos recurrentes -- cada una con su propia producción)."""
    def parents_by_so(child_doctype, so):
        return list(dict.fromkeys(
            frappe.get_all(child_doctype, filters={"sales_order": so}, pluck="parent")
        ))

    def q(dt, fields, so_child=None):
        if not frappe.db.has_column(dt, "costeo"):
            return []
        filters = {"costeo": costeo}
        if sales_order:
            if dt == "Work Order":
                filters["sales_order"] = sales_order
            elif so_child:
                names = parents_by_so(so_child, sales_order)
                if not names:
                    return []
                filters["name"] = ["in", names]
        return frappe.get_all(dt, filters=filters, fields=fields, order_by="creation desc")

    if sales_order:
        plan_name = _get_plan_for_so(costeo, sales_order)
        plan = frappe.get_all(
            "Production Plan", filters={"name": plan_name}, fields=["name", "status", "docstatus"]
        ) if plan_name else []
    else:
        plan = q("Production Plan", ["name", "status", "docstatus"])

    mrs = q("Material Request", ["name", "status", "docstatus", "material_request_type"],
            so_child="Material Request Item")
    pos = q("Purchase Order", ["name", "status", "docstatus", "supplier", "supplier_name",
                               "grand_total", "currency", "is_subcontracted", "per_received"],
            so_child="Purchase Order Item")
    wos = q("Work Order", ["name", "status", "docstatus", "production_item", "qty", "produced_qty"])

    compras = [p for p in pos if not p.get("is_subcontracted")]
    maquila = [p for p in pos if p.get("is_subcontracted")]

    receipts = []
    po_names = [p["name"] for p in pos]
    if po_names:
        rows = frappe.get_all("Purchase Receipt Item",
                              filters={"purchase_order": ["in", po_names]},
                              fields=["parent"], distinct=True)
        rnames = list({r["parent"] for r in rows})
        if rnames:
            receipts = frappe.get_all("Purchase Receipt", filters={"name": ["in", rnames]},
                                      fields=["name", "status", "docstatus"], order_by="creation desc")

    return {
        "plan": plan[0] if plan else None,
        "material_requests": mrs,
        "compras": compras,
        "maquila": maquila,
        "work_orders": wos,
        "receipts": receipts,
    }


@frappe.whitelist()
def get_plan_detail(costeo: str, sales_order: str = None) -> dict:
    """Detalle del Production Plan ligado al costeo, para el panel Producir.

    ``sales_order``, si se manda, es la OV activa -- se busca el plan de ESA OV en vez
    del más reciente del costeo."""
    plan_name = None
    if sales_order:
        plan_name = _get_plan_for_so(costeo, sales_order)
    elif frappe.db.has_column("Production Plan", "costeo"):
        rows = frappe.get_all("Production Plan", filters={"costeo": costeo},
                              fields=["name"], order_by="creation desc", limit=1)
        plan_name = rows[0].name if rows else None
    if not plan_name:
        return {"plan": None}

    pp = frappe.get_doc("Production Plan", plan_name)
    return {"plan": {
        "name": pp.name,
        "docstatus": pp.docstatus,
        "status": pp.status,
        "for_warehouse": pp.for_warehouse,
        "sales_order": pp.sales_orders[0].sales_order if pp.get("sales_orders") else None,
        "total_planned_qty": pp.total_planned_qty,
        "po_items": [{"name": r.name, "item_code": r.item_code, "planned_qty": r.planned_qty, "bom_no": r.bom_no,
                      "planned_qty_original": r.get("planned_qty_original") or r.planned_qty,
                      "planned_start_date": r.planned_start_date, "sales_order": r.sales_order}
                     for r in pp.get("po_items") or []],
        "sub_assembly_items": [{"production_item": r.production_item, "qty": r.qty,
                                "type_of_manufacturing": r.type_of_manufacturing, "supplier": r.supplier}
                               for r in pp.get("sub_assembly_items") or []],
        "mr_items": [{"item_code": r.item_code, "quantity": r.quantity, "warehouse": r.warehouse, "uom": r.uom}
                     for r in pp.get("mr_items") or []],
    }}


_QTY_TOLERANCIA_PCT = 0.05  # margen máximo permitido para "producir/comprar de más"


@frappe.whitelist()
def guardar_plan(plan: str, for_warehouse: str = None, items=None) -> dict:
    """``items``, si se manda, edita la cantidad a PRODUCIR de cada producto del plan
    (po_items.planned_qty) -- permite planear hasta un 5% más de lo que en realidad
    se necesita (para imprevistos: piezas defectuosas, muestras, etc.), nunca más.
    Como todo lo que sigue (sub-ensambles, Solicitud de Material, OC de
    subcontratación) sale de esta cantidad, subirla aquí es lo único que hace falta
    para que ese margen se refleje en TODO el flujo de producción sin tener que
    repetirlo lote por lote ni documento por documento."""
    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 0:
        frappe.throw(_("El plan ya está validado."))
    if for_warehouse:
        pp.for_warehouse = for_warehouse

    cambio_qty = False
    if items:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows if r.get("name")}
        has_original = frappe.db.has_column("Production Plan Item", "planned_qty_original")
        for it in pp.get("po_items") or []:
            r = by_name.get(it.name)
            if not r or r.get("planned_qty") is None:
                continue
            nueva_qty = flt(r.get("planned_qty"))
            original = (flt(it.get("planned_qty_original")) if has_original else 0) or flt(it.planned_qty)
            limite = original * (1 + _QTY_TOLERANCIA_PCT)
            if nueva_qty > limite + 0.001:
                frappe.throw(_(
                    "La cantidad a producir de {0} ({1}) excede el máximo permitido -- hasta 5% más de lo requerido ({2})."
                ).format(it.item_code, nueva_qty, round(limite, 2)))
            if abs(nueva_qty - flt(it.planned_qty)) > 0.001:
                it.planned_qty = nueva_qty
                cambio_qty = True

    if cambio_qty and pp.for_warehouse:
        # Recalcula sub-ensambles y materiales según la nueva cantidad -- si no, la
        # Solicitud de Material seguiría reflejando la cantidad vieja aunque aquí ya
        # se haya subido el plan.
        try:
            pp.get_sub_assembly_items()
        except Exception:
            pass
        _fill_mr_items_from_inventory(pp, pp.for_warehouse)

    pp.flags.ignore_permissions = True
    pp.save()
    return {"name": pp.name}


@frappe.whitelist()
def plan_obtener_materias_primas(plan: str, warehouse: str = None) -> dict:
    """Re-ejecuta 'Obtener materias primas para comprar' sobre un plan en borrador."""
    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 0:
        frappe.throw(_("El plan ya está validado."))
    if warehouse:
        pp.for_warehouse = warehouse
    _fill_mr_items_from_inventory(pp, pp.for_warehouse)
    pp.flags.ignore_permissions = True
    pp.save()
    return {"name": pp.name, "mr_items": len(pp.get("mr_items") or [])}


@frappe.whitelist()
def plan_crear_solicitud_material(plan: str) -> dict:
    """Crea las Solicitudes de Material DESDE el plan (nativo, quedan asociadas) y
    pre-llena el PROVEEDOR por materia prima tomándolo del Costeo (como la versión Desk),
    para habilitar la creación de una OC por proveedor."""
    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 1:
        frappe.throw(_("Valida el plan primero."))
    pp.make_material_request()
    mrs = list(dict.fromkeys(
        frappe.get_all("Material Request Item", filters={"production_plan": plan}, pluck="parent")
    ))
    # make_material_request() es el mapper nativo de ERPNext -- no conoce el campo
    # custom 'costeo', así que hay que ponerlo aparte (igual que crear_solicitud_material)
    # para que la Solicitud quede vinculada al Costeo y aparezca en su detalle/listas.
    if pp.get("costeo") and mrs and frappe.db.has_column("Material Request", "costeo"):
        for mr_name in mrs:
            frappe.db.set_value("Material Request", mr_name, "costeo", pp.get("costeo"))
    _asignar_proveedores_a_mrs(pp.get("costeo"), mrs)
    # Guarda la cantidad EXACTA calculada (antes de que alguien la edite) -- es la
    # base contra la que se valida el margen de "hasta 5% más" al guardar la solicitud.
    if mrs and frappe.db.has_column("Material Request Item", "qty_original"):
        for mr_name in mrs:
            for it in frappe.get_all("Material Request Item", filters={"parent": mr_name}, fields=["name", "qty"]):
                frappe.db.set_value("Material Request Item", it.name, "qty_original", it.qty, update_modified=False)
    return {"ok": True, "material_requests": mrs}


def _asignar_proveedores_a_mrs(costeo, mr_names):
    """Pone el proveedor en cada línea de materia prima: primero el del Costeo
    (costeo_producto_detalle, tipo Materia Prima), luego el proveedor por defecto del Item."""
    if not costeo or not mr_names or not frappe.db.has_column("Material Request Item", "supplier"):
        return
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _build_raw_material_supplier_map

    doc = frappe.get_doc("Costeo", costeo)
    supplier_map = _build_raw_material_supplier_map(doc.as_dict())
    company = doc.get("compañia")

    for mr_name in mr_names:
        items = frappe.get_all("Material Request Item", filters={"parent": mr_name},
                               fields=["name", "item_code", "supplier"])
        for it in items:
            if it.supplier:
                continue
            sup = (
                supplier_map.get(it.item_code)
                or frappe.db.get_value("Item Default", {"parent": it.item_code, "company": company}, "default_supplier")
                or frappe.db.get_value("Item Default", {"parent": it.item_code}, "default_supplier")
            )
            if sup:
                frappe.db.set_value("Material Request Item", it.name, "supplier", sup, update_modified=False)
    frappe.db.commit()


@frappe.whitelist()
def get_solicitud_material(plan: str) -> dict:
    """MR(s) ligadas al plan + detalle de la principal, para la pestaña Solicitud de material."""
    mr_names = list(dict.fromkeys(
        frappe.get_all("Material Request Item", filters={"production_plan": plan}, pluck="parent")
    ))
    if not mr_names:
        return {"material_requests": [], "detail": None}

    has_sup = frappe.db.has_column("Material Request Item", "supplier")
    has_rate = frappe.db.has_column("Material Request Item", "rate")
    mrs = frappe.get_all(
        "Material Request", filters={"name": ["in", mr_names]},
        fields=["name", "status", "docstatus", "material_request_type", "transaction_date", "schedule_date"],
        order_by="creation asc",
    )
    primary = frappe.get_doc("Material Request", mr_names[0])
    detail = {
        "name": primary.name,
        "docstatus": primary.docstatus,
        "status": primary.status,
        "material_request_type": primary.material_request_type,
        "transaction_date": str(primary.transaction_date) if primary.transaction_date else "",
        "schedule_date": str(primary.schedule_date) if primary.schedule_date else "",
        "company": primary.company,
        "items": [{
            "name": it.name, "item_code": it.item_code, "item_name": it.item_name,
            "qty": it.qty, "uom": it.uom, "conversion_factor": flt(it.conversion_factor) or 1,
            "warehouse": it.warehouse,
            "supplier": (it.get("supplier") if has_sup else ""),
            "rate": (it.get("rate") if has_rate else 0),
            "qty_original": it.get("qty_original") or it.qty,
        } for it in primary.items],
    }
    detail["linked_ocs"] = list(dict.fromkeys(
        frappe.get_all("Purchase Order Item", filters={"material_request": primary.name}, pluck="parent")
    ))
    detail["linked_rfqs"] = list(dict.fromkeys(
        frappe.get_all("Request for Quotation Item", filters={"material_request": primary.name}, pluck="parent")
    ))
    detail["linked_sqs"] = list(dict.fromkeys(
        frappe.get_all("Supplier Quotation Item", filters={"material_request": primary.name}, pluck="parent")
    ))
    return {"material_requests": mrs, "detail": detail}


def _uom_conversion_factor(item_code, uom, stock_uom=None):
    """Factor de conversión de `uom` a la UDM de almacén del artículo -- SOLO si `uom`
    es la propia stock_uom o una conversión ya dada de alta en el artículo (Item.uoms,
    ver item_api.save_item_uoms/get_item_uoms). None si esa UDM no está permitida para
    este artículo -- así el cambio de UDM en Solicitud de Material nunca inventa una
    conversión que no se haya capturado ahí."""
    stock_uom = stock_uom or frappe.db.get_value("Item", item_code, "stock_uom")
    if uom == stock_uom:
        return 1.0
    factor = frappe.db.get_value(
        "UOM Conversion Detail", {"parent": item_code, "parenttype": "Item", "uom": uom}, "conversion_factor"
    )
    return flt(factor) if factor else None


@frappe.whitelist()
def guardar_solicitud_material(mr: str, items=None, schedule_date=None) -> dict:
    """Guarda ediciones de la MR en borrador (proveedor/precio/cantidad por línea,
    fecha). El precio manual (si se captura) se respeta al generar la OC en lugar del
    que se jalaría solo de la cotización de proveedor / última compra -- ver mr_crear_oc.

    La cantidad se puede mover hasta un 5% de lo que en realidad se necesita
    (qty_original, capturada al crear la solicitud) -- de más (mermas/control de
    calidad) o de menos (ej. comprar en múltiplos/rollos cerrados) -- sin dejar que se
    dispare a lo que sea.

    La UDM de la Solicitud NO se puede cambiar aquí -- la Solicitud representa el total
    que de verdad se necesita, tal como sale del costeo, igual para cualquier proveedor.
    El ajuste de UDM al proveedor real (que puede vender en una unidad distinta) se hace
    en la Orden de Compra que se genera desde esta MR (ver guardar_documento_compra),
    donde sí se permite libremente, sin exigir que esa UDM ya esté dada de alta para el
    artículo -- ahí es el proveedor específico el que manda, no el catálogo interno."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 0:
        frappe.throw(_("La solicitud ya está validada; no se puede editar."))
    if schedule_date:
        doc.schedule_date = schedule_date
    if items:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows if r.get("name")}
        has_sup = frappe.db.has_column("Material Request Item", "supplier")
        has_rate = frappe.db.has_column("Material Request Item", "rate")
        has_original = frappe.db.has_column("Material Request Item", "qty_original")
        for it in doc.items:
            r = by_name.get(it.name)
            if not r:
                continue
            # La UDM de la Solicitud YA NO se puede cambiar aquí -- la Solicitud es el
            # total que de verdad se necesita, tal como sale del costeo, y cambiarla por
            # línea complicaba de más esta pantalla. El lugar correcto para ajustar la
            # UDM al proveedor real (que puede vender en una unidad distinta) es la
            # Orden de Compra que se genera desde aquí -- ver guardar_documento_compra,
            # que sí permite cambiarla libremente mientras la OC siga en borrador.
            # Cualquier "uom" que llegue en el payload simplemente se ignora.
            if r.get("qty") is not None:
                nueva_qty = flt(r.get("qty"))
                original = (flt(it.get("qty_original")) if has_original else 0) or flt(it.qty)
                limite_sup = original * (1 + _QTY_TOLERANCIA_PCT)
                limite_inf = original * (1 - _QTY_TOLERANCIA_PCT)
                if nueva_qty > limite_sup + 0.001 or nueva_qty < limite_inf - 0.001:
                    frappe.throw(_(
                        "La cantidad de {0} ({1}) se sale del margen permitido -- hasta 5% de más o de menos de lo requerido ({2} a {3})."
                    ).format(it.item_code, nueva_qty, round(limite_inf, 2), round(limite_sup, 2)))
                it.qty = nueva_qty
            if has_sup:
                it.supplier = r.get("supplier") or None
            if has_rate:
                it.rate = flt(r.get("rate")) or None
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


def _precio_para_oc(item_code, supplier, company=None):
    """Precio para la OC: si hay Presupuesto de Proveedor (Supplier Quotation) del MISMO
    proveedor para el item, usa ese; si no, el precio de lista / última compra."""
    if supplier:
        # Solo presupuestos de proveedor VALIDADOS (docstatus 1) sobrescriben el precio de
        # lista; los borradores son tentativos y no deben afectar la OC.
        sq_rows = frappe.get_all(
            "Supplier Quotation Item",
            filters={"item_code": item_code, "docstatus": 1},
            fields=["rate", "parent"],
            order_by="creation desc",
        )
        for r in sq_rows:
            if not r.rate:
                continue
            if frappe.db.get_value("Supplier Quotation", r.parent, "supplier") == supplier:
                return flt(r.rate)
    from costeo_yelke.api.costeo_template_api import _get_buying_rate
    return _get_buying_rate(item_code, supplier)


def _aplicar_impuestos_doc(doc):
    """Aplica la plantilla de impuestos de compra (IVA México) si el doc aún no tiene impuestos."""
    if doc.get("taxes"):
        return False
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _get_purchase_tax_template
    from erpnext.controllers.accounts_controller import get_taxes_and_charges
    template = _get_purchase_tax_template(doc.company)
    if not template:
        return False
    doc.taxes_and_charges = template
    for t in get_taxes_and_charges("Purchase Taxes and Charges Template", template):
        doc.append("taxes", t)
    return True


def _aplicar_precios_oc(po_names):
    for po_name in po_names:
        po = frappe.get_doc("Purchase Order", po_name)
        if po.docstatus != 0:
            continue
        changed = False
        for it in po.items:
            precio = _precio_para_oc(it.item_code, po.supplier, po.company)
            if precio is not None and flt(precio) != flt(it.rate):
                it.rate = flt(precio)
                changed = True
        if _aplicar_impuestos_doc(po):
            changed = True
        if changed:
            po.flags.ignore_permissions = True
            po.save()  # recalcula totales e impuestos


def _aplicar_rate_manual_mr(mr_doc, pos):
    """Si el usuario capturó un precio manual por material en la Solicitud (porque el
    proveedor por defecto le quedó mal y ajustó costo/proveedor ahí), ese precio gana
    sobre el que _aplicar_precios_oc jaló automáticamente (cotización/última compra)."""
    if not frappe.db.has_column("Material Request Item", "rate"):
        return
    rate_by_item = {r.item_code: flt(r.rate) for r in mr_doc.items if flt(r.get("rate"))}
    if not rate_by_item:
        return
    for po_name in pos:
        po = frappe.get_doc("Purchase Order", po_name)
        if po.docstatus != 0:
            continue
        changed = False
        for it in po.items:
            r = rate_by_item.get(it.item_code)
            if r and flt(it.rate) != r:
                it.rate = r
                changed = True
        if changed:
            po.flags.ignore_permissions = True
            po.save()


@frappe.whitelist()
def mr_crear_oc(mr: str, items=None, schedule_date=None, lote_ref: str = None) -> dict:
    """Crea Orden(es) de Compra desde la MR (una OC por proveedor) y jala el precio:
    primero el manual capturado en la Solicitud (si lo hay), si no del Presupuesto de
    Proveedor, si no de la lista de precios (última compra).

    Sin `items`, mapea todo el saldo pendiente de la MR (comportamiento nativo). Con
    `items` ([{item_code, qty}]), crea un LOTE parcial: cada OC generada se recorta a
    solo esos materiales y esas cantidades -- se puede llamar varias veces mientras
    quede saldo, para escalonar la compra de materia prima en tandas (igual patrón que
    las Órdenes de Subcontratación parciales). ERPNext solo actualiza el saldo
    comprometido de la MR al VALIDAR la OC, así que a partir del segundo lote siempre
    hay que indicar `items` explícitamente -- si no, podría volver a mapear el saldo
    completo mientras el lote anterior siga en borrador.

    `schedule_date` (opcional): fecha requerida de este lote -- se aplica a la OC y a
    cada una de sus líneas. `lote_ref` (opcional) correlaciona esta OC con el lote de
    subcontratación del mismo nombre (ver get_lotes_produccion)."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))

    existing_po_items = frappe.get_all(
        "Purchase Order Item", filters={"material_request": mr, "docstatus": ["<", 2]},
        fields=["item_code", "qty"],
    )
    if not items and existing_po_items:
        frappe.throw(_(
            "Ya existe una orden de compra para esta solicitud. Indica la cantidad del nuevo lote."
        ))

    qty_by_item = None
    if items:
        rows = json.loads(items) if isinstance(items, str) else items
        qty_by_item = {r.get("item_code"): flt(r.get("qty")) for r in rows if r.get("item_code")}
        comprometido = {}
        for r in existing_po_items:
            comprometido[r.item_code] = comprometido.get(r.item_code, 0) + flt(r.qty)
        # Un mismo artículo puede tener VARIAS líneas en la MR (una por lote, tras
        # mr_dividir_en_lotes) -- el saldo disponible es la SUMA de todas esas líneas,
        # no la de una sola (si no, un lote se comparaba contra el tamaño de otro).
        total_mr = {}
        for it in doc.items:
            if it.item_code in qty_by_item:
                total_mr[it.item_code] = total_mr.get(it.item_code, 0) + flt(it.qty)
        for item_code, qty in qty_by_item.items():
            disponible = total_mr.get(item_code, 0) - comprometido.get(item_code, 0)
            if qty > disponible + 0.001:
                frappe.throw(_(
                    "La cantidad para {0} ({1}) excede el saldo pendiente de la solicitud ({2})."
                ).format(item_code, qty, disponible))

    from costeo_yelke.overrides.material_request import make_purchase_order

    pos_antes = set(frappe.get_all("Purchase Order Item", filters={"material_request": mr}, pluck="parent"))
    result = make_purchase_order(mr)
    pos_despues = list(dict.fromkeys(
        frappe.get_all("Purchase Order Item", filters={"material_request": mr}, pluck="parent")
    ))
    pos = [p for p in pos_despues if p not in pos_antes]
    if not pos and result is not None:
        try:
            result.flags.ignore_permissions = True
            result.insert()
            pos = [result.name]
        except Exception:
            pass

    if qty_by_item:
        final_pos = []
        for po_name in pos:
            po = frappe.get_doc("Purchase Order", po_name)
            # El mapeador nativo crea una línea de OC por cada línea de la MR -- si el
            # mismo artículo aparece en varias líneas de la MR (ej. una por lote, tras
            # mr_dividir_en_lotes), aquí saldrían varias líneas duplicadas del mismo
            # artículo. Se conserva solo UNA por artículo, con la cantidad del lote.
            kept = []
            seen = set()
            for it in po.items:
                if it.item_code not in qty_by_item or it.item_code in seen:
                    continue
                q = qty_by_item[it.item_code]
                if q <= 0:
                    continue
                it.qty = q
                kept.append(it)
                seen.add(it.item_code)
            if not kept:
                frappe.delete_doc("Purchase Order", po_name, force=True, ignore_permissions=True)
                continue
            po.set("items", kept)
            po.flags.ignore_permissions = True
            po.save()
            final_pos.append(po_name)
        pos = final_pos

    _aplicar_precios_oc(pos)
    _aplicar_rate_manual_mr(doc, pos)

    if schedule_date:
        for po_name in pos:
            po = frappe.get_doc("Purchase Order", po_name)
            if po.docstatus != 0:
                continue
            po.schedule_date = schedule_date
            for it in po.items:
                it.schedule_date = schedule_date
            po.flags.ignore_permissions = True
            po.save()

    # ligar las OC al costeo (trazabilidad)
    plan = frappe.db.get_value("Material Request Item", {"parent": mr}, "production_plan")
    costeo = frappe.db.get_value("Production Plan", plan, "costeo") if plan else None
    if costeo and frappe.db.has_column("Purchase Order", "costeo"):
        for po in pos:
            frappe.db.set_value("Purchase Order", po, "costeo", costeo, update_modified=False)
    if lote_ref and frappe.db.has_column("Purchase Order", "lote_ref"):
        for po in pos:
            frappe.db.set_value("Purchase Order", po, "lote_ref", lote_ref, update_modified=False)
    frappe.db.commit()
    return {"ok": True, "purchase_orders": pos}


@frappe.whitelist()
def mr_crear_ocs_por_lotes(mr: str, lotes) -> dict:
    """Genera de un jalón varias Órdenes de Compra, una por lote, cada una con su
    propia fecha requerida -- para cuando ya se definieron los lotes de entrega ANTES
    de validar la solicitud (en vez de ir creando 'Nuevo lote' uno por uno después).

    `lotes`: [{"schedule_date": "2026-01-01", "lote_ref": "Lote 1", "items": [{"item_code","qty"}, ...]}, ...]
    Se procesan en el orden recibido -- cada llamada a mr_crear_oc ya valida que no se
    exceda el saldo pendiente de la solicitud. `lote_ref` es opcional; si se manda,
    correlaciona esa OC con el lote de subcontratación del mismo nombre."""
    rows = json.loads(lotes) if isinstance(lotes, str) else lotes
    purchase_orders = []
    for lote in rows:
        items = lote.get("items") or []
        if not items:
            continue
        r = mr_crear_oc(
            mr, items=json.dumps(items), schedule_date=lote.get("schedule_date") or None,
            lote_ref=lote.get("lote_ref") or None,
        )
        purchase_orders.extend(r.get("purchase_orders") or [])
    return {"ok": True, "purchase_orders": purchase_orders}


@frappe.whitelist()
def mr_dividir_en_lotes(mr: str, lotes) -> dict:
    """Divide las líneas de la MR (todavía en BORRADOR) en una fila por lote, cada
    una etiquetada con lote_ref -- a diferencia de mr_crear_ocs_por_lotes, esto NO
    crea ninguna Orden de Compra: la OC de cada lote se genera después, desde su
    propia pantalla (mr_generar_oc_lote), justo antes de comprometerse, por si algo
    cambió mientras tanto (precio de un presupuesto de proveedor, cantidad, etc.).

    `lotes`: [{"schedule_date": "2026-01-01", "lote_ref": "Lote 1", "items": [{"item_code","qty"}, ...]}, ...]
    Materiales que no queden en ningún lote se quedan como una fila normal, sin
    lote_ref -- disponibles para comprarse fuera del flujo de lotes si hace falta."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 0:
        frappe.throw(_("La solicitud ya está validada."))
    rows = json.loads(lotes) if isinstance(lotes, str) else lotes

    asignado = {}
    for lote in rows:
        for item in lote.get("items") or []:
            code = item.get("item_code")
            asignado[code] = asignado.get(code, 0) + flt(item.get("qty"))

    originals = [it.as_dict() for it in doc.items]
    doc.items = []

    def _append_row(base, qty, lote_ref=None, schedule_date=None):
        new_row = {k: v for k, v in base.items() if k not in ("name", "idx", "doctype", "parent", "parentfield", "parenttype")}
        new_row["qty"] = qty
        if lote_ref:
            new_row["lote_ref"] = lote_ref
        if schedule_date:
            new_row["schedule_date"] = schedule_date
        doc.append("items", new_row)

    for lote in rows:
        for item in lote.get("items") or []:
            qty = flt(item.get("qty"))
            if qty <= 0:
                continue
            base = next((r for r in originals if r.get("item_code") == item.get("item_code")), None)
            if not base:
                continue
            _append_row(base, qty, lote_ref=lote.get("lote_ref"), schedule_date=lote.get("schedule_date"))

    for base in originals:
        restante = flt(base.get("qty")) - asignado.get(base.get("item_code"), 0)
        if restante > 0.001:
            _append_row(base, restante)

    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def mr_generar_oc_lote(mr: str, lote_ref: str, supplier: str = None) -> dict:
    """Genera la Orden de Compra de UN lote específico (ya dividido por
    mr_dividir_en_lotes), con la cantidad y fecha que ya se capturaron al definir
    el lote -- se dispara desde la pantalla de ese lote, no automáticamente. Si se
    indica `supplier`, sólo genera la OC de ESE proveedor (su propio botón, junto a
    los de Solicitud de cotización / Presupuesto), sin tocar los demás."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))
    rows = [it for it in doc.items if it.get("lote_ref") == lote_ref and (not supplier or it.get("supplier") == supplier)]
    if not rows:
        frappe.throw(_("No hay materiales asignados a {0} en esta solicitud.").format(lote_ref))
    items = [{"item_code": r.item_code, "qty": r.qty} for r in rows]
    schedule_date = next((str(r.schedule_date) for r in rows if r.schedule_date), None)
    return mr_crear_oc(mr, items=json.dumps(items), schedule_date=schedule_date, lote_ref=lote_ref)


@frappe.whitelist()
def oc_jalar_precios(po: str) -> dict:
    """Re-jala los precios de una OC en borrador (Presupuesto de Proveedor → lista de precios)."""
    doc = frappe.get_doc("Purchase Order", po)
    if doc.docstatus != 0:
        frappe.throw(_("La OC ya está validada; no se puede editar."))
    _aplicar_precios_oc([po])
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def get_recibos(plan: str) -> dict:
    """OC validadas (materia prima) ligadas al plan + sus recibos de compra.

    Filtra por 'sales_order' en la línea de la OC (no 'production_plan'): el mapeador
    nativo que crea la OC de materiales desde la Solicitud (ver
    costeo_yelke/overrides/material_request.py) copia sales_order/sales_order_item de
    la línea de la MR, pero NUNCA copia production_plan -- filtrar por production_plan
    aquí dejaría el panel de Recibos vacío siempre. Se resuelve la OV del plan (vía la
    tabla nativa Production Plan Sales Order) y se filtra por esa OV; si el plan no está
    ligado a ninguna OV (plan armado directo del costeo, sin OV), cae a costeo completo."""
    sales_order = frappe.db.get_value("Production Plan Sales Order", {"parent": plan}, "sales_order")
    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    if sales_order:
        po_names = list(dict.fromkeys(
            frappe.get_all("Purchase Order Item", filters={"sales_order": sales_order}, pluck="parent")
        ))
    elif costeo and frappe.db.has_column("Purchase Order", "costeo"):
        po_names = frappe.get_all("Purchase Order", filters={"costeo": costeo, "is_subcontracted": 0}, pluck="name")
    else:
        po_names = []
    ocs = []
    if po_names:
        rows = frappe.get_all(
            "Purchase Order",
            filters={"name": ["in", po_names], "is_subcontracted": 0, "docstatus": 1},
            fields=["name", "supplier", "supplier_name", "status", "per_received", "grand_total"],
            order_by="creation desc",
        )
        for o in rows:
            o["receipts"] = list(dict.fromkeys(
                frappe.get_all("Purchase Receipt Item", filters={"purchase_order": o.name}, pluck="parent")
            ))
            ocs.append(o)
    return {"ocs": ocs}


@frappe.whitelist()
def crear_recibo_oc(po: str) -> dict:
    """Crea el Recibo de Compra desde la OC (entrada a inventario), poniendo el almacén
    de materias primas del costeo y asegurando los impuestos de compra (IVA). Si ya
    existe un recibo (borrador o validado) para esta OC lo regresa en vez de crear uno
    duplicado -- se dispara solo al validar la OC, así que debe ser segura de llamar
    más de una vez."""
    po_doc = frappe.get_doc("Purchase Order", po)
    if po_doc.docstatus != 1:
        frappe.throw(_("Valida la orden de compra primero."))

    existing_names = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": po}, pluck="parent")
    if existing_names:
        existing = frappe.get_all(
            "Purchase Receipt", filters={"name": ["in", existing_names], "docstatus": ["<", 2]},
            fields=["name"], order_by="creation desc", limit=1,
        )
        if existing:
            return {"ok": True, "name": existing[0]["name"]}

    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

    pr = make_purchase_receipt(po)
    costeo = po_doc.get("costeo")
    wh = frappe.db.get_value("Costeo", costeo, "almacen_materias_primas") if costeo else None
    if wh:
        pr.set_warehouse = wh
        for it in pr.items:
            it.warehouse = wh
    _aplicar_impuestos_doc(pr)  # el PR normalmente hereda impuestos de la OC; aseguramos

    pr.flags.ignore_permissions = True
    pr.flags.ignore_mandatory = True
    pr.insert()
    return {"ok": True, "name": pr.name}


_OM_GENERAL = ["om_modelo", "om_tela", "om_color", "om_color_principal", "om_forro", "om_combinacion",
               "om_fecha_requerida", "om_ubicacion", "om_aberturas", "om_bordado", "om_estampado",
               "om_sublimado", "om_reflejante", "om_observaciones",
               "om_prendas_caballero_total", "om_prendas_dama_total"]
_OM_CAB = ["t28", "t30", "t32", "t34", "t36", "t40", "t42", "t44"]
_OM_DAMA = ["t5", "t7", "t9", "t11", "t13", "t15", "t17"]


def _om_decode_tables(doc):
    """Decodifica om_tablas_flexibles (formato meta/celda de ERPNext) a una
    estructura amigable para el SPA: [{name, unit, columns:[id], rows:[{id, cells:{col:val}}]}]."""
    grouped, order = {}, []
    for row in doc.get("om_tablas_flexibles") or []:
        tname = (row.tabla or "").strip() or "Tabla sin nombre"
        if tname not in grouped:
            grouped[tname] = {"name": tname, "unit": row.unidad or "", "columns": [], "rows": [], "row_map": {}, "layout": None}
            order.append(tname)
        b = grouped[tname]
        if not b["unit"] and row.unidad:
            b["unit"] = row.unidad
        if (row.fila or "") == "__meta__" and (row.columna or "") == "__layout__":
            try:
                b["layout"] = json.loads(row.valor or "{}") or {}
            except Exception:
                b["layout"] = {}
            if b["layout"].get("unidad") and not b["unit"]:
                b["unit"] = b["layout"]["unidad"]
            continue
        rid, cid = (row.fila or "").strip(), (row.columna or "").strip()
        if not rid or not cid:
            continue
        if rid not in b["row_map"]:
            b["row_map"][rid] = {"id": rid, "cells": {}}
            b["rows"].append(b["row_map"][rid])
        if cid not in b["columns"]:
            b["columns"].append(cid)
        b["row_map"][rid]["cells"][cid] = row.valor or ""

    out = []
    for tname in order:
        b = grouped[tname]
        layout = b["layout"] or {}
        lcols = [c for c in (layout.get("columnas") or []) if c]
        lrows = [r for r in (layout.get("filas") or []) if r]
        columns = lcols if lcols else list(b["columns"])
        if not columns:
            columns = ["c1"]
        ordered = []
        for rid in lrows:
            if rid not in ordered:
                ordered.append(rid)
        for r in b["rows"]:
            if r["id"] and r["id"] not in ordered:
                ordered.append(r["id"])
        rows = []
        for rid in ordered:
            rm = b["row_map"].get(rid) or {"id": rid, "cells": {}}
            cells = dict(rm["cells"])
            for c in columns:
                cells.setdefault(c, "")
            rows.append({"id": rid, "cells": cells})
        if not rows:
            rows = [{"id": "r1", "cells": {c: "" for c in columns}}]
        out.append({"name": b["name"], "unit": b["unit"] or "", "columns": columns, "rows": rows})
    return out


def _om_encode_tables(doc, tables):
    """Vuelca la estructura amigable del SPA a om_tablas_flexibles con el formato
    meta/celda que consume ERPNext y el PDF."""
    doc.set("om_tablas_flexibles", [])
    for ti, table in enumerate(tables or []):
        tname = (str(table.get("name") or "").strip()) or f"Tabla {ti + 1}"
        unit = str(table.get("unit") or "")
        columns = [c for c in (table.get("columns") or []) if c] or ["c1"]
        rows = []
        for ri, r in enumerate(table.get("rows") or []):
            rid = (str(r.get("id") or "").strip()) or f"r{ri + 1}"
            rows.append({"id": rid, "cells": r.get("cells") or {}})
        if not rows:
            rows = [{"id": "r1", "cells": {}}]

        doc.append("om_tablas_flexibles", {
            "tabla": tname, "unidad": unit, "fila": "__meta__", "columna": "__layout__",
            "valor": json.dumps({"columnas": columns, "filas": [r["id"] for r in rows], "unidad": unit}),
        })
        for r in rows:
            for c in columns:
                val = r["cells"].get(c)
                val = "" if val is None else str(val)
                if not val:
                    continue
                doc.append("om_tablas_flexibles", {
                    "tabla": tname, "unidad": unit, "fila": r["id"], "columna": c, "valor": val,
                })


def _om_maestra_po(costeo: str):
    """La OC de subcontratación "maestra" del proyecto -- la única desde la que se
    edita la Orden de Manufactura (las demás la heredan solas, ver guardar_om). Se
    define como la PRIMERA OC de subcontratación creada para el costeo: hay una sola
    ficha técnica por proyecto, así que no importa de qué etapa/lote sea, cualquiera
    sirve como fuente -- se fija la primera nomás para tener un criterio único y
    estable.

    Desempate por `name` además de `creation`: cuando las 4 etapas se crean de un
    jalón (plan_crear_subcontratacion crea todas las OC en el mismo request), sus
    timestamps de creación pueden quedar iguales o casi iguales -- sin un segundo
    criterio de orden, MySQL no garantiza cuál "gana" el ORDER BY, así que la
    "maestra" podía salir distinta según cuándo se consultara (síntoma: la ficha
    técnica aparecía editable en una etapa que no debía)."""
    if not costeo:
        return None
    return frappe.db.get_value(
        "Purchase Order", {"costeo": costeo, "is_subcontracted": 1},
        "name", order_by="creation asc, name asc",
    )


def get_om(po: str) -> dict:
    """Campos de la Orden de Manufactura (instrucciones de confección) de una OC subcontratada."""
    doc = frappe.get_doc("Purchase Order", po)
    general = {}
    for f in _OM_GENERAL:
        v = doc.get(f)
        general[f] = str(v) if (f == "om_fecha_requerida" and v) else v

    def child(field, cols):
        out = []
        for r in doc.get(field) or []:
            row = {c: r.get(c) for c in cols}
            row["name"] = r.name
            out.append(row)
        return out

    return {
        "docstatus": doc.docstatus,
        "es_maestra": po == _om_maestra_po(doc.get("costeo")),
        "general": general,
        "tallas_caballero": child("om_tallas_caballero", ["linea"] + _OM_CAB + ["total"]),
        "tallas_dama": child("om_tallas_dama", ["linea"] + _OM_DAMA + ["total"]),
        "procesos": child("om_procesos", ["proceso", "nombre_proceso", "ubicacion", "colores"]),
        "tablas": _om_decode_tables(doc),
        "archivos": [
            {"name": r.name, "archivo": r.archivo, "descripcion": r.descripcion}
            for r in (doc.get("om_archivos") or [])
        ],
    }


def _guardar_om_una(po: str, general=None, tallas_caballero=None, tallas_dama=None, procesos=None, tablas=None, archivos=None) -> str:
    """Guarda la Orden de Manufactura en UNA OC subcontratada. Uso interno -- ver
    guardar_om, que además la replica automáticamente al resto del proyecto (solo
    a las hermanas que sigan en borrador, ver ahí).

    Se permite en borrador O ya validada -- es una ficha técnica de proyecto, no
    parte de los términos comerciales de la OC, así que validar la OC no debe
    bloquearla (los campos om_* tienen allow_on_submit=1, ver patch v0_0_4). Solo
    se bloquea si la OC ya está CANCELADA (docstatus 2): esa ya no representa
    nada vigente."""
    doc = frappe.get_doc("Purchase Order", po)
    if doc.docstatus == 2:
        frappe.throw(_("La orden está cancelada; no se puede editar."))

    if general:
        g = json.loads(general) if isinstance(general, str) else general
        for f, v in g.items():
            if f in _OM_GENERAL and doc.meta.get_field(f):
                doc.set(f, v)

    def set_tallas(field, rows_json, sizes, total_field):
        if rows_json is None:
            return
        rows = json.loads(rows_json) if isinstance(rows_json, str) else rows_json
        doc.set(field, [])
        gran_total = 0
        for r in rows:
            row = {k: v for k, v in r.items() if k != "name"}
            total = sum(int(r.get(s) or 0) for s in sizes)
            row["total"] = total
            gran_total += total
            doc.append(field, row)
        if doc.meta.get_field(total_field):
            doc.set(total_field, gran_total)

    set_tallas("om_tallas_caballero", tallas_caballero, _OM_CAB, "om_prendas_caballero_total")
    set_tallas("om_tallas_dama", tallas_dama, _OM_DAMA, "om_prendas_dama_total")

    if procesos is not None:
        rows = json.loads(procesos) if isinstance(procesos, str) else procesos
        doc.set("om_procesos", [])
        for i, r in enumerate(rows, 1):
            row = {k: v for k, v in r.items() if k != "name"}
            if not row.get("proceso"):
                row["proceso"] = f"Proceso {i}"
            doc.append("om_procesos", row)

    if tablas is not None:
        t = json.loads(tablas) if isinstance(tablas, str) else tablas
        _om_encode_tables(doc, t)

    if archivos is not None:
        a = json.loads(archivos) if isinstance(archivos, str) else archivos
        doc.set("om_archivos", [])
        for r in a:
            doc.append("om_archivos", {"archivo": r.get("archivo"), "descripcion": r.get("descripcion")})

    doc.flags.ignore_permissions = True
    doc.save()
    return doc.get("costeo")


@frappe.whitelist()
def guardar_om(po: str, general=None, tallas_caballero=None, tallas_dama=None, procesos=None, tablas=None, archivos=None) -> dict:
    """Guarda la Orden de Manufactura y la replica sola al resto de OC de
    subcontratación DEL MISMO COSTEO que sigan en borrador -- todas las etapas, todos
    los lotes (comparten la misma OC por etapa) y todas las OV/producciones del
    proyecto. Hay una sola ficha técnica por proyecto, no una por etapa: no hace falta
    volver a capturarla ni copiarla a mano en cada una.

    Sólo se puede editar desde la OC "maestra" (_om_maestra_po) -- las demás la
    reciben ya hecha (el frontend las muestra de solo lectura); esto es sólo el
    candado del lado del servidor, por si acaso."""
    maestra = _om_maestra_po(frappe.db.get_value("Purchase Order", po, "costeo"))
    if maestra and po != maestra:
        frappe.throw(_(
            "La Orden de Manufactura se captura una sola vez, desde {0} -- las demás etapas la heredan solas."
        ).format(maestra))
    costeo = _guardar_om_una(po, general, tallas_caballero, tallas_dama, procesos, tablas, archivos)
    if costeo:
        origen = get_om(po)
        hermanas = frappe.get_all(
            "Purchase Order",
            filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": 0, "name": ["!=", po]},
            pluck="name",
        )
        for p in hermanas:
            _guardar_om_una(
                p,
                general=json.dumps(origen["general"]),
                tallas_caballero=json.dumps(origen["tallas_caballero"]),
                tallas_dama=json.dumps(origen["tallas_dama"]),
                procesos=json.dumps(origen["procesos"]),
                tablas=json.dumps(origen["tablas"]),
                archivos=json.dumps(origen["archivos"]),
            )
    return {"ok": True}


@frappe.whitelist()
def get_subcontratos(plan: str) -> dict:
    """OC de subcontratación (maquila) ligadas al plan.

    Filtra por 'sales_order' en la línea de la OC (mismo criterio que get_recibos, para
    no tener dos campos distintos haciendo el mismo trabajo) -- si el costeo tiene
    varias OV con sus propios planes, cada plan solo ve SUS propias OC de maquila
    (ver plan_crear_subcontratacion, que las etiqueta al crearlas). Sin OV ligada al
    plan, cae a costeo completo."""
    sales_order = frappe.db.get_value("Production Plan Sales Order", {"parent": plan}, "sales_order")
    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    if sales_order:
        po_names = list(dict.fromkeys(
            frappe.get_all("Purchase Order Item", filters={"sales_order": sales_order}, pluck="parent")
        ))
    elif costeo and frappe.db.has_column("Purchase Order", "costeo"):
        po_names = frappe.get_all("Purchase Order", filters={"costeo": costeo, "is_subcontracted": 1}, pluck="name")
    else:
        po_names = []
    pos = []
    if po_names:
        pos = frappe.get_all(
            "Purchase Order",
            filters={"name": ["in", po_names], "is_subcontracted": 1},
            fields=["name", "supplier", "supplier_name", "docstatus", "status", "grand_total", "per_received"],
            order_by="creation asc",
        )
    return {"ocs": pos}


def _po_for_bom_item(bom_item, sales_order, costeo):
    """OC de subcontratación cuya línea de servicio produce `bom_item` (el
    sub-ensamblaje o producto terminado de una etapa) -- una etapa = una OC,
    etiquetada al crearse (fg_item) por _create_subcontracting_pos_from_stages."""
    names = []
    if sales_order:
        names = frappe.get_all(
            "Purchase Order Item", filters={"fg_item": bom_item, "sales_order": sales_order}, pluck="parent"
        )
    elif costeo and frappe.db.has_column("Purchase Order", "costeo"):
        costeo_pos = frappe.get_all(
            "Purchase Order", filters={"costeo": costeo, "is_subcontracted": 1}, pluck="name"
        )
        if costeo_pos:
            names = frappe.get_all(
                "Purchase Order Item",
                filters={"fg_item": bom_item, "parent": ["in", costeo_pos]},
                pluck="parent",
            )
    names = list(dict.fromkeys(names))
    if not names:
        return None
    return frappe.db.get_value(
        "Purchase Order", {"name": ["in", names], "is_subcontracted": 1}, ["name", "docstatus"], as_dict=True
    )


@frappe.whitelist()
def get_lotes_produccion(plan: str) -> dict:
    """Vista por LOTE de la subcontratación. Cada lote se descompone en PARADAS (ver
    _lote_paradas): un paso del flujo en un taller = 1 Subcontracting Order + 1 envío
    + 1 recibo. Un taller que maquila para varios productos en el mismo punto del
    flujo tiene UNA parada (con la cantidad de cada uno); uno que hace dos pasos NO
    adyacentes tiene DOS. Devuelve ``{productos: [...], lotes: [{lote_ref, productos,
    paradas, material_*}]}``."""
    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    if not costeo:
        return {"productos": [], "lotes": []}

    doc = frappe.get_doc("Costeo", costeo)
    pts_costeo = _productos_terminados_de_costeo(costeo)

    # Materia prima: no está ligada a un producto específico (una Solicitud de
    # Material puede cubrir varios productos del mismo costeo), así que se agrupa
    # por lote_ref a nivel de COSTEO y se ofrece igual a todos los productos que
    # compartan ese lote_ref -- el usuario es quien decide, al capturar el lote de
    # entrega, con qué lote de subcontratación se corresponde.
    material_pos = frappe.get_all(
        "Purchase Order",
        filters={"costeo": costeo, "is_subcontracted": 0, "lote_ref": ["not in", ["", None]], "docstatus": ["<", 2]},
        fields=["name", "lote_ref", "docstatus", "supplier", "supplier_name", "per_received", "enviado_el"],
        order_by="creation asc",
    ) if frappe.db.has_column("Purchase Order", "lote_ref") else []
    for p in material_pos:
        rnames = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": p["name"]}, pluck="parent")
        receipt = None
        if rnames:
            r = frappe.get_all(
                "Purchase Receipt", filters={"name": ["in", rnames]},
                fields=["name", "docstatus"], order_by="creation desc", limit=1,
            )
            receipt = r[0] if r else None
        p["receipt"] = receipt
        p["receipt_validated"] = bool(receipt and receipt["docstatus"] == 1)
    material_pos_by_lote = {}
    for p in material_pos:
        material_pos_by_lote.setdefault(p["lote_ref"], []).append(p)

    # Materiales ya divididos en lotes (Material Request Item.lote_ref) -- TODOS, ya
    # tengan OC o no: el orden de los proveedores en la pantalla del lote sale de esta
    # lista, así que debe ser estable (si sólo se listaran los que aún no tienen OC, el
    # proveedor que acaba de generar la suya desaparecería de aquí y su tarjeta
    # "saltaría" al final, reapareciendo sólo por material_pos). "Generar OC" se sigue
    # disparando a propósito desde la pantalla del lote, no automáticamente al validar
    # la solicitud (algo pudo cambiar entretanto: precio de un presupuesto, cantidad).
    mr_names = frappe.get_all("Material Request", filters={"costeo": costeo, "docstatus": 1}, pluck="name")
    has_sup = frappe.db.has_column("Material Request Item", "supplier")
    materiales_por_lote = {}
    if mr_names and frappe.db.has_column("Material Request Item", "lote_ref"):
        mri_rows = frappe.get_all(
            "Material Request Item",
            filters={"parent": ["in", mr_names], "lote_ref": ["not in", ["", None]]},
            fields=["parent", "item_code", "item_name", "qty", "uom", "lote_ref", "schedule_date"]
            + (["supplier"] if has_sup else []),
        )
        for r in mri_rows:
            materiales_por_lote.setdefault(r["lote_ref"], {"mr": r["parent"], "items": []})
            materiales_por_lote[r["lote_ref"]]["items"].append({
                "item_code": r["item_code"], "item_name": r["item_name"],
                "qty": r["qty"], "uom": r["uom"], "supplier": (r.get("supplier") if has_sup else ""),
            })

    # RFQ / Presupuesto de proveedor ya generados por lote (uno por proveedor, se
    # disparan a mano desde la pantalla del lote) -- para mostrarlos como ya creados
    # en vez de volver a ofrecer el botón de generarlos.
    rfqs_por_lote, sqs_por_lote = {}, {}
    if frappe.db.has_column("Request for Quotation", "lote_ref"):
        for r in frappe.get_all(
            "Request for Quotation",
            filters={"costeo": costeo, "lote_ref": ["not in", ["", None]], "docstatus": ["<", 2]},
            fields=["name", "lote_ref", "docstatus"],
        ):
            sup = frappe.db.get_value("Request for Quotation Supplier", {"parent": r["name"]}, "supplier")
            rfqs_por_lote.setdefault(r["lote_ref"], []).append({"name": r["name"], "supplier": sup, "docstatus": r["docstatus"]})
    if frappe.db.has_column("Supplier Quotation", "lote_ref"):
        for r in frappe.get_all(
            "Supplier Quotation",
            filters={"costeo": costeo, "lote_ref": ["not in", ["", None]], "docstatus": ["<", 2]},
            fields=["name", "lote_ref", "supplier", "docstatus"],
        ):
            sqs_por_lote.setdefault(r["lote_ref"], []).append({"name": r["name"], "supplier": r["supplier"], "docstatus": r["docstatus"]})

    item_name_cache = {}

    def _inm(code):
        if code not in item_name_cache:
            item_name_cache[code] = frappe.db.get_value("Item", code, "item_name") or code
        return item_name_cache[code]

    img_cache = {}

    def _img(code):
        if code not in img_cache:
            img_cache[code] = frappe.db.get_value("Item", code, "image") or None
        return img_cache[code]

    def _bonito(code):
        """Nombre legible de un servicio: su item_name si difiere del código, si no
        el código con guiones/underscores como espacios y en formato título."""
        nombre = _inm(code)
        if nombre and nombre != code:
            return nombre
        return (code or "").replace("_", " ").replace("-", " ").strip().title()

    def _titulo_parada(parada):
        nombres = [_bonito(s) for s in parada.servicios]
        if len(nombres) == 1:
            return nombres[0]
        if not nombres:
            return parada.supplier
        return f"{nombres[0]} +{len(nombres) - 1}"

    # ---- SCO de maquila del costeo, con su estado (envío / recibo) ----
    maquila_pos = frappe.get_all(
        "Purchase Order",
        filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": ["<", 2]},
        pluck="name",
    ) if frappe.db.has_column("Purchase Order", "costeo") else []
    scos_all = frappe.get_all(
        "Subcontracting Order",
        filters={"purchase_order": ["in", maquila_pos or [""]], "docstatus": ["<", 2]},
        fields=["name", "purchase_order", "lote_ref", "docstatus", "schedule_date"],
        order_by="creation asc",
    ) if maquila_pos else []
    for s in scos_all:
        s["items"] = frappe.get_all(
            "Subcontracting Order Item", filters={"parent": s["name"]}, fields=["item_code", "qty"]
        )
        s["transfer_done"] = bool(frappe.db.exists("Stock Entry", {
            "subcontracting_order": s["name"], "purpose": "Send to Subcontractor", "docstatus": 1,
        }))
        scr_names = frappe.get_all(
            "Subcontracting Receipt Item", filters={"subcontracting_order": s["name"]}, pluck="parent"
        )
        scr = frappe.get_all(
            "Subcontracting Receipt", filters={"name": ["in", scr_names or [""]]},
            fields=["name", "docstatus"], order_by="creation desc", limit=1,
        ) if scr_names else []
        s["receipt"] = scr[0] if scr else None
        s["receipt_validated"] = bool(scr and scr[0]["docstatus"] == 1)

    po_ds_cache = {}

    def _po_ds(po):
        if po not in po_ds_cache:
            po_ds_cache[po] = frappe.db.get_value("Purchase Order", po, "docstatus")
        return po_ds_cache[po]

    scos_by_lote = {}
    for s in scos_all:
        scos_by_lote.setdefault(s["lote_ref"] or "Sin lote", []).append(s)

    lote_keys = list(dict.fromkeys(
        list(scos_by_lote.keys())
        + list(material_pos_by_lote.keys())
        + list(materiales_por_lote.keys())
    ))

    todos_pts = [p.finished_item for p in doc.costeo_producto if p.finished_item]

    # Estructura de referencia del costeo (sin lote): para cada producto, la OC de
    # maquila de su primera parada -- la usa "Nuevo lote" para sugerir cantidades.
    estructura_ref, _fref = _lote_paradas(doc, {p: 1 for p in todos_pts})
    root_po_de_prod = {}
    for parada in estructura_ref:
        if parada.nivel == 0:
            for pr in parada.productos:
                root_po_de_prod.setdefault(pr, parada.po)

    lotes_out = []
    for lote_ref in lote_keys:
        scos_lote = scos_by_lote.get(lote_ref, [])
        materiales = materiales_por_lote.get(lote_ref)
        material_pos_lote = material_pos_by_lote.get(lote_ref, [])

        # Cantidad real por producto en el lote: la qty de cualquiera de sus piezas
        # (todas iguales dentro del lote) -- máx entre sus fg para no sumar paradas.
        qty_por_fg = {}
        for s in scos_lote:
            for it in s["items"]:
                qty_por_fg[it["item_code"]] = qty_por_fg.get(it["item_code"], 0) + flt(it["qty"])
        qty_por_prod = {}
        for fg, q in qty_por_fg.items():
            pr = _producto_de_fg(fg, pts_costeo)
            if pr:
                qty_por_prod[pr] = max(qty_por_prod.get(pr, 0), round(q))

        # Estructura de paradas: si aún no hay SCO (lote de material), todos los
        # productos del costeo (cantidad 0) para mostrar qué talleres hará falta.
        estructura = qty_por_prod or {p: 0 for p in todos_pts}
        paradas, _faltan = _lote_paradas(doc, {p: (q or 1) for p, q in estructura.items()})

        paradas_out = []
        for parada in paradas:
            fgset = set(parada.fg_items)
            sco = next((
                s for s in scos_lote
                if s["purchase_order"] == parada.po
                and any(it["item_code"] in fgset for it in s["items"])
            ), None)
            productos_parada = []
            for pr in parada.productos:
                q = 0
                if sco:
                    q = round(sum(
                        flt(it["qty"]) for it in sco["items"]
                        if it["item_code"] in fgset and _producto_de_fg(it["item_code"], pts_costeo) == pr
                    ))
                productos_parada.append({"finished_item": pr, "item_name": _inm(pr), "qty": q})
            paradas_out.append({
                "parada_id": parada.parada_id,
                "supplier": parada.supplier,
                "titulo": _titulo_parada(parada),
                "servicios": parada.servicios,
                "fg_items": parada.fg_items,
                "productos": productos_parada,
                "recibe_de": sorted(parada.recibe_de),
                "es_terminal": parada.es_terminal,
                "orden": parada.orden,
                "nivel": parada.nivel,
                "po": parada.po,
                "po_docstatus": _po_ds(parada.po),
                "sco": sco["name"] if sco else None,
                "sco_docstatus": sco["docstatus"] if sco else None,
                "transfer_done": sco["transfer_done"] if sco else False,
                "receipt": sco["receipt"] if sco else None,
                "receipt_validated": sco["receipt_validated"] if sco else False,
            })

        done_maquila = bool(paradas_out) and all(p["receipt_validated"] for p in paradas_out)
        done_material = all(mp.get("receipt_validated") for mp in material_pos_lote)
        lotes_out.append({
            "lote_ref": lote_ref,
            "schedule_date": (scos_lote[0]["schedule_date"] if scos_lote else None),
            "done": done_maquila and done_material,
            "productos": [
                {"finished_item": p, "item_name": _inm(p), "qty": q, "image": _img(p)}
                for p, q in sorted(qty_por_prod.items())
            ],
            "paradas": paradas_out,
            "material_pos": material_pos_lote,
            "material_mr": materiales["mr"] if materiales else None,
            "material_items": materiales["items"] if materiales else [],
            "material_rfqs": rfqs_por_lote.get(lote_ref, []),
            "material_sqs": sqs_por_lote.get(lote_ref, []),
        })

    return {
        "productos": [
            {
                "finished_item": p.finished_item,
                "item_name": _inm(p.finished_item),
                "root_po": root_po_de_prod.get(p.finished_item),
                "root_po_docstatus": _po_ds(root_po_de_prod[p.finished_item])
                if root_po_de_prod.get(p.finished_item) else None,
            }
            for p in doc.costeo_producto if p.finished_item
        ],
        "lotes": lotes_out,
    }


# =============================================================================
# FLUJO DE SUBCONTRATACIÓN (nuevo): OC → Subcontracting Order → Transferencia → Recibo
# =============================================================================

def _party_links(doctype, party, link_doctype="Supplier"):
    """Direcciones/contactos ligados a un proveedor o cliente (Dynamic Link)."""
    if not party:
        return []
    names = frappe.get_all(
        "Dynamic Link",
        filters={"link_doctype": link_doctype, "link_name": party, "parenttype": doctype},
        pluck="parent",
    )
    label_field = "address_title" if doctype == "Address" else "name"
    out = []
    for n in dict.fromkeys(names):
        label = frappe.db.get_value(doctype, n, label_field) or n
        out.append({"value": n, "label": label})
    return out


def _producto_de_fg(fg_item, productos_terminados):
    """Producto terminado al que pertenece un ``fg_item`` de OC/SCO de maquila.

    ``fg_item`` es o el código del producto terminado tal cual (operación terminal)
    o un sintético ``"<PT> · <slug>"`` (sub-ensamblaje de una operación intermedia,
    ver _resolve_production_operations). ``productos_terminados`` debe venir
    ordenado de más largo a más corto para que un PT que sea prefijo de otro no
    gane primero."""
    if not fg_item:
        return None
    for pt in productos_terminados:
        if fg_item == pt or fg_item.startswith(pt + " · "):
            return pt
    return None


def _productos_terminados_de_costeo(costeo):
    """Códigos de producto terminado de un costeo, ordenados de más largo a más
    corto (ver _producto_de_fg)."""
    if not costeo:
        return []
    pts = frappe.get_all("Costeo Producto", filters={"parent": costeo}, pluck="finished_item")
    return sorted({p for p in pts if p}, key=len, reverse=True)


def _po_subcontratacion_lineas(po_doc, productos=None) -> list:
    """Detalle por línea (una por Purchase Order Item) del avance de subcontratación
    de una OC -- puede agrupar varias etapas del mismo proveedor en renglones
    separados (ver _create_subcontracting_pos_from_stages -- ej. 3 servicios de
    bordado distintos, mismo bordador, en una sola OC). qty_subcontratada suma
    TODAS las Subcontracting Order (borrador + validadas, docstatus<2) vinculadas
    por 'purchase_order_item' (campo NATIVO de Subcontracting Order Item que
    apunta a la fila exacta de origen), así que el avance de cada línea nunca se
    mezcla con el de las demás aunque compartan la misma OC. Con una sola línea
    (el caso de siempre hasta ahora) esto se comporta idéntico a antes.

    Cada línea trae ``producto`` (el PT al que pertenece su fg_item) -- una OC de un
    proveedor que maquila para VARIOS productos del costeo tiene líneas de cada uno,
    y el saldo pendiente / los lotes se calculan por producto, no mezclados.
    ``productos`` (iterable), si se pasa, filtra a solo las líneas de esos PT."""
    pts = _productos_terminados_de_costeo(po_doc.get("costeo"))
    items = po_doc.items or []
    sco_names = frappe.get_all(
        "Subcontracting Order",
        filters={"purchase_order": po_doc.name, "docstatus": ["<", 2]},
        pluck="name",
        order_by="creation asc",
    )
    qty_por_po_item = {}
    if sco_names:
        for r in frappe.get_all(
            "Subcontracting Order Item",
            filters={"parent": ["in", sco_names]},
            fields=["purchase_order_item", "qty"],
        ):
            qty_por_po_item[r.purchase_order_item] = qty_por_po_item.get(r.purchase_order_item, 0) + flt(r.qty)

    # Los renglones de OC que comparten fg_item son UNA sola pieza repartida entre
    # varios servicios del mismo proveedor (ver _resolve_production_operations): se
    # colapsan sumando sus porciones para que la pieza cuente como una. Renglones con
    # fg_item DISTINTO son piezas distintas y se dejan por separado (el llamador toma
    # el mínimo entre ellas -- un lote combinado no puede pasar de la más corta).
    por_fg = {}
    orden = []
    for it in items:
        # En PIEZAS (fg_item_qty), que es la unidad de Subcontracting Order Item.qty
        # -- it.qty (de la OC) está en unidades de SERVICIO, no siempre 1:1 con piezas.
        qty_total_linea = flt(it.get("fg_item_qty")) or flt(it.qty)
        qty_sub_linea = qty_por_po_item.get(it.name, 0)
        key = it.get("fg_item") or it.name
        if key not in por_fg:
            por_fg[key] = {
                "purchase_order_item": it.name,
                "purchase_order_items": [],
                "fg_item": it.get("fg_item"),
                "producto": _producto_de_fg(it.get("fg_item") or "", pts),
                "servicios": [],
                "qty_total": 0.0,
                "qty_subcontratada": 0.0,
            }
            orden.append(key)
        d = por_fg[key]
        d["purchase_order_items"].append(it.name)
        d["servicios"].append(it.item_code)
        d["qty_total"] += qty_total_linea
        d["qty_subcontratada"] += qty_sub_linea

    lineas = []
    for key in orden:
        d = por_fg[key]
        d["servicio"] = " + ".join(dict.fromkeys(d["servicios"]))
        # Las prendas se subcontratan en piezas enteras -- la suma de porciones
        # fraccionarias (5000/3 x 3) puede quedar en 5000.001 por redondeo de campo.
        d["qty_total"] = round(d["qty_total"], 3)
        if abs(d["qty_total"] - round(d["qty_total"])) < 0.01:
            d["qty_total"] = float(round(d["qty_total"]))
        d["qty_subcontratada"] = round(d["qty_subcontratada"], 3)
        d["qty_pendiente"] = round(d["qty_total"] - d["qty_subcontratada"], 3)
        # Mismo criterio de pieza entera: un pendiente de ±0.01 es polvo de
        # redondeo del reparto entre servicios (1000/3 en varias tandas), no un
        # saldo real -- se aplana a entero para no ofrecer un lote de "0.002 pz".
        if abs(d["qty_pendiente"] - round(d["qty_pendiente"])) < 0.01:
            d["qty_pendiente"] = float(round(d["qty_pendiente"]))
        lineas.append(d)

    if productos is not None:
        productos = set(productos)
        lineas = [l for l in lineas if l.get("producto") in productos]
    return lineas


def _po_saldo_por_producto(po_doc) -> dict:
    """{producto: saldo_pendiente} de una OC de maquila -- el saldo de cada producto
    es el MÍNIMO entre sus propias líneas (un lote combinado no puede prometer más
    piezas que el servicio más corto de ese producto), calculado de forma
    independiente por producto para no mezclar dos prendas del mismo proveedor."""
    saldos = {}
    for l in _po_subcontratacion_lineas(po_doc):
        prod = l.get("producto")
        if prod is None:
            continue
        pend = flt(l["qty_pendiente"])
        saldos[prod] = pend if prod not in saldos else min(saldos[prod], pend)
    return saldos


def _po_saldo_por_fg(po_doc) -> dict:
    """{fg_item: saldo_pendiente} de una OC de maquila -- _po_subcontratacion_lineas
    ya colapsa por fg_item (los k servicios que comparten pieza son una línea), así
    que hay una entrada por sub-ensamblaje. Sirve para el saldo de UNA parada (un
    taller que hace varios pasos del flujo tiene un fg_item por paso)."""
    return {
        l["fg_item"]: flt(l["qty_pendiente"])
        for l in _po_subcontratacion_lineas(po_doc)
        if l.get("fg_item")
    }


@frappe.whitelist()
def sub_get_flujo(po: str) -> dict:
    """Estado del flujo de subcontratación de una OC: validada → Subcontracting Order(s)
    → transferencia de material (Stock Entry) → Subcontracting Receipt.

    Una OC puede tener VARIAS Subcontracting Order parciales (lotes escalonados en
    fechas distintas); cada una trae su propio avance de transferencia y recibo.

    'lineas' (ver _po_subcontratacion_lineas) trae el detalle por renglón cuando la
    OC agrupa varias etapas del mismo proveedor; los escalares
    qty_total/qty_subcontratada/qty_pendiente siguen existiendo para no romper al
    llamador, pero ahora son el MÍNIMO entre líneas -- un lote combinado (una sola
    Subcontracting Order que cubre todas a la vez) nunca puede prometer más piezas
    que el renglón más corto. Con una sola línea el mínimo es exactamente ese
    valor, cero cambio de comportamiento."""
    po_doc = frappe.get_doc("Purchase Order", po)
    lineas = _po_subcontratacion_lineas(po_doc)

    # OJO: qty_pendiente NO es qty_total - qty_subcontratada (esos dos mínimos
    # pueden venir de líneas DISTINTAS y restarlos entre sí puede dar un saldo mayor
    # al real -- ej. línea A 250 total/100 hecho = 150 pendiente, línea B 250/50 =
    # 200 pendiente; min(total)-min(subcontratada) = 250-50 = 200, pero un lote de
    # 200 más rebasaría el total de la línea A). Cada escalar es el mínimo de SU
    # PROPIA columna entre líneas, de forma independiente.
    qty_total = min((l["qty_total"] for l in lineas), default=0)
    qty_subcontratada = min((l["qty_subcontratada"] for l in lineas), default=0)
    qty_pendiente = min((l["qty_pendiente"] for l in lineas), default=0)

    out = {
        "po_validated": po_doc.docstatus == 1,
        "supplier": po_doc.supplier,
        "lineas": lineas,
        "qty_total": qty_total,
        "qty_subcontratada": qty_subcontratada,
        "qty_pendiente": qty_pendiente,
        "scos": [],
        "warehouses": frappe.get_all(
            "Warehouse",
            filters={"company": po_doc.company, "is_group": 0, "disabled": 0},
            fields=["name", "warehouse_name"],
            order_by="name asc",
        ),
        "address_options": _party_links("Address", po_doc.supplier),
        "contact_options": _party_links("Contact", po_doc.supplier),
    }
    sco_names = frappe.get_all(
        "Subcontracting Order",
        filters={"purchase_order": po, "docstatus": ["<", 2]},
        pluck="name",
        order_by="creation asc",
    )
    for sco_name in sco_names:
        sco = frappe.get_doc("Subcontracting Order", sco_name)
        entry = {
            "name": sco.name,
            "docstatus": sco.docstatus,
            "status": sco.status,
            "schedule_date": sco.schedule_date,
            "supplier": sco.supplier,
            "supplier_warehouse": sco.supplier_warehouse,
            "set_warehouse": sco.set_warehouse,
            "supplier_address": sco.supplier_address,
            "contact_person": sco.contact_person,
            "shipping_address": sco.shipping_address,
            "distribute_additional_costs_based_on": sco.distribute_additional_costs_based_on or "Qty",
            "total_additional_costs": sco.total_additional_costs,
            "per_received": sco.per_received,
            "additional_costs": [
                {"name": r.name, "description": r.description, "amount": r.amount, "expense_account": r.expense_account}
                for r in (sco.additional_costs or [])
            ],
            "supplied_items": [
                {
                    "rm_item_code": r.rm_item_code,
                    "item_name": frappe.db.get_value("Item", r.rm_item_code, "item_name"),
                    "required_qty": r.required_qty,
                    "reserve_warehouse": getattr(r, "reserve_warehouse", None),
                    "stock_uom": r.stock_uom,
                }
                for r in (sco.supplied_items or [])
            ],
            "service_items": [
                {"item_code": r.item_code, "qty": r.qty, "rate": r.rate, "fg_item": r.fg_item}
                for r in (sco.service_items or [])
            ],
            "transfer": {"done": False, "entries": []},
            "receipts": [],
        }

        ses = frappe.get_all(
            "Stock Entry",
            filters={"subcontracting_order": sco.name, "purpose": "Send to Subcontractor"},
            fields=["name", "docstatus"],
            order_by="creation asc",
        )
        entry["transfer"]["entries"] = ses
        entry["transfer"]["done"] = any(s.docstatus == 1 for s in ses)

        scr_parents = list(dict.fromkeys(frappe.get_all(
            "Subcontracting Receipt Item",
            filters={"subcontracting_order": sco.name, "docstatus": ["<", 2]},
            pluck="parent",
        )))
        entry["receipts"] = [
            dict(zip(("name", "docstatus", "status"),
                     frappe.db.get_value("Subcontracting Receipt", p, ["name", "docstatus", "status"])))
            for p in scr_parents
        ]
        out["scos"].append(entry)

    return out


def _sub_qty_disponible_info(po: str, producto: str = None) -> dict:
    """Cuántas unidades del servicio se pueden subcontratar YA, según la materia prima
    que hay en stock ahora mismo -- para sugerir (y limitar) la cantidad de un lote de
    subcontratación sin necesidad de crear la SCO a ciegas y descubrir hasta la
    transferencia que faltaba material (o, peor, tomar de una vez el 100% del saldo de
    la OC sin fijarse en el stock real). Uso interno -- ver sub_qty_disponible (misma
    info por API) y sub_crear_sco (que la usa para no dejar crear un lote más grande
    de lo que el stock real soporta).

    ``producto``, si se pasa, restringe el cálculo a las líneas de ESE producto
    terminado -- para una OC de un proveedor que maquila para varios productos del
    costeo, cada uno con su propio saldo y su propio consumo de materia prima.

    'supplied_items' (la explosión de materia prima por BOM) sólo la calcula ERPNext
    en el ciclo completo de validate() de la Subcontracting Order -- reconstruirlo a
    mano aquí duplicaría esa lógica y se desincroniza fácil con factores de
    conversión/UOM. Así que se crea una SCO real EN BORRADOR (para que corra el
    cálculo nativo tal cual), se lee, y se borra de inmediato -- nunca se valida ni se
    deja rastro, es puro cómputo."""
    from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order

    po_doc = frappe.get_doc("Purchase Order", po)
    if po_doc.docstatus != 1:
        frappe.throw(_("Valida la orden de compra primero."))

    sco_draft = make_subcontracting_order(po)
    sco_draft = frappe.get_doc(sco_draft) if isinstance(sco_draft, dict) else sco_draft
    if producto:
        # Recorte ANTES de insert() para que la explosión de materia prima
        # (supplied_items, la calcula el validate() nativo) sea solo la de este producto.
        pts = _productos_terminados_de_costeo(po_doc.get("costeo"))
        sco_draft.set("items", [
            it for it in (sco_draft.get("items") or [])
            if _producto_de_fg(it.item_code, pts) == producto
        ])
        sco_draft.set("service_items", [
            si for si in (sco_draft.get("service_items") or [])
            if _producto_de_fg(si.get("fg_item"), pts) == producto
        ])
        if not sco_draft.get("items"):
            return {"saldo_pendiente": 0, "sugerido": 0, "limitado_por_stock": False, "materiales": []}
    sco_draft.flags.ignore_permissions = True
    sco_draft.flags.ignore_mandatory = True
    sco_draft.insert()
    frappe.delete_doc("Subcontracting Order", sco_draft.name, force=True, ignore_permissions=True)

    # En PIEZAS (items), no en unidades de servicio (service_items): required_qty de la
    # materia prima está calculado para las piezas, así que dividir entre el servicio
    # daría un consumo por unidad inflado (x3 en una etapa de 3 salidas) y el chequeo
    # de stock rechazaría lotes que sí alcanzan.
    #
    # Las filas de sco_draft.items que comparten item_code (el FG producido) son la
    # MISMA pieza repartida entre varios servicios del mismo proveedor (ver
    # _resolve_production_operations): se SUMAN sus porciones para reconstruir la
    # pieza. El mínimo se toma entre piezas DISTINTAS -- un lote combinado no puede
    # pasar de la pieza con menos saldo.
    por_fg = {}
    for r in (sco_draft.items or []):
        por_fg[r.item_code] = por_fg.get(r.item_code, 0) + flt(r.qty)
    saldo_pendiente = min(por_fg.values(), default=0)
    # ±0.01 = polvo de redondeo del reparto entre servicios (ver
    # _po_subcontratacion_lineas), no un saldo real -- las prendas son piezas enteras.
    if abs(saldo_pendiente - round(saldo_pendiente)) < 0.01:
        saldo_pendiente = float(round(saldo_pendiente))
    mp, wip, semi_terminados = _stage_material_warehouses(po)

    materiales = []
    limite = None
    for r in (sco_draft.supplied_items or []):
        consumo_por_unidad = (flt(r.required_qty) / saldo_pendiente) if saldo_pendiente else 0
        # OJO: NO usar r.reserve_warehouse -- es un default nativo de ERPNext (pensado
        # para su flujo de "Reserve Stock" en la propia SCO) que no tiene relación con
        # el almacén real que usa este costeo por etapa; usarlo hacía que el chequeo
        # revisara el stock de un almacén equivocado (a veces con más existencia de la
        # real) y dejara pasar cantidades que el almacén verdadero no soportaba.
        #
        # Por MATERIAL, no por etapa completa: una etapa "no raíz" (que recibe el
        # semiterminado de otra) puede seguir necesitando avíos propios comprados
        # directo (ej. botones que se cosen hasta Confección) -- esos SIEMPRE viven en
        # materia prima, aunque el semiterminado de la etapa anterior viva en trabajo
        # en proceso. Ver _stage_material_warehouses.
        warehouse = wip if r.rm_item_code in semi_terminados else mp
        warehouse = warehouse or mp or wip
        disponible = flt(frappe.db.get_value(
            "Bin", {"item_code": r.rm_item_code, "warehouse": warehouse}, "actual_qty"
        )) if warehouse else 0.0
        soportado = (disponible / consumo_por_unidad) if consumo_por_unidad > 0 else None
        materiales.append({
            "item_code": r.rm_item_code,
            "item_name": frappe.db.get_value("Item", r.rm_item_code, "item_name"),
            "warehouse": warehouse, "requerido_total": flt(r.required_qty),
            "disponible": disponible, "unidades_soportadas": soportado,
        })
        if soportado is not None:
            limite = soportado if limite is None else min(limite, soportado)

    sugerido = saldo_pendiente if limite is None else min(saldo_pendiente, limite)
    sugerido = max(0, math.floor(sugerido + 1e-6))
    return {
        "saldo_pendiente": saldo_pendiente, "sugerido": sugerido,
        "limitado_por_stock": sugerido < saldo_pendiente, "materiales": materiales,
    }


@frappe.whitelist()
def sub_qty_disponible(po: str, producto: str = None) -> dict:
    """Ver _sub_qty_disponible_info -- expuesta tal cual por API para la sugerencia
    de cantidad que muestra el formulario de "Nuevo lote". ``producto`` restringe la
    sugerencia a ese producto terminado (OC compartida entre varios productos)."""
    return _sub_qty_disponible_info(po, producto=producto)


def _repartir_qty_en_filas(filas, q):
    """Reparte ``q`` piezas entre ``filas`` que comparten item_code (la misma pieza
    dividida entre varios servicios del mismo proveedor, ver
    _resolve_production_operations). ERPNext recalcula service_items.qty =
    items.qty x conversion_factor al validar, así que cada servicio termina
    facturando el lote completo. Con una sola fila (el caso normal) queda
    ``it.qty = min(q, disponible)``.

    Cada fila ya viene con ``it.qty`` = su CUPO restante (fg_item_qty menos lo ya
    subcontratado en esa fila -- lo pone populate_items_table nativo). El reparto
    respeta ese cupo fila por fila (para que en lotes sucesivos de un total que no
    divide exacto -- ej. 1000/3 en 3 tandas -- ninguna fila rebase su fg_item_qty), y
    garantiza que la SUMA sea exactamente ``min(q, cupo total)``: si al repartir en
    partes iguales una fila topa con su cupo, el faltante se redistribuye a las filas
    que aún tengan espacio -- así el lote no pierde ni gana piezas por arrastre de
    redondeo. Si ``q`` es entero (las prendas no se maquilan "a medias") el reparto es
    entero -> la explosión de materia prima del BOM también cuadra exacta."""
    prec = frappe.get_precision("Subcontracting Order Item", "qty") or 3
    cupos = [flt(it.qty) for it in filas]
    total = min(flt(q), sum(cupos))
    k = len(filas)
    entero = abs(total - round(total)) < 1e-9
    base = float(int(round(total)) // k) if entero else flt(total / k, prec)

    asign = [0.0] * k
    restante = total
    for i in range(k):
        asign[i] = min(base, cupos[i])
        restante -= asign[i]
    for i in range(k):
        if restante <= 1e-9:
            break
        add = min(cupos[i] - asign[i], restante)
        asign[i] = flt(asign[i] + add, prec)
        restante -= add
    for it, a in zip(filas, asign):
        it.qty = flt(a, prec)


@frappe.whitelist()
def sub_crear_sco(po: str, qty: float = None, schedule_date: str = None, lote_ref: str = None,
                  validar_stock: bool = True, cantidades=None, fg_items=None) -> dict:
    """Crea una Subcontracting Order (borrador) a partir de la OC validada.

    Sin `qty` ni `cantidades`, mapea todo el saldo pendiente por subcontratar de la OC
    (comportamiento nativo). Con `qty`/`schedule_date`, crea un LOTE parcial con esa
    cantidad y fecha de entrega — se puede llamar varias veces mientras quede saldo,
    para escalonar la producción en tandas (ERPNext ya soporta varias SCO parciales
    contra una misma OC). Si la OC ya está completamente subcontratada, lanza error.

    `cantidades` = ``{producto: qty}``: para OC de un proveedor que maquila para VARIOS
    productos del costeo (líneas de servicio de cada uno en la misma OC). La SCO se
    recorta a solo las líneas de esos productos y la cantidad de cada uno se reparte
    entre sus propios servicios. Un producto sin saldo pendiente se omite en silencio
    (así, en el 2º lote de un producto que ya terminó, ese producto simplemente no
    aparece -- no arrastra un pendiente inexistente). Cuando se pasa `cantidades`, se
    ignora `qty`.

    `fg_items` (lista de sub-ensamblajes), si se pasa junto con `cantidades`, recorta
    ADEMÁS a solo esas piezas -- es una PARADA: un paso del flujo en un taller (ver
    _lote_paradas). Un taller que hace corte al inicio y un acabado al final tiene 2
    paradas contra la MISMA OC, cada una su propia SCO.

    `lote_ref` correlaciona esta SCO con las de OTRAS paradas (otras OC, u otra parada
    del mismo taller) que pertenecen al mismo lote de producción -- ver
    get_lotes_produccion."""
    from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order

    if isinstance(cantidades, str):
        cantidades = frappe.parse_json(cantidades) if cantidades else None
    if isinstance(fg_items, str):
        fg_items = frappe.parse_json(fg_items) if fg_items else None
    fg_items = set(fg_items) if fg_items else None

    # Siempre en piezas enteras -- una prenda no se subcontrata "a medias", y sin
    # esto una sugerencia o captura con decimales (p. ej. arrastrado de otro cálculo)
    # se colaba tal cual a la SCO.
    if qty:
        qty = round(flt(qty))

    if frappe.db.get_value("Purchase Order", po, "docstatus") != 1:
        frappe.throw(_("Valida la orden de compra primero."))

    po_doc = frappe.get_doc("Purchase Order", po)
    pts = _productos_terminados_de_costeo(po_doc.get("costeo"))

    # ------------------------------------------------------------------ #
    # Modo multi-producto: cantidades = {producto: qty}
    # ------------------------------------------------------------------ #
    if cantidades is not None:
        cantidades = {p: round(flt(q)) for p, q in cantidades.items() if flt(q) > 0}
        if not cantidades:
            frappe.throw(_("Indica la cantidad de al menos un producto para el lote."))

        if fg_items:
            # Saldo de la PARADA: por producto, el mínimo pendiente entre SUS piezas
            # de esta parada (no entre todas las del taller).
            saldo_fg = _po_saldo_por_fg(po_doc)
            saldos = {}
            for fg in fg_items:
                pr = _producto_de_fg(fg, pts)
                if pr is None:
                    continue
                s = flt(saldo_fg.get(fg, 0))
                saldos[pr] = s if pr not in saldos else min(saldos[pr], s)
        else:
            saldos = _po_saldo_por_producto(po_doc)
        # Productos que ya no tienen pendiente en esta OC: se omiten sin error (2º
        # lote de un producto que ya terminó -- ver docstring).
        cantidades = {p: q for p, q in cantidades.items() if flt(saldos.get(p, 0)) > 0.001}
        if not cantidades:
            frappe.throw(_("Los productos indicados ya están completamente subcontratados en esta OC."))

        excesos = [
            _("{0}: pediste {1}, pendiente {2}").format(p, q, round(flt(saldos.get(p, 0)), 3))
            for p, q in cantidades.items()
            if flt(q) > flt(saldos.get(p, 0)) + 0.001
        ]
        if excesos:
            frappe.throw(_(
                "La cantidad de algún producto excede su saldo pendiente de subcontratar -- {0}."
            ).format("; ".join(excesos)))

        if validar_stock:
            for p, q in cantidades.items():
                info = _sub_qty_disponible_info(po, producto=p)
                if flt(q) > info["sugerido"] + 0.001:
                    frappe.throw(_(
                        "No hay materia prima suficiente en stock para {0} unidades de {1} -- "
                        "ahora mismo alcanza para {2}."
                    ).format(q, p, info["sugerido"]))

        sco = make_subcontracting_order(po)
        sco = frappe.get_doc(sco) if isinstance(sco, dict) else sco

        def _incluir(fg):
            return _producto_de_fg(fg, pts) in cantidades and (fg_items is None or fg in fg_items)

        # Recorte a solo las líneas de los productos pedidos (y, si es una parada,
        # solo esas piezas del taller).
        sco.set("items", [it for it in (sco.get("items") or []) if _incluir(it.item_code)])
        sco.set("service_items", [si for si in (sco.get("service_items") or []) if _incluir(si.get("fg_item"))])
        if not sco.get("items"):
            frappe.throw(_("La OC no tiene líneas de maquila para lo indicado en este lote."))
        # Reparto por (producto, pieza): la cantidad de cada producto se divide entre
        # sus servicios para producir 1 pieza, no k (ver _repartir_qty_en_filas).
        grupos = {}
        for it in sco.get("items") or []:
            prod = _producto_de_fg(it.item_code, pts)
            grupos.setdefault((prod, it.item_code), []).append(it)
        for (prod, _ic), filas in grupos.items():
            _repartir_qty_en_filas(filas, cantidades[prod])

        if schedule_date:
            sco.schedule_date = schedule_date
            for it in sco.get("items") or []:
                it.schedule_date = schedule_date
        if lote_ref and sco.meta.get_field("lote_ref"):
            sco.lote_ref = lote_ref
        sco.flags.ignore_permissions = True
        sco.flags.ignore_mandatory = True
        sco.insert()
        return {"ok": True, "sco": sco.name, "cantidades": cantidades,
                "fg_items": sorted(fg_items) if fg_items else None}

    # ------------------------------------------------------------------ #
    # Modo clásico: qty único (OC de un solo producto) -- comportamiento previo
    # ------------------------------------------------------------------ #
    existing_scos = frappe.get_all(
        "Subcontracting Order", filters={"purchase_order": po, "docstatus": ["<", 2]}, pluck="name"
    )
    if not qty and existing_scos:
        # Ya hay al menos una SCO (borrador o validada): a partir de la segunda SIEMPRE hay
        # que indicar cantidad -- si no, ERPNext podría mapear otra vez el saldo completo
        # porque subcontracted_quantity solo se actualiza al VALIDAR, no con drafts.
        frappe.throw(_("Ya existe una orden de subcontratación para esta OC. Indica la cantidad del nuevo lote."))

    # Saldo pendiente REAL de la OC completa -- si agrupa varias etapas del mismo
    # proveedor (ver _create_subcontracting_pos_from_stages), un lote combinado no
    # puede prometer más piezas que el renglón más corto (ver
    # _po_subcontratacion_lineas / sub_get_flujo, mismo criterio ahí). Con una sola
    # línea (el caso de siempre) esto da exactamente lo mismo que antes.
    lineas = _po_subcontratacion_lineas(po_doc)
    saldo_pendiente = min((l["qty_pendiente"] for l in lineas), default=0)
    # Cantidad que de verdad se va a mapear: la indicada, o -- si no se indicó -- todo
    # el saldo pendiente (comportamiento nativo de ERPNext sin `qty`). OJO: `qty=0` NO
    # cuenta como "indicada" (es lo que llega cuando un lote nace del lado de materia
    # prima y todavía no tiene ninguna SCO de ninguna etapa -- lote.qty vale 0 hasta
    # que se crea la primera) -- si se dejara pasar de largo aquí, se mapearía el
    # saldo COMPLETO sin ningún chequeo de stock, que es justo el bug que se repitió.
    qty_efectiva = flt(qty) if qty else saldo_pendiente

    if qty and flt(qty) > saldo_pendiente + 0.001:
        frappe.throw(_(
            "La cantidad del lote ({0}) excede el saldo pendiente de subcontratar ({1})."
        ).format(qty, saldo_pendiente))
    if saldo_pendiente <= 0.001:
        frappe.throw(_("Esta orden de compra ya está completamente subcontratada."))

    # No dejar pedir (ni mapear por default) más de lo que la materia prima EN STOCK
    # ahora mismo soporta -- si no, la SCO se crea "completa" y hasta la transferencia
    # (mucho después) se descubre que faltaba material.
    #
    # `validar_stock=False` lo salta a propósito para abrir un lote COMPLETO de golpe
    # (ver lote_abrir): ahí las etapas 2+ todavía no pueden tener su insumo -- lo
    # produce la etapa anterior, que ni siquiera ha empezado -- así que exigir stock
    # al comprometerse con el taller es pedir algo imposible. Una SCO es el encargo
    # ("te pido esto"), no el movimiento de material; quien sí debe exigir existencias
    # es la TRANSFERENCIA, y ahí el candado lo pone ERPNext solo (stock negativo) al
    # validar el Stock Entry. De paso se ahorra el cálculo, que es caro: crea y borra
    # una SCO borrador en cada llamada.
    info = _sub_qty_disponible_info(po) if validar_stock else None
    if info and qty_efectiva > info["sugerido"] + 0.001:
        faltantes = [
            m for m in info["materiales"]
            if m["unidades_soportadas"] is not None and m["unidades_soportadas"] + 0.001 < qty_efectiva
        ]
        detalle = "; ".join(
            _("{0}: hay {1}, alcanza para {2}").format(
                m["item_name"] or m["item_code"], m["disponible"], math.floor(m["unidades_soportadas"])
            ) for m in faltantes
        )
        frappe.throw(_(
            "No hay materia prima suficiente en stock para {0} unidades -- ahora mismo alcanza para {1}. {2}"
        ).format(qty_efectiva, info["sugerido"], detalle))

    sco = make_subcontracting_order(po)
    if qty:
        # Las filas que comparten item_code (el FG producido) son una sola pieza
        # repartida entre varios servicios del mismo proveedor -- el qty del lote se
        # reparte entre ellas para que produzcan UNA pieza, no k.
        grupos_fg = {}
        for it in sco.get("items") or []:
            grupos_fg.setdefault(it.item_code, []).append(it)
        for filas in grupos_fg.values():
            _repartir_qty_en_filas(filas, qty)
    if schedule_date:
        sco.schedule_date = schedule_date
        for it in sco.get("items") or []:
            it.schedule_date = schedule_date
    if lote_ref and sco.meta.get_field("lote_ref"):
        sco.lote_ref = lote_ref

    sco.flags.ignore_permissions = True
    sco.flags.ignore_mandatory = True
    sco.insert()
    # 'supplied_items' (la materia prima requerida, proporcional al qty de la prenda por
    # explosión de BOM) queda fraccionaria (p. ej. 182.6 metros) -- ERPNext la recalcula
    # desde el BOM en CADA validate()/save() (create_raw_materials_supplied, nativo de
    # SubcontractingController), así que redondearla aquí mismo no serviría de nada (se
    # pisa sola al guardar). El redondeo hacia arriba se hace en su lugar vía el hook
    # redondear_materia_prima_sco (ver hooks.py doc_events -- corre DESPUÉS del
    # validate() nativo, en cada guardado, incluido el insert() de aquí arriba).
    return {"ok": True, "sco": sco.name}


def redondear_materia_prima_sco(doc, method=None):
    """Hook 'validate' de Subcontracting Order (ver hooks.py, doc_events) -- la materia
    prima requerida por ítem (supplied_items) sale fraccionaria de la explosión nativa
    de BOM; se redondea SIEMPRE hacia arriba, igual que la transferencia
    (sub_transferir_material/_redondear_qty_arriba). Si no se hiciera aquí también, la
    transferencia (ya redondeada) terminaría pidiendo más de lo que la propia SCO
    todavía cree que se necesita, y ERPNext bloquea eso nativamente con "no puede
    transferirse más que X contra Subcontracting Order Y"."""
    for r in (doc.get("supplied_items") or []):
        redondeado = math.ceil(round(flt(r.required_qty), 4) - 1e-6)
        if redondeado != r.required_qty:
            r.required_qty = redondeado


def _default_landed_cost_account(company):
    """Cuenta por defecto para costos que se CAPITALIZAN al valor del inventario
    (fletes/maniobras de entrada, costos adicionales en SCO/transferencia/recibo de
    subcontratación) -- el tipo de cuenta 'Expenses Included In Valuation' es el que
    ERPNext espera para esto (no la cuenta de gasto genérica de la compañía, que en este
    caso es Costo de Ventas y mezclaría el flete con el COGS del período)."""
    return (
        frappe.get_cached_value("Company", company, "expenses_included_in_valuation")
        or frappe.get_cached_value("Company", company, "default_expense_account")
    )


def _landed_cost_row(company, description, amount, expense_account=None):
    """Arma una fila de 'Landed Cost Taxes and Charges' (additional_costs de SCO/Stock
    Entry/Subcontracting Receipt) con account_currency/base_amount ya resueltos -- en el
    escritorio de ERPNext esos dos campos los llena JS al capturar la fila; como aquí se
    guarda por API sin pasar por ese JS, hay que fijarlos a mano o el monto se posterga a
    0 en el asiento contable (base_amount queda vacío) y el documento truena al validar
    con 'Debit and Credit not equal'."""
    amount = flt(amount)
    currency = frappe.get_cached_value("Company", company, "default_currency")
    return {
        "expense_account": expense_account or _default_landed_cost_account(company),
        "description": description,
        "amount": amount,
        "account_currency": currency,
        "exchange_rate": 1,
        "base_amount": amount,
    }


@frappe.whitelist()
def sub_guardar_sco(sco: str, campos=None, costos=None) -> dict:
    """Guarda almacenes, dirección/contacto y costos adicionales en la SCO en borrador."""
    doc = frappe.get_doc("Subcontracting Order", sco)
    if doc.docstatus != 0:
        frappe.throw(_("La orden de subcontratación ya está validada."))

    if campos:
        c = json.loads(campos) if isinstance(campos, str) else campos
        for f in ("supplier_warehouse", "set_warehouse", "supplier_address", "contact_person",
                  "shipping_address", "distribute_additional_costs_based_on"):
            if f in c and doc.meta.get_field(f):
                doc.set(f, c.get(f) or None)
        # `set_warehouse` es solo el default para el selector -- el almacén que de verdad
        # usa ERPNext para recibir cada línea es Item.warehouse (a nivel de renglón), que
        # el cliente Desk propaga automáticamente al cambiar el header pero que aquí, al
        # guardar por API, se queda con lo que trajera `make_subcontracting_order` (a
        # veces un almacén viejo/no relacionado) si no lo igualamos a mano.
        if "set_warehouse" in c and c.get("set_warehouse"):
            for it in doc.items:
                it.warehouse = c["set_warehouse"]

    if costos is not None:
        rows = json.loads(costos) if isinstance(costos, str) else costos
        doc.set("additional_costs", [])
        for r in rows:
            amount = flt(r.get("amount"))
            if not (r.get("description") and amount):
                continue
            doc.append("additional_costs", _landed_cost_row(doc.company, r.get("description"), amount, r.get("expense_account")))

    doc.flags.ignore_permissions = True
    doc.save()
    return {"ok": True}


@frappe.whitelist()
def sub_validar_sco(sco: str) -> dict:
    """Valida (submit) la orden de subcontratación."""
    doc = frappe.get_doc("Subcontracting Order", sco)
    if doc.docstatus == 0:
        doc.flags.ignore_permissions = True
        doc.submit()
    return {"ok": True}


def _etapas_rows_for_po(po: str):
    """Operaciones que corresponden a esta OC de subcontratación -- inversa de
    _create_subcontracting_pos_from_stages: usa los mismos fg_item (op.output_item)
    con los que se etiquetó cada línea de servicio. Una OC agrupa TODAS las etapas
    del mismo proveedor y varios servicios pueden compartir un fg_item, así que
    regresa una entrada por fg_item ÚNICO de la OC:
    [{"op": op, "is_root": bool, "fg_item": str}, ...]. is_root=True si la operación
    NO recibe de ninguna otra (consume materia prima directa)."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return []
    fg_items = frappe.get_all("Purchase Order Item", filters={"parent": po}, pluck="fg_item")
    fg_items = [f for f in dict.fromkeys(fg_items) if f]
    if not fg_items:
        return []
    doc = frappe.get_doc("Costeo", costeo)
    etapas_por_producto = {}
    for row in doc.tabla_etapas_costeo:
        etapas_por_producto.setdefault(row.producto_terminado, []).append(row)

    op_por_fg = {}
    for producto, etapas in etapas_por_producto.items():
        for op in _resolve_production_operations(etapas, producto):
            if op.output_item and op.output_item not in op_por_fg:
                op_por_fg[op.output_item] = {
                    "op": op, "is_root": not op.upstream_keys, "fg_item": op.output_item,
                }

    return [op_por_fg[f] for f in fg_items if f in op_por_fg]


def _stage_material_warehouses(po: str):
    """Devuelve (mp, wip, semi_terminados) para las etapas de esta OC de
    subcontratación -- puede ser más de una (ver _etapas_rows_for_po: una OC agrupa
    todas las etapas del mismo proveedor). 'semi_terminados' es la UNIÓN, sobre
    TODOS los productos representados en la OC, de los item codes que son la SALIDA
    de alguna etapa de su propio producto (subensamblaje o producto terminado) --
    son los únicos materiales que de verdad llegan vía SCO/Recibo de una etapa
    anterior y por lo tanto viven en 'wip'. Cualquier OTRO material del BOM de la
    etapa (telas, hilos, botones…) es materia prima genuina comprada directo y vive
    en 'mp', SIN IMPORTAR si la etapa en sí es raíz o no -- una etapa "no raíz" (que
    recibe el semiterminado de otra) puede perfectamente seguir necesitando avíos
    propios (ej. botones que se cosen hasta la etapa de Confección, no antes)."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return None, None, set()
    mp, wip = frappe.db.get_value("Costeo", costeo, ["almacen_materias_primas", "almacen_trabajo_en_proceso"]) or (None, None)
    etapas_info = _etapas_rows_for_po(po)
    semi_terminados = set()
    if etapas_info:
        productos = {info["op"].producto_terminado for info in etapas_info}
        doc = frappe.get_doc("Costeo", costeo)
        for producto in productos:
            etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == producto]
            for op in _resolve_production_operations(etapas_prod, producto):
                if op.output_item:
                    semi_terminados.add(op.output_item)
    return mp, wip, semi_terminados


def _stage_source_warehouse_for_po(po: str):
    """Almacén de origen recomendado (UN solo valor, para el botón 'usar recomendado
    por etapa' -- la transferencia real ya se prellena por material, ver
    _aplicar_almacenes_origen_por_material) según la etapa: las etapas RAÍZ (sin
    'recibe_de' -- consumen materia prima directa; puede haber MÁS DE UNA en
    paralelo, p. ej. "Bordado de Mangas" + "Confección de Cuello" que luego
    convergen en "Confección") usan el almacén de materia prima; las que
    dependen del semi-terminado de otra etapa usan el de trabajo en proceso. Antes
    esto se decidía por "¿es la OC de subcontratación creada primero?", que sólo es
    correcto en cadenas lineales -- con ramas en paralelo, la segunda raíz caía mal
    clasificada como "depende de otra etapa" sólo por haberse creado después.

    Una OC puede agrupar varias etapas del mismo proveedor (ver
    _etapas_rows_for_po) que no necesariamente son todas raíz o todas no-raíz --
    aquí solo se decide el default del botón/cabecera (por mayoría); el detalle
    correcto por renglón lo sigue poniendo _aplicar_almacenes_origen_por_material."""
    if not po:
        return None
    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return None
    mp, wip = frappe.db.get_value("Costeo", costeo, ["almacen_materias_primas", "almacen_trabajo_en_proceso"]) or (None, None)
    etapas_info = _etapas_rows_for_po(po)
    if etapas_info:
        raices = sum(1 for info in etapas_info if info["is_root"])
        es_mayoria_raiz = raices * 2 >= len(etapas_info)
        return (mp if es_mayoria_raiz else wip) or mp or wip
    # No se pudo resolver la etapa (dato viejo/incompleto) -- cae al criterio anterior.
    sub_pos = frappe.get_all(
        "Purchase Order",
        filters={"costeo": costeo, "is_subcontracted": 1},
        order_by="creation asc",
        pluck="name",
    )
    is_first = bool(sub_pos) and sub_pos[0] == po
    return (mp if is_first else wip) or mp or wip


def _stage_source_warehouse(sco_name: str):
    po = frappe.db.get_value("Subcontracting Order", sco_name, "purchase_order")
    return _stage_source_warehouse_for_po(po)


def _aplicar_almacenes_origen_por_material(se, po):
    """Fija el almacén de origen POR RENGLÓN del Stock Entry -- una etapa puede necesitar
    a la vez semiterminado (de trabajo en proceso) Y avíos propios (de materia prima),
    así que cada línea del Stock Entry se manda a buscar a su almacén correcto (ver
    _stage_material_warehouses), en vez de forzar un único almacén para todo el
    documento. La cabecera (from_warehouse, solo un valor visual/default) se deja en
    el almacén que use la MAYORÍA de las líneas."""
    mp, wip, semi_terminados = _stage_material_warehouses(po)
    if not mp and not wip:
        return
    conteo = {"mp": 0, "wip": 0}
    for it in se.items:
        wh = wip if it.item_code in semi_terminados else mp
        wh = wh or mp or wip
        it.s_warehouse = wh
        conteo["wip" if wh == wip else "mp"] += 1
    se.from_warehouse = wip if conteo["wip"] > conteo["mp"] else mp


def _redondear_qty_arriba(se, save=True):
    """Redondea hacia arriba (nunca hacia abajo) la cantidad de cada línea de la
    transferencia -- la materia prima llega fraccionaria por la explosión de BOM
    (p. ej. 182.6 metros) y en el taller no se mide/transfiere así; de quedarse corto
    el taller no tendría material suficiente para la cantidad completa del lote."""
    cambio = False
    for it in se.items:
        redondeado = math.ceil(round(flt(it.qty), 4) - 1e-6)
        if redondeado != it.qty:
            it.qty = redondeado
            cambio = True
    if cambio and save and se.docstatus == 0:
        se.flags.ignore_permissions = True
        se.save()


def _aplicar_articulos_alternos_por_talla(se, sco: str, save: bool = False):
    """Si el lote de esta Orden de Subcontratación (sco.lote_ref) corresponde a
    una talla con sustitución de material (sobrecosto_tipo = 'Material'),
    reemplaza esa línea del Stock Entry por el artículo REAL (ej. Cierre 70cm en
    vez de Cierre 60cm) -- mismo Stock Entry que ya arma sub_transferir_material,
    solo se ajustan las líneas afectadas antes de guardarlo. El BOM del producto
    sigue sin tocarse (sigue costeando con el material estándar); esto solo
    afecta lo que se transfiere/consume para ESTE lote en particular, así el
    inventario y la producción reconocen el artículo que de verdad se compró
    (ver crear_boms_spa, que ya dejó marcado allow_alternative_item en el BOM y
    registrado el par en Item Alternative la primera vez que se usó)."""
    lote_ref = frappe.db.get_value("Subcontracting Order", sco, "lote_ref")
    if not lote_ref:
        return False
    po = frappe.db.get_value("Subcontracting Order", sco, "purchase_order")
    costeo = frappe.db.get_value("Purchase Order", po, "costeo") if po else None
    if not costeo:
        return False

    tallas = frappe.get_all(
        "Costeo Producto Talla",
        filters={"parent": costeo, "lote_ref": lote_ref, "sobrecosto_tipo": "Material"},
        fields=["sobrecosto_material_original", "sobrecosto_material_alterno"],
    )
    alterno_por_original = {
        t.sobrecosto_material_original: t.sobrecosto_material_alterno
        for t in tallas if t.sobrecosto_material_original and t.sobrecosto_material_alterno
    }
    if not alterno_por_original:
        return False

    cambio = False
    for row in se.items:
        alterno = alterno_por_original.get(row.item_code)
        if not alterno or row.get("original_item"):  # ya se sustituyó antes -- no repetir
            continue
        _asegurar_articulo_alterno(row.item_code, alterno)
        alt = frappe.db.get_value("Item", alterno, ["item_name", "description", "stock_uom"], as_dict=True)
        row.original_item = row.item_code
        row.allow_alternative_item = 1
        row.item_code = alterno
        row.item_name = alt.item_name
        row.description = alt.description or alt.item_name
        row.uom = alt.stock_uom
        row.stock_uom = alt.stock_uom
        row.conversion_factor = 1
        row.transfer_qty = row.qty
        cambio = True

    if cambio and save and se.docstatus == 0:
        se.flags.ignore_permissions = True
        se.save()
    return cambio


@frappe.whitelist()
def sub_transferir_material(sco: str) -> dict:
    """Crea el Stock Entry 'Send to Subcontractor' EN BORRADOR (igual que el botón nativo
    'Transferencia → Materiales al proveedor' de ERPNext). No lo valida: el usuario revisa
    almacenes y cantidades y lo valida aparte (así no fuerza stock negativo).
    El almacén de origen se pre-llena según la etapa (materia prima / trabajo en proceso).
    Si el lote de esta orden tiene sustitución de material por talla, esa línea ya
    llega con el artículo alterno real (ver _aplicar_articulos_alternos_por_talla)."""
    from erpnext.controllers.subcontracting_controller import make_rm_stock_entry

    doc = frappe.get_doc("Subcontracting Order", sco)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la orden de subcontratación primero."))

    # Reutiliza un borrador existente si ya se generó uno -- de paso, sanea sus
    # cantidades por si quedó de antes de que esto redondeara hacia arriba (o si el
    # required_qty de la SCO que lo originó todavía traía decimales), y aplica la
    # sustitución de material si todavía no se había hecho.
    existing = frappe.db.get_value(
        "Stock Entry",
        {"subcontracting_order": sco, "purpose": "Send to Subcontractor", "docstatus": 0},
        "name",
    )
    if existing:
        se_existing = frappe.get_doc("Stock Entry", existing)
        _aplicar_articulos_alternos_por_talla(se_existing, sco, save=True)
        _redondear_qty_arriba(se_existing)
        return {"ok": True, "stock_entry": existing, "docstatus": 0}

    se = make_rm_stock_entry(sco, order_doctype="Subcontracting Order")
    se = frappe.get_doc(se) if isinstance(se, dict) else se
    po = frappe.db.get_value("Subcontracting Order", sco, "purchase_order")
    _aplicar_almacenes_origen_por_material(se, po)
    _aplicar_articulos_alternos_por_talla(se, sco)
    _redondear_qty_arriba(se, save=False)
    se.flags.ignore_permissions = True
    se.insert()
    return {"ok": True, "stock_entry": se.name, "docstatus": se.docstatus}


@frappe.whitelist()
def sub_get_transferencia(stock_entry: str) -> dict:
    """Detalle del Stock Entry de transferencia (almacenes + materiales + disponibilidad)."""
    doc = frappe.get_doc("Stock Entry", stock_entry)
    items = []
    for r in (doc.items or []):
        avail = None
        if r.s_warehouse:
            avail = flt(frappe.db.get_value("Bin", {"item_code": r.item_code, "warehouse": r.s_warehouse}, "actual_qty"))
        items.append({
            "name": r.name,
            "item_code": r.item_code,
            "item_name": r.item_name,
            "qty": r.qty,
            "s_warehouse": r.s_warehouse,
            "t_warehouse": r.t_warehouse,
            "uom": r.uom,
            "available": avail,
        })
    recommended = None
    if doc.subcontracting_order:
        recommended = _stage_source_warehouse(doc.subcontracting_order)
    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "from_warehouse": doc.from_warehouse,
        "to_warehouse": doc.to_warehouse,
        "recommended_source": recommended,
        "items": items,
        "distribute_additional_costs_based_on": doc.get("distribute_additional_costs_based_on") or "Qty",
        "total_additional_costs": doc.get("total_additional_costs"),
        "additional_costs": [
            {"name": r.name, "description": r.description, "amount": r.amount, "expense_account": r.expense_account}
            for r in (doc.get("additional_costs") or [])
        ],
    }


@frappe.whitelist()
def get_stock_disponible(item_code: str, warehouse: str) -> dict:
    """Existencia real (Bin) de un artículo en un almacén -- para refrescar "Disponible"
    al vuelo cuando el usuario cambia el almacén de origen de una fila de la
    transferencia (cada material puede necesitar salir de un almacén distinto, ver
    _stage_material_warehouses)."""
    if not item_code or not warehouse:
        return {"available": None}
    return {"available": flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))}


@frappe.whitelist()
def sub_guardar_transferencia(stock_entry: str, from_warehouse=None, to_warehouse=None, items=None,
                               costos=None, distribute_additional_costs_based_on=None) -> dict:
    """Guarda almacenes de origen/destino, cantidades y costos adicionales (flete al enviar
    materia prima al taller) del Stock Entry en borrador -- se capitalizan al valor del
    material recibido en el almacén del proveedor, igual que en la SCO."""
    doc = frappe.get_doc("Stock Entry", stock_entry)
    if doc.docstatus != 0:
        frappe.throw(_("La transferencia ya está validada."))

    # El `items` que manda el SPA es la última copia cargada del documento -- si el
    # usuario acaba de cambiar el almacén de origen/destino en el header, esa copia
    # todavía trae el almacén VIEJO en cada fila. Por eso `items` (cantidades y
    # cualquier ajuste fila-por-fila) se aplica primero, y el from_warehouse/
    # to_warehouse del header se aplica AL FINAL para que gane siempre sobre datos
    # obsoletos -- si no, la fila se queda con el almacén anterior aunque el header
    # ya muestre el nuevo.
    if items is not None:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows}
        for it in doc.items:
            r = by_name.get(it.name)
            if not r:
                continue
            if r.get("qty") is not None:
                # Igual que al crear la transferencia: la materia prima siempre se
                # redondea hacia arriba, nunca hacia abajo.
                it.qty = math.ceil(round(flt(r.get("qty")), 4) - 1e-6)
            if r.get("s_warehouse"):
                it.s_warehouse = r.get("s_warehouse")
            if r.get("t_warehouse"):
                it.t_warehouse = r.get("t_warehouse")

    if from_warehouse:
        doc.from_warehouse = from_warehouse
        for it in doc.items:
            it.s_warehouse = from_warehouse
    if to_warehouse:
        doc.to_warehouse = to_warehouse
        for it in doc.items:
            it.t_warehouse = to_warehouse

    if distribute_additional_costs_based_on and doc.meta.get_field("distribute_additional_costs_based_on"):
        doc.distribute_additional_costs_based_on = distribute_additional_costs_based_on

    if costos is not None:
        rows = json.loads(costos) if isinstance(costos, str) else costos
        doc.set("additional_costs", [])
        for r in rows:
            amount = flt(r.get("amount"))
            if not (r.get("description") and amount):
                continue
            doc.append("additional_costs", _landed_cost_row(doc.company, r.get("description"), amount, r.get("expense_account")))

    doc.flags.ignore_permissions = True
    doc.save()
    return {"ok": True}


@frappe.whitelist()
def sub_validar_transferencia(stock_entry: str) -> dict:
    """Valida (submit) el Stock Entry de transferencia. Puede lanzar NegativeStockError si la
    materia prima aún no está en el almacén de origen (hay que comprarla/recibirla primero)."""
    doc = frappe.get_doc("Stock Entry", stock_entry)
    if doc.docstatus == 0:
        doc.flags.ignore_permissions = True
        doc.submit()
    return {"ok": True}


@frappe.whitelist()
def sub_crear_recibo(sco: str) -> dict:
    """Crea el Subcontracting Receipt (borrador) para recibir el producto terminado del taller."""
    from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import make_subcontracting_receipt

    if frappe.db.get_value("Subcontracting Order", sco, "docstatus") != 1:
        frappe.throw(_("Valida la orden de subcontratación primero."))
    existing = frappe.db.get_value("Subcontracting Receipt Item", {"subcontracting_order": sco, "docstatus": ["<", 2]}, "parent")
    if existing:
        return {"ok": True, "scr": existing}

    scr = make_subcontracting_receipt(sco)
    scr.flags.ignore_permissions = True
    scr.flags.ignore_mandatory = True
    scr.insert()
    return {"ok": True, "scr": scr.name}


def _transitive_upstream(ops_by_key):
    """{op_key: set(TODOS los op_key aguas arriba, transitivos)} sobre el grafo de
    operaciones completo (varios productos)."""
    memo = {}

    def up(k, visitando):
        if k in memo:
            return memo[k]
        if k in visitando:
            return set()
        visitando.add(k)
        acc = set()
        for u in ops_by_key[k].upstream_keys:
            if u in ops_by_key:
                acc.add(u)
                acc |= up(u, visitando)
        visitando.discard(k)
        memo[k] = acc
        return acc

    return {k: up(k, set()) for k in ops_by_key}


def _lote_paradas(doc, cantidades):
    """Descompone el trabajo de maquila de un lote (``cantidades`` = {producto: qty})
    en PARADAS. Una parada es un paso del flujo en un taller que se encarga de un
    jalón -- se traduce en 1 Subcontracting Order + 1 envío + 1 recibo.

    - Operaciones del MISMO taller sin relación de ancestro entre sí (paralelas,
      aunque sean de productos distintos) -> MISMA parada.
    - Operaciones del mismo taller donde una es ancestro (transitivo) de otra ->
      paradas DISTINTAS, en secuencia (2 SCO contra la misma OC).
    - Talleres distintos -> paradas distintas.

    Devuelve ``(paradas, faltan_oc)`` donde cada parada es un ``frappe._dict`` con
    parada_id, supplier, po, fg_items (ordenado), op_keys (set), productos
    ({producto: qty}), servicios (lista de service_item), es_terminal, recibe_de
    (set de parada_id), orden (int topológico). ``faltan_oc`` = sub-ensamblajes sin
    OC de maquila validada."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    costeo = doc.name

    ops_by_key = {}
    for prod in cantidades:
        etapas = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == prod]
        for op in _resolve_production_operations(etapas, prod):
            if not op.output_item or not op.supplier or not op.servicios:
                continue
            op.producto = prod
            ops_by_key[op.op_key] = op

    trans_up = _transitive_upstream(ops_by_key)

    po_de_key, faltan = {}, []
    for k, op in ops_by_key.items():
        po = frappe.db.get_value("Purchase Order Item", {"fg_item": op.output_item, "docstatus": 1}, "parent")
        if not po or frappe.db.get_value("Purchase Order", po, "costeo") != costeo:
            faltan.append(op.output_item)
            continue
        po_de_key[k] = po

    por_supplier = {}
    for k, op in ops_by_key.items():
        if k in po_de_key:
            por_supplier.setdefault(op.supplier, []).append(k)

    paradas, parada_de_op = [], {}
    for supplier, keys in por_supplier.items():
        keyset = set(keys)
        nivel = {}

        def _niv(k, _keyset=keyset):
            if k in nivel:
                return nivel[k]
            ancestros = trans_up[k] & _keyset
            nivel[k] = 1 + max((_niv(a, _keyset) for a in ancestros), default=-1)
            return nivel[k]

        olas = {}
        for k in keys:
            olas.setdefault(_niv(k), []).append(k)

        for niv in sorted(olas):
            op_keys = olas[niv]
            fg_items = sorted({ops_by_key[k].output_item for k in op_keys})
            productos = {ops_by_key[k].producto: round(flt(cantidades[ops_by_key[k].producto]))
                        for k in op_keys}
            servicios = []
            for k in op_keys:
                for s in ops_by_key[k].servicios:
                    si = s.get("service_item")
                    if si and si not in servicios:
                        servicios.append(si)
            pid = hashlib.md5((supplier + "|" + "|".join(fg_items)).encode()).hexdigest()[:12]
            paradas.append(frappe._dict(
                parada_id=pid,
                supplier=supplier,
                po=po_de_key[op_keys[0]],
                op_keys=set(op_keys),
                fg_items=fg_items,
                productos=productos,
                servicios=servicios,
                es_terminal=any(ops_by_key[k].is_terminal for k in op_keys),
                recibe_de=set(),
            ))
            for k in op_keys:
                parada_de_op[k] = pid

    by_pid = {p.parada_id: p for p in paradas}
    for parada in paradas:
        for k in parada.op_keys:
            for u in ops_by_key[k].upstream_keys:
                upid = parada_de_op.get(u)
                if upid and upid != parada.parada_id:
                    parada.recibe_de.add(upid)

    # Orden topológico (Kahn) sobre recibe_de.
    indeg = {p.parada_id: len(p.recibe_de) for p in paradas}
    cola = sorted([pid for pid, d in indeg.items() if d == 0])
    orden, i = {}, 0
    hijos = {p.parada_id: [] for p in paradas}
    for p in paradas:
        for up in p.recibe_de:
            hijos.setdefault(up, []).append(p.parada_id)
    while cola:
        pid = cola.pop(0)
        i += 1
        orden[pid] = i
        for h in sorted(hijos.get(pid, [])):
            indeg[h] -= 1
            if indeg[h] == 0:
                cola.append(h)
        cola.sort()

    # nivel = distancia más larga desde una parada raíz -- las paradas del mismo
    # nivel corren en paralelo (columna en la UI); niveles crecientes = secuencia.
    nivel = {}

    def _pnivel(pid):
        if pid in nivel:
            return nivel[pid]
        nivel[pid] = 0
        nivel[pid] = 1 + max((_pnivel(u) for u in by_pid[pid].recibe_de), default=-1)
        return nivel[pid]

    for p in paradas:
        p.orden = orden.get(p.parada_id, 999)
        p.nivel = _pnivel(p.parada_id)
    paradas.sort(key=lambda p: (p.nivel, p.orden, p.supplier))

    return paradas, list(dict.fromkeys(faltan))


@frappe.whitelist()
def get_tallas_material_sin_lote(costeo: str) -> list:
    """Tallas con sustitución de material (sobrecosto_tipo = 'Material') ya
    'Definidas' (cantidad confirmada por el cliente) que todavía no se asignaron
    a ningún lote -- se ofrecen al abrir un lote nuevo para que esa cantidad se
    marque como "esta parte es de tal talla" (ver lote_abrir, tallas_por_producto)
    y el envío de material al taller de ese lote use el artículo alterno."""
    rows = frappe.get_all(
        "Costeo Producto Talla",
        filters={
            "parent": costeo, "sobrecosto_tipo": "Material", "estado_cantidad": "Definida",
            "qty": [">", 0], "lote_ref": ["in", ["", None]],
        },
        fields=["name", "finished_item", "genero", "talla", "qty", "sobrecosto_material_original", "sobrecosto_material_alterno"],
    )
    for r in rows:
        r["talla_label"] = " ".join(filter(None, [r.genero, _tallas_label(r.talla)])) or r.talla
        r["material_label"] = frappe.db.get_value("Item", r.sobrecosto_material_alterno, "item_name") or r.sobrecosto_material_alterno
    return rows


@frappe.whitelist()
def lote_abrir(plan: str, lote_ref: str, cantidades=None, schedule_date: str = None,
               qty: float = None, producto: str = None, tallas_por_producto=None) -> dict:
    """Abre un lote de producción de un jalón: crea y valida la Subcontracting Order
    de CADA PARADA del lote (ver _lote_paradas) -- un paso del flujo en un taller,
    con la cantidad de cada producto que entra en el lote.

    ``cantidades`` = ``{producto: qty}``. Un taller que maquila para VARIOS productos
    en el mismo punto del flujo recibe UNA sola SCO (con la cantidad de cada uno). Un
    taller que hace dos pasos NO adyacentes del flujo recibe DOS SCO (una por parada).
    Un producto sin saldo pendiente se omite en silencio.

    Compat: `qty` (+ `producto`) -- firma anterior -- se traduce a ``cantidades``.

    NO exige materia prima en stock (validar_stock=False): las paradas 2+ reciben su
    insumo de la anterior, que todavía no ha producido nada. El candado de existencias
    vive en la TRANSFERENCIA.

    Las paradas que ya tengan su SCO en este lote se saltan -- seguro reintentar.

    ``tallas_por_producto`` (opcional) = ``{producto: nombre_de_fila_de_talla}`` --
    cuando la cantidad de un producto en este lote corresponde a una talla con
    sustitución de material ya confirmada ('Definida'), se marca esa fila con
    este lote_ref (Costeo Producto Talla.lote_ref). Así, al enviar el material
    de este lote al taller, el sistema sabe que debe usar el artículo alterno en
    vez del material estándar (ver _aplicar_articulos_alternos_por_talla)."""
    if not lote_ref:
        frappe.throw(_("Indica la referencia del lote."))
    if isinstance(cantidades, str):
        cantidades = frappe.parse_json(cantidades) if cantidades else None
    if isinstance(tallas_por_producto, str):
        tallas_por_producto = frappe.parse_json(tallas_por_producto) if tallas_por_producto else None

    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    if not costeo:
        frappe.throw(_("El plan no está ligado a ningún costeo."))
    doc = frappe.get_doc("Costeo", costeo)
    pts_costeo = [p.finished_item for p in doc.costeo_producto if p.finished_item]

    if tallas_por_producto:
        for producto_fi, talla_row in tallas_por_producto.items():
            if producto_fi in pts_costeo and talla_row:
                frappe.db.set_value("Costeo Producto Talla", talla_row, "lote_ref", lote_ref, update_modified=False)

    if cantidades is None:
        if not qty or flt(qty) <= 0:
            frappe.throw(_("Indica la cantidad del lote."))
        objetivo = [producto] if producto else pts_costeo
        cantidades = {p: flt(qty) for p in objetivo}

    cantidades = {p: round(flt(q)) for p, q in cantidades.items() if p in pts_costeo and flt(q) > 0}
    if not cantidades:
        frappe.throw(_("Indica la cantidad de al menos un producto para el lote."))

    paradas, faltan = _lote_paradas(doc, cantidades)
    creadas, saltadas = [], []
    errores = [_("{0}: su orden de compra de maquila no está validada.").format(fg) for fg in faltan]

    for parada in paradas:
        # ¿Ya hay una SCO de este lote que cubra las piezas de esta parada?
        scos_lote = frappe.get_all(
            "Subcontracting Order",
            filters={"purchase_order": parada.po, "lote_ref": lote_ref, "docstatus": ["<", 2]},
            pluck="name",
        )
        cubierto = set()
        for s in scos_lote:
            cubierto |= set(frappe.get_all(
                "Subcontracting Order Item", filters={"parent": s}, pluck="item_code"
            ))
        if set(parada.fg_items) <= cubierto:
            saltadas.append(parada.parada_id)
            continue
        try:
            r = sub_crear_sco(
                parada.po, cantidades=parada.productos, fg_items=parada.fg_items,
                schedule_date=schedule_date, lote_ref=lote_ref, validar_stock=False,
            )
            sub_validar_sco(r["sco"])
            creadas.append({"parada_id": parada.parada_id, "supplier": parada.supplier,
                            "sco": r["sco"], "cantidades": r.get("cantidades")})
        except Exception as exc:
            errores.append(f"{parada.supplier}: {exc}")

    frappe.db.commit()
    return {"ok": not errores, "creadas": creadas, "saltadas": saltadas, "errores": errores}


@frappe.whitelist()
def sub_enviar_material(sco: str) -> dict:
    """Manda la materia prima al taller y deja listo el recibo: crea la transferencia,
    la VALIDA (el material sale del almacén de verdad) y crea el Subcontracting Receipt
    en BORRADOR, esperando la confirmación de cuánto entregó el taller.

    Junta 4 pasos que no aportaban ningún dato (crear transferencia, validarla, crear
    recibo) en una sola acción con un significado claro: "ya le mandé el material".
    Lo que NO se automatiza es validar el recibo -- ahí sí hay un dato real que sólo
    conoce el usuario (la cantidad entregada, con su merma o rechazo)."""
    if frappe.db.get_value("Subcontracting Order", sco, "docstatus") != 1:
        frappe.throw(_("Valida la orden de subcontratación primero."))

    se_name = frappe.db.get_value(
        "Stock Entry", {"subcontracting_order": sco, "purpose": "Send to Subcontractor", "docstatus": 1}, "name"
    )
    if not se_name:
        se_name = sub_transferir_material(sco)["stock_entry"]
        se = frappe.get_doc("Stock Entry", se_name)
        if se.docstatus == 0:
            se.flags.ignore_permissions = True
            se.submit()

    scr_name = sub_crear_recibo(sco)["scr"]
    frappe.db.commit()
    return {"ok": True, "stock_entry": se_name, "scr": scr_name}


@frappe.whitelist()
def sub_get_recibo(scr: str) -> dict:
    """Datos del Subcontracting Receipt (almacenes aceptado/rechazado/proveedor + líneas)."""
    doc = frappe.get_doc("Subcontracting Receipt", scr)
    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.status,
        "set_warehouse": doc.set_warehouse,
        "rejected_warehouse": doc.rejected_warehouse,
        "supplier_warehouse": doc.supplier_warehouse,
        "items": [
            {
                "name": r.name,
                "item_code": r.item_code,
                "item_name": r.item_name,
                "qty": r.qty,
                "rejected_qty": r.get("rejected_qty"),
                "warehouse": r.warehouse,
                "rejected_warehouse": r.get("rejected_warehouse"),
                "stock_uom": r.get("stock_uom"),
            }
            for r in (doc.items or [])
        ],
        "distribute_additional_costs_based_on": doc.get("distribute_additional_costs_based_on") or "Qty",
        "total_additional_costs": doc.get("total_additional_costs"),
        "additional_costs": [
            {"name": r.name, "description": r.description, "amount": r.amount, "expense_account": r.expense_account}
            for r in (doc.get("additional_costs") or [])
        ],
    }


@frappe.whitelist()
def sub_guardar_recibo(scr: str, set_warehouse=None, rejected_warehouse=None, supplier_warehouse=None, items=None,
                        costos=None, distribute_additional_costs_based_on=None) -> dict:
    """Guarda los almacenes, cantidades y costos adicionales (flete de regreso del taller,
    maniobras, etc.) del Subcontracting Receipt en borrador -- se capitalizan al valor
    del producto recibido. Al menos una fila (aunque sea $0) es obligatoria antes de
    validar -- ver validar_envio_capturado_recibo."""
    doc = frappe.get_doc("Subcontracting Receipt", scr)
    if doc.docstatus != 0:
        frappe.throw(_("El recibo ya está validado."))

    if set_warehouse:
        doc.set_warehouse = set_warehouse
        for it in doc.items:
            it.warehouse = set_warehouse
    if rejected_warehouse:
        doc.rejected_warehouse = rejected_warehouse
    if supplier_warehouse:
        doc.supplier_warehouse = supplier_warehouse

    if items is not None:
        rows = json.loads(items) if isinstance(items, str) else items
        has_rejected = bool(frappe.get_meta("Subcontracting Receipt Item").get_field("rejected_qty"))
        by_name = {r.get("name"): r for r in rows}
        for it in doc.items:
            r = by_name.get(it.name)
            if not r:
                continue
            if r.get("qty") is not None:
                it.qty = flt(r.get("qty"))
            if has_rejected and r.get("rejected_qty") is not None:
                it.rejected_qty = flt(r.get("rejected_qty"))
            if r.get("warehouse"):
                it.warehouse = r.get("warehouse")
            if r.get("rejected_warehouse"):
                it.rejected_warehouse = r.get("rejected_warehouse")

    if distribute_additional_costs_based_on and doc.meta.get_field("distribute_additional_costs_based_on"):
        doc.distribute_additional_costs_based_on = distribute_additional_costs_based_on

    if costos is not None:
        rows = json.loads(costos) if isinstance(costos, str) else costos
        doc.set("additional_costs", [])
        for r in rows:
            # OJO: solo se exige description -- amount=0 es una fila VÁLIDA (es
            # justamente "no hubo costo, pero ya se registró") y no debe descartarse
            # como si estuviera vacía, o el candado obligatorio de abajo nunca la vería.
            if not r.get("description"):
                continue
            doc.append("additional_costs", _landed_cost_row(doc.company, r.get("description"), flt(r.get("amount")), r.get("expense_account")))

    doc.flags.ignore_permissions = True
    doc.save()
    return {"ok": True}


def _dedupe_items_por_proveedor(rows, qty_by_item):
    kept = []
    seen = set()
    for it in rows:
        if it.item_code not in qty_by_item or it.item_code in seen:
            continue
        it.qty = qty_by_item[it.item_code]
        kept.append(it)
        seen.add(it.item_code)
    return kept


@frappe.whitelist()
def mr_crear_rfq(mr: str, supplier: str, items, lote_ref: str = None) -> dict:
    """Crea una Solicitud de Cotización (RFQ) para UN proveedor -- se dispara con su
    propio botón desde la pantalla del lote (no se genera sola al validar la
    solicitud, ni junta a todos los proveedores en un solo documento: cada
    proveedor tiene su RFQ, y sólo se crea cuando el usuario la pide)."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))
    from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

    rows = json.loads(items) if isinstance(items, str) else items
    qty_by_item = {r.get("item_code"): flt(r.get("qty")) for r in rows if r.get("item_code")}
    if not qty_by_item:
        frappe.throw(_("Indica al menos un material."))

    rfq = make_request_for_quotation(mr)
    rfq.set("items", _dedupe_items_por_proveedor(rfq.items, qty_by_item))
    if not rfq.items:
        frappe.throw(_("Ninguno de los materiales indicados sigue pendiente en la solicitud."))
    rfq.set("suppliers", [])
    rfq.append("suppliers", {"supplier": supplier})
    rfq.flags.ignore_permissions = True
    rfq.flags.ignore_mandatory = True
    rfq.insert()
    if lote_ref and frappe.db.has_column("Request for Quotation", "lote_ref"):
        frappe.db.set_value("Request for Quotation", rfq.name, "lote_ref", lote_ref, update_modified=False)
    if frappe.db.has_column("Request for Quotation", "costeo"):
        frappe.db.set_value("Request for Quotation", rfq.name, "costeo", doc.get("costeo"), update_modified=False)
    return {"ok": True, "rfq": rfq.name}


@frappe.whitelist()
def mr_crear_presupuesto_proveedor(mr: str, supplier: str, items, lote_ref: str = None) -> dict:
    """Crea un Presupuesto de Proveedor (Supplier Quotation) para UN proveedor -- mismo
    criterio que mr_crear_rfq: por su propio botón, un documento por proveedor."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))
    from erpnext.stock.doctype.material_request.material_request import make_supplier_quotation

    rows = json.loads(items) if isinstance(items, str) else items
    qty_by_item = {r.get("item_code"): flt(r.get("qty")) for r in rows if r.get("item_code")}
    if not qty_by_item:
        frappe.throw(_("Indica al menos un material."))

    sq = make_supplier_quotation(mr)
    sq.set("items", _dedupe_items_por_proveedor(sq.items, qty_by_item))
    if not sq.items:
        frappe.throw(_("Ninguno de los materiales indicados sigue pendiente en la solicitud."))
    sq.supplier = supplier
    sq.flags.ignore_permissions = True
    sq.flags.ignore_mandatory = True
    sq.insert()
    if lote_ref and frappe.db.has_column("Supplier Quotation", "lote_ref"):
        frappe.db.set_value("Supplier Quotation", sq.name, "lote_ref", lote_ref, update_modified=False)
    if frappe.db.has_column("Supplier Quotation", "costeo"):
        frappe.db.set_value("Supplier Quotation", sq.name, "costeo", doc.get("costeo"), update_modified=False)
    return {"ok": True, "supplier_quotation": sq.name}


FLETE_DESCRIPTION = "Flete / Envío"


def _get_shipping_row_amount(doc):
    """Lee el monto de la fila de flete (si existe) de la tabla 'taxes' del documento."""
    for r in (doc.get("taxes") or []):
        if r.description == FLETE_DESCRIPTION:
            return flt(r.tax_amount)
    return 0


def _set_purchase_shipping_row(doc, amount):
    """Agrega/edita la fila de flete en 'taxes' (Purchase Taxes and Charges),
    identificándola por su descripción para no duplicarla en guardados sucesivos.
    category='Valuation and Total' -> se suma al total a pagar AL PROVEEDOR y además
    se capitaliza al valor del material recibido (igual que ERPNext lo hace nativamente
    para cualquier Purchase Order/Purchase Receipt con costo de flete).

    OJO: la fila se guarda incluso en $0 -- nunca se elimina sola. "0 porque no hubo
    envío" tiene que quedar registrado como una respuesta explícita, distinta de
    "todavía nadie lo capturó" (sin fila). Eso es justo lo que usa el candado
    obligatorio del recibo -- ver _envio_capturado_taxes / _validar_envio_capturado_recibo."""
    amount = flt(amount)
    rows = doc.get("taxes") or []
    existing = next((r for r in rows if r.description == FLETE_DESCRIPTION), None)
    account = _default_landed_cost_account(doc.company)
    if existing:
        existing.tax_amount = amount
        existing.account_head = account
    else:
        doc.append("taxes", {
            "charge_type": "Actual",
            "account_head": account,
            "description": FLETE_DESCRIPTION,
            "category": "Valuation and Total",
            "add_deduct_tax": "Add",
            "tax_amount": amount,
        })


def _envio_capturado_taxes(doc):
    return any(r.description == FLETE_DESCRIPTION for r in (doc.get("taxes") or []))


def validar_envio_capturado_recibo(doc, method=None):
    """Hook before_submit (ver hooks.py, doc_events) -- en TODO recibo (materia prima o
    subcontratación) hay que dejar registrado el costo de envío antes de validar,
    aunque sea $0, para no dejarlo pasar en blanco -- sin importar si se llega aquí
    desde el SPA, el escritorio de Frappe o la consola.

    En el Recibo de compra (materia prima) esto es el campo dedicado "Costo de envío"
    (fila de flete en 'taxes', ver _envio_capturado_taxes). En el Recibo de
    subcontratación NO hay un campo aparte -- "Costos adicionales" (additional_costs)
    ya es justo eso (flete, maniobras, etc.), así que ahí basta con exigir que tenga
    AL MENOS una fila capturada (puede ser $0); duplicar un campo de envío aparte solo
    confundía con la misma tabla."""
    if doc.doctype == "Purchase Receipt":
        capturado = _envio_capturado_taxes(doc)
    elif doc.doctype == "Subcontracting Receipt":
        capturado = bool(doc.get("additional_costs"))
    else:
        return
    if not capturado:
        if doc.doctype == "Purchase Receipt":
            frappe.throw(_("Captura el costo de envío antes de validar el recibo (pon 0 si no hubo)."))
        else:
            frappe.throw(_("Registra al menos un costo adicional antes de validar el recibo (pon 0 si no hubo)."))


@frappe.whitelist()
def get_documento_compra(doctype: str, name: str) -> dict:
    """Detalle genérico de un documento de compra (OC / RFQ / Presupuesto de proveedor)."""
    doc = frappe.get_doc(doctype, name)
    meta = doc.meta

    items = []
    for it in doc.get("items") or []:
        items.append({
            "name": it.name,
            "item_code": it.item_code,
            "item_name": it.get("item_name"),
            "qty": it.get("qty"),
            "rate": it.get("rate"),
            "uom": it.get("uom"),
            "warehouse": it.get("warehouse"),
            "has_rate": bool(it.meta.get_field("rate")),
        })

    return {
        "doctype": doctype,
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.get("status"),
        "supplier": doc.get("supplier"),
        "transaction_date": str(doc.get("transaction_date") or ""),
        "has_posting_date": bool(meta.get_field("posting_date")),
        "posting_date": str(doc.get("posting_date") or ""),
        "set_warehouse": doc.get("set_warehouse") or "",
        "has_schedule_date": bool(meta.get_field("schedule_date")),
        "schedule_date": str(doc.get("schedule_date") or ""),
        "has_valid_till": bool(meta.get_field("valid_till")),
        "valid_till": str(doc.get("valid_till") or ""),
        "has_payment_terms": bool(meta.get_field("payment_terms_template")),
        "payment_terms_template": doc.get("payment_terms_template") or "",
        "has_tc": bool(meta.get_field("tc_name")),
        "tc_name": doc.get("tc_name") or "",
        "currency": doc.get("currency"),
        "grand_total": doc.get("grand_total"),
        "contact_email": doc.get("contact_email") or "",
        "contact_mobile": doc.get("contact_mobile") or "",
        # El costo de envío nunca se conoce todavía al momento de la OC -- se
        # captura hasta el Recibo de compra (materia prima), que es donde de verdad
        # aplica y donde es obligatorio (ver validar_envio_capturado_recibo).
        # shipping_cost=None (no 0) cuando nadie lo ha capturado todavía -- así el SPA
        # puede distinguir "$0 porque no hubo envío" (respuesta explícita) de "campo
        # vacío" (nadie lo llenó), que es justo lo que no se debe dejar pasar.
        "has_shipping": doctype == "Purchase Receipt",
        "shipping_cost": flt(_get_shipping_row_amount(doc)) if _envio_capturado_taxes(doc) else None,
        "enviado_el": str(doc.get("enviado_el") or "") if meta.get_field("enviado_el") else "",
        # Doble validación (Enviar -> Revisor -> Aprobador) -- hoy solo Purchase
        # Order (materia prima y subcontratada) tiene estos campos, ver patch
        # v0_2_30. Para el resto, requiere_doble_validacion viene en False y el
        # SPA no muestra el paso de "Revisar".
        "requiere_doble_validacion": meta.has_field("revisado_yelke"),
        "revisado_yelke": bool(doc.get("revisado_yelke")) if meta.has_field("revisado_yelke") else False,
        "revisado_por_yelke": doc.get("revisado_por_yelke") or "",
        "revisado_en_yelke": str(doc.get("revisado_en_yelke") or "") if meta.has_field("revisado_yelke") else "",
        "items": items,
    }


@frappe.whitelist()
def guardar_documento_compra(doctype: str, name: str, schedule_date=None, valid_till=None,
                             transaction_date=None, posting_date=None, payment_terms_template=None,
                             tc_name=None, items=None, shipping_cost=None) -> dict:
    """Guarda ediciones de un documento de compra en borrador.

    La UDM de línea solo se puede cambiar en la Orden de Compra (no en RFQ, Presupuesto
    de proveedor ni Recibo) -- es el punto donde ya se sabe con qué proveedor específico
    se está comprando, y ese proveedor puede vender en una unidad distinta a la que se
    costeó o a la que trae la Solicitud de Material. A diferencia de
    guardar_solicitud_material, aquí SÍ se permite cambiar a cualquier UDM del catálogo,
    exista o no ya una conversión dada de alta para el artículo -- si existe, se usa esa;
    si no, el factor de conversión se deja en 1 (igual que ERPNext nativo) para que se
    pueda ajustar a mano."""
    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 0:
        frappe.throw(_("El documento ya está validado; no se puede editar."))
    meta = doc.meta

    if transaction_date and meta.get_field("transaction_date"):
        doc.transaction_date = transaction_date
    if posting_date and meta.get_field("posting_date"):
        doc.posting_date = posting_date
    if schedule_date and meta.get_field("schedule_date"):
        doc.schedule_date = schedule_date
    if valid_till and meta.get_field("valid_till"):
        doc.valid_till = valid_till
    if meta.get_field("payment_terms_template"):
        doc.payment_terms_template = payment_terms_template or None
    if meta.get_field("tc_name"):
        doc.tc_name = tc_name or None
        if meta.get_field("terms"):
            doc.terms = resolver_terminos(tc_name)

    if items:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows if r.get("name")}
        for it in doc.get("items") or []:
            r = by_name.get(it.name)
            if not r:
                continue
            if r.get("qty") is not None:
                it.qty = flt(r.get("qty"))
            if r.get("rate") is not None and it.meta.get_field("rate"):
                it.rate = flt(r.get("rate"))
            if doctype == "Purchase Order" and r.get("uom") and it.meta.get_field("uom"):
                nuevo_uom = r.get("uom")
                if nuevo_uom != it.uom:
                    # stock_uom real del artículo (catálogo) -- NO el que trae el renglón,
                    # que puede venir "congelado" a la UDM con la que se armó la Solicitud
                    # de Material (ver _make_supplier_purchase_order en
                    # overrides/material_request.py). Se recalcula aquí siempre contra el
                    # maestro del artículo para que el factor de conversión sea correcto
                    # sin importar en qué UDM se haya costeado o solicitado originalmente.
                    stock_uom_real = frappe.db.get_value("Item", it.item_code, "stock_uom")
                    factor = _uom_conversion_factor(it.item_code, nuevo_uom, stock_uom=stock_uom_real)
                    it.uom = nuevo_uom
                    if it.meta.get_field("stock_uom"):
                        it.stock_uom = stock_uom_real
                    it.conversion_factor = factor if factor else 1.0

    if doctype in ("Purchase Order", "Purchase Receipt") and shipping_cost is not None and meta.get_field("taxes"):
        _set_purchase_shipping_row(doc, shipping_cost)

    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def plan_dividir_lotes(plan: str, item_code: str, lotes) -> dict:
    """Divide la cantidad planificada de un producto del plan en varios lotes
    (cantidad + fecha), para poder generar Órdenes de Trabajo escalonadas.

    `lotes` es una lista de dicts {"qty": float, "planned_start_date": "YYYY-MM-DD"}.
    La suma de los lotes debe igualar la cantidad ya planificada para el producto
    (ERPNext genera una Work Order por cada fecha distinta al crear las órdenes).
    """
    if isinstance(lotes, str):
        lotes = frappe.parse_json(lotes)
    if not lotes:
        frappe.throw(_("Indica al menos un lote."))

    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 0:
        frappe.throw(_("El plan ya está validado."))

    existing = [r for r in pp.get("po_items") or [] if r.item_code == item_code]
    if not existing:
        frappe.throw(_("El producto {0} no está en el plan.").format(item_code))

    total_actual = sum(flt(r.planned_qty) for r in existing)
    total_lotes = sum(flt(l.get("qty")) for l in lotes)
    if abs(total_lotes - total_actual) > 0.001:
        frappe.throw(_(
            "La suma de los lotes ({0}) debe ser igual a la cantidad planificada ({1})."
        ).format(total_lotes, total_actual))

    template = existing[0]
    keep = {
        "item_code":   template.item_code,
        "bom_no":      template.bom_no,
        "warehouse":   template.warehouse,
        "sales_order": template.sales_order,
        "sales_order_item": template.sales_order_item,
        "description": template.description,
        "stock_uom":   template.stock_uom,
    }
    pp.set("po_items", [r for r in pp.get("po_items") or [] if r.item_code != item_code])
    for lote in lotes:
        row = dict(keep)
        row["planned_qty"] = flt(lote.get("qty"))
        row["planned_start_date"] = lote.get("planned_start_date") or None
        pp.append("po_items", row)

    pp.flags.ignore_permissions = True
    pp.flags.ignore_mandatory = True
    pp.save()
    frappe.db.commit()
    return {
        "name": pp.name,
        "po_items": [{"item_code": r.item_code, "planned_qty": r.planned_qty, "bom_no": r.bom_no,
                      "planned_start_date": r.planned_start_date, "sales_order": r.sales_order}
                     for r in pp.get("po_items") or []],
    }


@frappe.whitelist()
def plan_crear_ordenes_trabajo(plan: str) -> dict:
    """Crea las Órdenes de Trabajo DESDE el plan (nativo, quedan asociadas)."""
    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 1:
        frappe.throw(_("Valida el plan primero."))
    pp.make_work_order()
    wos = frappe.get_all("Work Order", filters={"production_plan": plan}, pluck="name")
    return {"ok": True, "work_orders": wos}


@frappe.whitelist()
def plan_crear_subcontratacion(plan: str) -> dict:
    """Crea las OC de subcontratación por ETAPA (misma lógica del costeo, se conserva)
    y las liga al Production Plan a nivel de línea (production_plan + sub-assembly).

    La cantidad de cada etapa sale de los po_items DEL PLAN, no del costeo completo --
    el plan ya está ligado a una OV específica (desbloquear_plan_produccion lo construye
    con get_items_from='Sales Order'), así que sus po_items ya traen la cantidad
    correcta de ESA orden (puede ser distinta a la del costeo si es una réplica con otra
    cantidad). Las OC creadas quedan etiquetadas con esa misma OV (sales_order nativo en
    Purchase Order Item) para poder filtrarlas después por OV."""
    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 1:
        frappe.throw(_("Valida el plan primero."))
    costeo = pp.get("costeo")
    if not costeo:
        frappe.throw(_("El plan no está ligado a un costeo."))

    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import (
        _build_stage_subcontracting_rows,
        _create_subcontracting_pos_from_stages,
    )
    doc = frappe.get_doc("Costeo", costeo)
    source = doc.as_dict()

    sales_order = pp.sales_orders[0].sales_order if pp.get("sales_orders") else None
    qty_map_override = None
    if pp.get("po_items"):
        qty_map_override = {}
        for r in pp.get("po_items"):
            if r.item_code:
                qty_map_override[r.item_code] = qty_map_override.get(r.item_code, 0) + flt(r.planned_qty)

    stage_rows = _build_stage_subcontracting_rows(source, qty_map_override=qty_map_override)
    if not stage_rows:
        frappe.throw(_(
            "No hay etapas de subcontratación con proveedor y servicio. "
            "Configúralas en 'Etapas de Manufactura'."
        ))

    result = _create_subcontracting_pos_from_stages(source, stage_rows, sales_order=sales_order)
    po_names = result.get("purchase_orders", [])

    # Mapa production_item -> nombre de la fila sub_assembly_item del plan
    sub_map = {}
    for r in pp.get("sub_assembly_items") or []:
        if r.production_item and r.production_item not in sub_map:
            sub_map[r.production_item] = r.name

    for po_name in po_names:
        items = frappe.get_all("Purchase Order Item", filters={"parent": po_name},
                               fields=["name", "fg_item"])
        for it in items:
            frappe.db.set_value("Purchase Order Item", it.name, "production_plan", plan,
                                update_modified=False)
            if it.fg_item and sub_map.get(it.fg_item):
                frappe.db.set_value("Purchase Order Item", it.name,
                                    "production_plan_sub_assembly_item", sub_map[it.fg_item],
                                    update_modified=False)
        if frappe.db.has_column("Purchase Order", "costeo"):
            frappe.db.set_value("Purchase Order", po_name, "costeo", costeo, update_modified=False)

    frappe.db.commit()
    return {"ok": True, "purchase_orders": po_names}


@frappe.whitelist()
def get_reporte_final(costeo: str, sales_order: str = None) -> dict:
    """Reporte final del costeo: compara lo ESTIMADO (capturado en el paso 'Costear',
    guardado en Costeo Producto/Costeo Producto Detalle/Etapas Costeo) contra lo REAL,
    tomando los montos de los documentos ya VALIDADOS de todo el proceso -- compra de
    materia prima (+ su flete), subcontratación (servicio + flete de ida al taller +
    flete de regreso), flete de entrega al cliente, y la factura de venta real.

    ``sales_order``, si se manda, es la OV activa elegida en el SPA -- el reporte se
    calcula SOLO para esa OV: las cantidades del estimado se toman de SUS líneas (no del
    total histórico del costeo, que puede diferir si esta OV es una réplica con otra
    cantidad) y el lado real (OC de materiales/maquila, remisiones, factura) se filtra a
    los documentos ligados a esa OV. Sin ``sales_order`` cae al comportamiento anterior
    (todo el costeo junto), para costeos con una sola OV.

    Todo se calcula SIN IVA: se usan siempre net_total / item.amount (nunca grand_total),
    igual que el costeo interno nunca ha manejado IVA. Los documentos de flete (fila
    'Flete / Envío' en OC, 'Costos adicionales' en SCO/transferencia/recibo, flete_costo
    en remisión) tampoco llevan IVA -- son montos capturados directos, sin impuesto.

    Sólo cuenta como REAL lo que ya está validado (docstatus=1); lo que sigue en
    borrador se reporta aparte en 'pendientes' para que quede claro que el número
    todavía puede moverse."""
    doc = frappe.get_doc("Costeo", costeo)
    company = doc.compañia

    # Cantidad por producto: de la OV activa si se dio (sus propias líneas), si no la
    # del costeo completo (comportamiento previo).
    if sales_order:
        qty_por_producto = {
            r.item_code: flt(r.qty)
            for r in frappe.get_all("Sales Order Item", filters={"parent": sales_order},
                                    fields=["item_code", "qty"])
            if r.item_code
        }
    else:
        qty_por_producto = {p.finished_item: flt(p.qty) for p in doc.costeo_producto}

    # ── ESTIMADO (ya calculado y guardado en el paso Costear) ──────────────────
    productos = []
    est_costo_total = 0.0
    est_venta_total = 0.0
    est_overhead_total = 0.0
    for p in doc.costeo_producto:
        if sales_order and p.finished_item not in qty_por_producto:
            continue  # este producto del costeo no forma parte de la OV activa
        qty = qty_por_producto.get(p.finished_item, flt(p.qty))
        costo_u = flt(p.total_unit_cost)
        venta_u = flt(p.unit_sales_price)
        # total_sales_price ya guardado es exacto cuando la cantidad coincide con la del
        # costeo (puede incluir sobrecosto de tallas extraordinarias, no solo venta_u*qty);
        # si la OV activa tiene otra cantidad (réplica), se recalcula proporcional.
        if abs(qty - flt(p.qty)) < 0.001:
            venta_total_row = flt(p.total_sales_price) or (venta_u * qty)
        else:
            venta_total_row = venta_u * qty
        costo_total_row = costo_u * qty
        est_costo_total += costo_total_row
        est_venta_total += venta_total_row
        est_overhead_total += flt(p.overhead_amt) * qty
        productos.append({
            "finished_item": p.finished_item, "qty": qty,
            "material_cost_unit": flt(p.material_cost), "services_cost_unit": flt(p.services_cost),
            "shipping_cost_unit": flt(p.shipping_cost), "overhead_amt_unit": flt(p.overhead_amt),
            "overhead_pct": flt(p.overhead_pct),
            "total_unit_cost": costo_u, "unit_sales_price": venta_u, "margin_pct": flt(p.margin_pct),
            "costo_total": costo_total_row, "venta_total": venta_total_row,
        })
    base_sin_overhead = est_costo_total - est_overhead_total
    overhead_pct_prom = (est_overhead_total / base_sin_overhead * 100) if base_sin_overhead > 0 else 0

    # ── MATERIALES: estimado vs real ────────────────────────────────────────────
    # d.total/e.precio_servicio son costo POR UNIDAD del producto terminado -- para
    # comparar contra el gasto real (que sí es el total del proyecto) hay que escalar
    # cada renglón por la cantidad del producto al que pertenece.
    materiales_estimado = []
    materiales_estimado_total = 0.0
    for d in doc.costeo_producto_detalle:
        if d.concept_type != "Materia Prima" or not d.item:
            continue
        if sales_order and d.finished_item not in qty_por_producto:
            continue  # material de un producto que no está en la OV activa
        qty_producto = qty_por_producto.get(d.finished_item, 1)
        total_proyecto = flt(d.total) * qty_producto
        materiales_estimado_total += total_proyecto
        materiales_estimado.append({
            "item": d.item, "finished_item": d.finished_item, "proveedor": d.supplier,
            "precio_unitario": flt(d.unit_price), "cantidad": flt(d.internal_qty),
            "total": flt(d.total), "total_proyecto": total_proyecto,
        })

    so_po_names = None
    if sales_order:
        so_po_names = list(dict.fromkeys(frappe.get_all(
            "Purchase Order Item", filters={"sales_order": sales_order}, pluck="parent"
        ))) or [""]

    def _po_filters(is_subcontracted, docstatus):
        filters = {"costeo": costeo, "is_subcontracted": is_subcontracted, "docstatus": docstatus}
        if so_po_names is not None:
            filters["name"] = ["in", so_po_names]
        return filters

    mat_pos = frappe.get_all(
        "Purchase Order", filters=_po_filters(0, 1),
        fields=["name", "supplier", "supplier_name"], order_by="creation asc",
    )
    mat_pos_borrador = frappe.get_all(
        "Purchase Order", filters=_po_filters(0, 0), pluck="name",
    )
    materiales_real = []
    material_directo_real = 0.0
    flete_materiales_real = 0.0
    for po in mat_pos:
        po_doc = frappe.get_doc("Purchase Order", po.name)
        flete = _get_shipping_row_amount(po_doc)
        flete_materiales_real += flete
        for it in po_doc.items:
            material_directo_real += flt(it.amount)
            materiales_real.append({
                "po": po.name, "item_code": it.item_code, "item_name": it.item_name,
                "proveedor": po.supplier_name or po.supplier, "qty": flt(it.qty), "rate": flt(it.rate),
                "amount": flt(it.amount),
            })

    # ── SERVICIOS DE SUBCONTRATACIÓN: estimado vs real (+ fletes ida/regreso) ──
    servicios_estimado = []
    servicios_estimado_total = 0.0
    for e in doc.tabla_etapas_costeo:
        if sales_order and e.producto_terminado not in qty_por_producto:
            continue  # etapa de un producto que no está en la OV activa
        qty_producto = qty_por_producto.get(e.producto_terminado, 1)
        total_proyecto = flt(e.precio_servicio) * qty_producto
        servicios_estimado_total += total_proyecto
        servicios_estimado.append({
            "finished_item": e.producto_terminado, "etapa": e.etapa, "servicio": e.servicio,
            "proveedor": e.proveedor, "precio": flt(e.precio_servicio), "total_proyecto": total_proyecto,
        })

    sub_pos = frappe.get_all(
        "Purchase Order", filters=_po_filters(1, 1),
        fields=["name", "supplier", "supplier_name"], order_by="creation asc",
    )
    sub_pos_borrador = frappe.get_all(
        "Purchase Order", filters=_po_filters(1, 0), pluck="name",
    )
    servicios_real = []
    servicio_directo_real = 0.0
    flete_taller_ida_real = 0.0
    flete_taller_regreso_real = 0.0
    sco_borrador = se_borrador = scr_borrador = 0
    for po in sub_pos:
        po_doc = frappe.get_doc("Purchase Order", po.name)
        for it in po_doc.items:
            servicio_directo_real += flt(it.amount)
            servicios_real.append({
                "po": po.name, "item_code": it.item_code, "item_name": it.item_name,
                "proveedor": po.supplier_name or po.supplier, "qty": flt(it.qty), "rate": flt(it.rate),
                "amount": flt(it.amount),
            })

        scos = frappe.get_all("Subcontracting Order", filters={"purchase_order": po.name}, fields=["name", "docstatus"])
        for sco_row in scos:
            if sco_row.docstatus == 0:
                sco_borrador += 1
                continue
            if sco_row.docstatus != 1:
                continue
            sco_doc = frappe.get_doc("Subcontracting Order", sco_row.name)
            for c in sco_doc.additional_costs:
                flete_taller_ida_real += flt(c.amount)

            ses = frappe.get_all(
                "Stock Entry",
                filters={"subcontracting_order": sco_row.name, "purpose": "Send to Subcontractor"},
                fields=["name", "docstatus"],
            )
            for se_row in ses:
                if se_row.docstatus == 0:
                    se_borrador += 1
                    continue
                if se_row.docstatus != 1:
                    continue
                se_doc = frappe.get_doc("Stock Entry", se_row.name)
                for c in se_doc.additional_costs:
                    flete_taller_ida_real += flt(c.amount)

            scr_names = list(dict.fromkeys(frappe.get_all(
                "Subcontracting Receipt Item", filters={"subcontracting_order": sco_row.name}, pluck="parent",
            )))
            for scr_name in scr_names:
                scr_status = frappe.db.get_value("Subcontracting Receipt", scr_name, "docstatus")
                if scr_status == 0:
                    scr_borrador += 1
                    continue
                if scr_status != 1:
                    continue
                scr_doc = frappe.get_doc("Subcontracting Receipt", scr_name)
                for c in scr_doc.additional_costs:
                    flete_taller_regreso_real += flt(c.amount)

    # ── ENVÍO AL CLIENTE: estimado vs real ──────────────────────────────────────
    shipping_estimado_total = sum(
        flt(p.shipping_cost) * qty_por_producto.get(p.finished_item, flt(p.qty))
        for p in doc.costeo_producto
        if not sales_order or p.finished_item in qty_por_producto
    )
    if sales_order:
        dn_parents = list(dict.fromkeys(frappe.get_all(
            "Delivery Note Item", filters={"against_sales_order": sales_order, "docstatus": 1}, pluck="parent",
        )))
        dn_parents_borrador = list(dict.fromkeys(frappe.get_all(
            "Delivery Note Item", filters={"against_sales_order": sales_order, "docstatus": 0}, pluck="parent",
        )))
        dns = frappe.get_all(
            "Delivery Note", filters={"name": ["in", dn_parents or [""]]},
            fields=["name", "flete_costo", "flete_proveedor", "flete_journal_entry"],
        )
        dns_borrador = dn_parents_borrador
    else:
        dns = frappe.get_all(
            "Delivery Note", filters={"costeo": costeo, "docstatus": 1},
            fields=["name", "flete_costo", "flete_proveedor", "flete_journal_entry"],
        )
        dns_borrador = frappe.get_all("Delivery Note", filters={"costeo": costeo, "docstatus": 0}, pluck="name")
    flete_cliente_real = sum(flt(d.flete_costo) for d in dns)

    # ── INGRESO REAL (factura de venta, sin IVA) ────────────────────────────────
    # Sales Invoice no siempre trae el campo 'costeo' directo (depende de si el sitio
    # ya tiene ese custom field) -- se busca igual que en get_costeo_related: vía
    # Sales Invoice Item.sales_order, que es el enlace confiable. Con OV activa se usa
    # ESA orden; sin ella, la más reciente del costeo (comportamiento previo).
    si = None
    si_borrador = False
    so_name = sales_order or frappe.db.get_value(
        "Sales Order", {"costeo": costeo}, "name", order_by="creation desc"
    )
    if so_name:
        si_parents = list(dict.fromkeys(frappe.get_all(
            "Sales Invoice Item", filters={"sales_order": so_name, "docstatus": ["<", 2]}, pluck="parent",
        )))
        for p in si_parents:
            row = frappe.db.get_value("Sales Invoice", p, ["name", "docstatus", "net_total", "grand_total"], as_dict=True)
            if not row:
                continue
            if row.docstatus == 1:
                si = row
            elif row.docstatus == 0:
                si_borrador = True
    ingreso_real = flt(si.net_total) if si else 0.0

    # ── TOTALES Y RENTABILIDAD ───────────────────────────────────────────────────
    costo_directo_real = (
        material_directo_real + flete_materiales_real
        + servicio_directo_real + flete_taller_ida_real + flete_taller_regreso_real
        + flete_cliente_real
    )
    # El overhead es un % FIJO (lo estipula contabilidad aparte -- luz, nóminas, renta) que
    # se aplica sobre el costo real total (la suma de OC de materiales, OC/SCO de
    # subcontratación y los distintos fletes -- costo_directo_real, ya calculado arriba).
    # Lo fijo es la TASA, no el monto: si el costo real sube (cambio de proveedor, flete
    # imprevisto, etc.) el overhead absorbido sube proporcionalmente con él, igual que
    # cualquier costeo por absorción -- no se congela al monto estimado.
    overhead_real = costo_directo_real * (overhead_pct_prom / 100) if overhead_pct_prom else 0.0
    costo_total_real = costo_directo_real + overhead_real

    # Cantidad real (de la REMISIÓN, no de la factura -- el overhead acompaña al costo,
    # no al precio/ingreso) solo para mostrar un "unitario" de referencia en el reporte.
    qty_real_total = 0.0
    if dns:
        for it in frappe.get_all("Delivery Note Item", filters={"parent": ["in", [d.name for d in dns]]}, fields=["qty"]):
            qty_real_total += flt(it.qty)

    # Unitario = promedio ponderado (total / cantidad) -- coincide con overhead_amt_unit
    # cuando solo hay un producto; con varios productos de tarifa distinta puede diferir
    # del estimado si la MEZCLA real de productos remisionados no fue la planeada.
    est_qty_total = sum(qty_por_producto.get(p.finished_item, flt(p.qty)) for p in doc.costeo_producto
                        if not sales_order or p.finished_item in qty_por_producto)
    overhead_unit_estimado = (est_overhead_total / est_qty_total) if est_qty_total else 0
    overhead_unit_real = (overhead_real / qty_real_total) if qty_real_total else 0

    rentabilidad_estimada_monto = est_venta_total - est_costo_total
    rentabilidad_estimada_pct = (rentabilidad_estimada_monto / est_venta_total * 100) if est_venta_total else 0
    rentabilidad_real_monto = ingreso_real - costo_total_real
    rentabilidad_real_pct = (rentabilidad_real_monto / ingreso_real * 100) if ingreso_real else 0

    pendientes = {
        "ocs_materia_prima_borrador": len(mat_pos_borrador),
        "ocs_subcontratacion_borrador": len(sub_pos_borrador),
        "sco_borrador": sco_borrador, "transferencias_borrador": se_borrador,
        "recibos_borrador": scr_borrador, "remisiones_borrador": len(dns_borrador),
        "factura_venta_borrador": bool(si_borrador),
    }
    completo = bool(si) and not any(pendientes.values())

    return {
        "costeo": costeo, "cliente": doc.cliente, "compania": company, "completo": completo,
        "pendientes": pendientes,
        "estimado": {
            "productos": productos, "materiales": materiales_estimado, "servicios": servicios_estimado,
            "materiales_total": materiales_estimado_total, "servicios_total": servicios_estimado_total,
            "shipping_total": shipping_estimado_total, "overhead_pct_promedio": overhead_pct_prom,
            "overhead_total": est_overhead_total, "overhead_unit": overhead_unit_estimado, "qty_total": est_qty_total,
            "costo_total": est_costo_total, "venta_total": est_venta_total,
            "rentabilidad_pct": rentabilidad_estimada_pct, "rentabilidad_monto": rentabilidad_estimada_monto,
        },
        "real": {
            "materiales": materiales_real, "material_directo": material_directo_real,
            "flete_materiales": flete_materiales_real,
            "servicios": servicios_real, "servicio_directo": servicio_directo_real,
            "flete_taller_ida": flete_taller_ida_real, "flete_taller_regreso": flete_taller_regreso_real,
            "flete_cliente": flete_cliente_real,
            "costo_directo": costo_directo_real, "overhead": overhead_real, "overhead_unit": overhead_unit_real,
            "qty_total": qty_real_total, "costo_total": costo_total_real,
            "ingreso": ingreso_real, "sales_invoice": si.name if si else None,
            "rentabilidad_pct": rentabilidad_real_pct, "rentabilidad_monto": rentabilidad_real_monto,
        },
        "variacion": {
            "costo_monto": costo_total_real - est_costo_total,
            "costo_pct": ((costo_total_real - est_costo_total) / est_costo_total * 100) if est_costo_total else 0,
            "venta_monto": ingreso_real - est_venta_total,
            "venta_pct": ((ingreso_real - est_venta_total) / est_venta_total * 100) if est_venta_total else 0,
            "rentabilidad_pct_puntos": rentabilidad_real_pct - rentabilidad_estimada_pct,
            "rentabilidad_monto": rentabilidad_real_monto - rentabilidad_estimada_monto,
        },
    }


@frappe.whitelist()
def enviar_por_correo(doctype: str, name: str, recipients: str, subject: str = None, message: str = None, print_format: str = None) -> dict:
    """Envía un documento por correo.

    Adjunta el PDF si el generador está disponible (wkhtmltopdf); si no,
    envía el documento renderizado como HTML en el cuerpo (sin dependencia).
    """
    recipient_list = [r.strip() for r in (recipients or "").replace(";", ",").split(",") if r.strip()]
    if not recipient_list:
        frappe.throw(_("Indica al menos un destinatario."))

    fmt = print_format or "Standard"
    attachments = None
    body = message or f"Adjunto {doctype} {name}."
    used = "pdf"

    try:
        attachments = [frappe.attach_print(doctype, name, print_format=fmt)]
    except Exception:
        # Sin wkhtmltopdf: incrustar el documento como HTML en el cuerpo del correo.
        used = "html"
        print_html = frappe.get_print(doctype, name, print_format=fmt)
        body = (message or "") + "<br><br>" + print_html

    frappe.sendmail(
        recipients=recipient_list,
        subject=subject or f"{doctype} {name}",
        message=body,
        attachments=attachments,
        reference_doctype=doctype,
        reference_name=name,
    )
    if doctype == "Purchase Order" and frappe.db.has_column("Purchase Order", "enviado_el"):
        frappe.db.set_value("Purchase Order", name, "enviado_el", frappe.utils.now_datetime(), update_modified=False)
        frappe.db.commit()
    return {"ok": True, "sent_to": recipient_list, "attachment": used}
