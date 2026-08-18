import json
import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, getdate, nowdate

from costeo_yelke.api import item_api

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


def _sobrecosto_titulo(sobrecosto_tipo, sobrecosto_valor):
    if sobrecosto_tipo == "Porcentaje":
        return f"Tallas extra (+{flt(sobrecosto_valor):g}%)"
    return f"Tallas extra (+${flt(sobrecosto_valor):,.2f} c/u)"


def _build_talla_extra_description(base_description, sobrecosto_tipo, sobrecosto_valor, rows):
    """Descripción autogenerada para la línea de tallas extra: mismo producto,
    listando qué tallas llevan el sobrecosto. No exige cantidad -- lo normal
    es que al cotizar no se sepa cuántas piezas serán tallas extra, solo que
    existe el ajuste de precio; si sí se capturó cantidad por talla, se
    incluye como referencia."""
    titulo = _sobrecosto_titulo(sobrecosto_tipo, sobrecosto_valor)
    lineas = []
    for t in rows:
        etiqueta = " ".join(filter(None, [t.genero, _talla_label(t.talla)]))
        sufijo = f" × {cint(t.qty)} pza(s)" if flt(t.qty) > 0 else ""
        lineas.append(f"- {etiqueta}{sufijo}")
    bloque = f"{titulo}:\n" + "\n".join(lineas)
    base = (base_description or "").strip()
    return f"{base}\n\n{bloque}" if base else bloque


def _quotation_items_para_producto(doc, p):
    """Arma las líneas de Quotation Item para un Costeo Producto: la línea
    base con la descripción normal, más una línea aparte por cada grupo de
    sobrecosto de talla (agrupando las que comparten mismo tipo/valor), ya
    que en la práctica casi nunca se conoce el desglose exacto de piezas por
    talla extra al cotizar -- solo el % o monto de ajuste. Si sí se captura
    cantidad por talla, esa cantidad se resta de la línea base y se usa en la
    línea extra en vez del 1 de referencia."""
    talla_rows = _tallas_extra_para_producto(doc, p.finished_item)

    if not talla_rows:
        item = {"item_code": p.finished_item, "qty": p.qty, "rate": p.unit_sales_price or 0}
        if p.description:
            item["description"] = p.description
        return [item]

    grupos = {}
    for t in talla_rows:
        key = (t.sobrecosto_tipo, flt(t.sobrecosto_valor))
        grupos.setdefault(key, []).append(t)

    total_talla_qty = sum(flt(t.qty) for t in talla_rows)
    base_qty = flt(p.qty) - total_talla_qty if total_talla_qty > 0 else flt(p.qty)

    items = []
    if base_qty > 0:
        item = {"item_code": p.finished_item, "qty": base_qty, "rate": p.unit_sales_price or 0}
        if p.description:
            item["description"] = p.description
        items.append(item)

    for (sobrecosto_tipo, sobrecosto_valor), rows in grupos.items():
        qty_grupo = sum(flt(t.qty) for t in rows)
        qty = qty_grupo if qty_grupo > 0 else 1
        rate = rows[0].precio_venta or p.unit_sales_price or 0
        items.append({
            "item_code": p.finished_item,
            "qty": qty,
            "rate": rate,
            "description": _build_talla_extra_description(p.description, sobrecosto_tipo, sobrecosto_valor, rows),
        })

    return items


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
        for item in _quotation_items_para_producto(doc, p):
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
    mx_product_service_key: str = None,
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
        if mx_product_service_key:
            payload["mx_product_service_key"] = mx_product_service_key
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

    candidatos = set()
    for d in doc.costeo_producto_detalle:
        if d.concept_type == "Materia Prima" and d.item:
            candidatos.add(d.item)
    for e in doc.tabla_etapas_costeo:
        if e.servicio:
            candidatos.add(e.servicio)
        if e.subensamblaje:
            candidatos.add(e.subensamblaje)
    for s in doc.get("tabla_salidas_etapa") or []:
        if s.subensamblaje:
            candidatos.add(s.subensamblaje)

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

    # Las etapas se procesan por producto usando el mismo grafo de dependencias
    # que crear_boms_spa / crear_subcontracting_bom (_resolve_stage_graph) -- la
    # etapa TERMINAL (nadie la referencia como entrada, puede ser resultado de
    # varios procesos en paralelo que convergen) usa finished_item como resultado,
    # NO el texto que haya en "subensamblaje" de esa fila (ese campo se ignora
    # ahí). Si no replicamos el mismo criterio aquí, el checklist le pide al
    # usuario materializar como "Sub-Ensamblaje" un texto que en realidad es
    # simplemente el producto terminado.
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

    advertencias = []
    for producto in doc.costeo_producto:
        fi = producto.finished_item
        if not fi:
            continue
        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == fi]
        graph_info, etapas_ord = _resolve_stage_graph(etapas_prod, doc.get("tabla_salidas_etapa"))
        for e in etapas_ord:
            es_ultima = graph_info.get(e.get("node_key"), {}).get("is_terminal", True)
            # La UDM del servicio es lote_uom (lo que ya se capturó en el costeo, ej.
            # "Pieza") -- y si el proveedor cobra por lote (lote_qty > 1, ej. $19 por
            # 25 confecciones), se sugiere de una vez la conversión "1 Lote = lote_qty
            # {lote_uom}" para no volver a capturarla al crear el Item.
            lote_qty = flt(e.lote_qty) or 1
            add(
                "servicio_etapa", e.servicio, "Servicios", e.proveedor, e.producto_terminado,
                unit_price=e.precio_servicio,
                internal_uom=e.lote_uom,
                supplier_uom=LOTE_UOM if lote_qty > 1 else None,
                conversion_factor=lote_qty if lote_qty > 1 else None,
            )
            if not es_ultima:
                if not e.subensamblaje:
                    advertencias.append(
                        f'La etapa "{e.servicio or e.etapa}" de "{fi}" todavía no tiene sub-ensamblaje '
                        "que produce -- complétalo en 'Preparar Manufactura' o los BOMs no se podrán crear."
                    )
                add("subensamblaje_etapa", e.subensamblaje, "Sub-Ensamblajes", None, e.producto_terminado)
            elif e.subensamblaje and e.subensamblaje != fi:
                advertencias.append(
                    f'En la última etapa de "{fi}", el sub-ensamblaje capturado ("{e.subensamblaje}") '
                    f"se ignora — el resultado de la etapa terminal siempre es el producto terminado."
                )

    return {
        "grupos": list(grupos.values()),
        "advertencias": advertencias,
        "company": doc.compañia,
        "almacen_materias_primas": doc.almacen_materias_primas or "",
        "almacen_trabajo_en_proceso": doc.almacen_trabajo_en_proceso or "",
    }


@frappe.whitelist()
def materializar_articulo(costeo: str, row_type: str, texto: str, item_code: str, prefill=None, supplier: str = None, precio: float = None) -> dict:
    """Resuelve un grupo de renglones de material/servicio/subensamblaje en texto
    libre: si item_code ya existe, solo vincula (reescribe el texto libre por el
    item_code en todos los renglones que comparten ese mismo texto); si es nuevo,
    lo crea reutilizando item_api.create_item con el 'prefill' armado en el
    frontend (mismo patrón de ProductoNuevoPage.vue), inyectando el proveedor ya
    conocido del renglón en supplier_items antes de crear. Si el prefill no trae
    item_defaults/item_prices, se completan automáticamente con la compañía,
    almacén y precio de compra ya conocidos del costeo -- para no obligar al
    usuario a repetir configuración que ya existe en el renglón."""
    if isinstance(prefill, str):
        prefill = json.loads(prefill) if prefill else {}
    prefill = dict(prefill or {})

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

    if row_type == "subensamblaje_etapa":
        # El mismo texto libre también puede vivir en tabla_salidas_etapa (etapas
        # con más de una salida) -- vive como tabla HERMANA de Etapas Costeo en
        # Costeo (parent = el costeo, igual que arriba), no anidada dentro de la
        # etapa. Actualiza ambos lugares para que el checklist no vuelva a
        # detectar la misma salida como pendiente.
        frappe.db.set_value(
            "Etapa Costeo Salida", {"parent": costeo, "subensamblaje": texto}, "subensamblaje", item_code
        )

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
            }),
        )
        creados.append(item_code)
    return {"creados": creados}


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
    """Valida (submit) un documento en borrador."""
    doc = frappe.get_doc(doctype, name)
    doc.flags.ignore_permissions = True
    doc.submit()
    if doctype == "Sales Invoice" and frappe.db.has_column("Sales Invoice", "overhead_journal_entry"):
        _contabilizar_overhead_factura(doc)
    return {"name": doc.name, "docstatus": doc.docstatus}


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
        so.append("items", {
            "item_code": p.finished_item,
            "qty": p.qty,
            "rate": p.unit_sales_price or 0,
            "delivery_date": deliv,
        })

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

        po_qty = flt(frappe.db.get_value("Purchase Order Item", {"parent": po.name}, "qty"))
        scos = frappe.get_all(
            "Subcontracting Order", filters={"purchase_order": po.name, "docstatus": 1}, fields=["name"]
        )
        if not scos:
            continue
        out["lotes_total"] += len(scos)

        sco_qty_total = flt(frappe.db.sql(
            """select coalesce(sum(qty), 0) from `tabSubcontracting Order Item`
               where parent in %(scos)s""",
            {"scos": [s.name for s in scos]},
        )[0][0])

        scr_qtys = frappe.db.sql(
            """select sri.subcontracting_order as sco, sum(sri.qty) as qty
               from `tabSubcontracting Receipt Item` sri
               inner join `tabSubcontracting Receipt` sr on sr.name = sri.parent
               where sri.subcontracting_order in %(scos)s and sr.docstatus = 1
               group by sri.subcontracting_order""",
            {"scos": [s.name for s in scos]},
            as_dict=True,
        )
        scr_qty_map = {r.sco: flt(r.qty) for r in scr_qtys}

        todas_recibidas = True
        qty_recibida = 0.0
        for sco in scos:
            q = scr_qty_map.get(sco.name, 0.0)
            if q > 0:
                out["lotes_recibidos"] += 1
                qty_recibida += q
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
        "customer_name": doc.customer_name,
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

    costo_venta_account = frappe.get_cached_value(
        "Account", {"account_name": "COSTO DE VENTAS", "company": si_doc.company}, "name"
    )
    if not costo_venta_account:
        frappe.throw(_("No se encontró la cuenta 'COSTO DE VENTAS' para la compañía {0}.").format(si_doc.company))
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
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def dashboard_metrics() -> dict:
    """Métricas del flujo de costeo → venta → producción subcontratada → facturación."""
    from frappe.utils import add_months

    # Todas las métricas monetarias usan el NETO (sin IVA): el impuesto es trasladado,
    # no es ingreso ni costo real. base_net_total = neto en moneda de la compañía.
    def suma(dt, field="base_net_total", filters=None):
        f = dict(filters or {})
        f["docstatus"] = ["<", 2]
        rows = frappe.get_all(dt, filters=f, fields=[f"sum({field}) as t"])
        return flt(rows[0].t) if rows and rows[0].t else 0.0

    # ── Costeos por estado (pipeline) ────────────────────────────────────────
    estados = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado"]
    por_estado = {e: 0 for e in estados}
    for r in frappe.get_all("Costeo", fields=["costeo_status", "count(name) as n"], group_by="costeo_status"):
        st = r.get("costeo_status") or "Borrador"
        por_estado[st] = por_estado.get(st, 0) + (r.n or 0)
    total_costeos = sum(por_estado.values())

    # ── Embudo de valor ──────────────────────────────────────────────────────
    valor_cotizado = suma("Quotation")
    valor_vendido = suma("Sales Order")
    valor_facturado = suma("Sales Invoice")
    compras_mp = suma("Purchase Order", filters={"is_subcontracted": 0})
    gasto_maquila = suma("Purchase Order", filters={"is_subcontracted": 1})

    # ── Prendas ──────────────────────────────────────────────────────────────
    prendas_vendidas = suma("Sales Order", field="total_qty")

    # ── Margen promedio (del costeo) ─────────────────────────────────────────
    margen_prom = 0.0
    cp = frappe.get_meta("Costeo").get_field("costeo_producto")
    cp_dt = cp.options if cp else None
    if cp_dt and frappe.db.has_column(cp_dt, "margin_pct"):
        r = frappe.db.sql(f"SELECT AVG(margin_pct) FROM `tab{cp_dt}` WHERE margin_pct > 0")
        margen_prom = flt(r[0][0]) if r and r[0][0] else 0.0

    # ── Producción subcontratada (avance) ────────────────────────────────────
    sub_pos = frappe.get_all("Purchase Order", filters={"is_subcontracted": 1, "docstatus": 1}, pluck="name")
    recibidas = 0
    for po in sub_pos:
        sco = frappe.db.get_value("Subcontracting Order", {"purchase_order": po, "docstatus": 1}, "name")
        if sco and frappe.db.get_value("Subcontracting Receipt Item", {"subcontracting_order": sco, "docstatus": 1}, "parent"):
            recibidas += 1
    total_sub = len(sub_pos)

    # ── Top clientes (por valor de OV) ───────────────────────────────────────
    top_clientes = frappe.get_all(
        "Sales Order",
        filters={"docstatus": ["<", 2]},
        fields=["customer", "sum(base_net_total) as monto", "sum(total_qty) as prendas", "count(name) as ordenes"],
        group_by="customer", order_by="monto desc", limit=6,
    )

    # ── Talleres (gasto de maquila por proveedor) ────────────────────────────
    talleres = frappe.get_all(
        "Purchase Order",
        filters={"is_subcontracted": 1, "docstatus": ["<", 2]},
        fields=["supplier", "supplier_name", "sum(base_net_total) as monto", "count(name) as ordenes"],
        group_by="supplier", order_by="monto desc", limit=6,
    )

    # ── Facturado por mes (últimos 6) ────────────────────────────────────────
    facturado_mes = frappe.db.sql(
        """SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS mes, SUM(base_net_total) AS monto
           FROM `tabSales Invoice`
           WHERE docstatus < 2 AND posting_date >= %s
           GROUP BY mes ORDER BY mes""",
        (add_months(nowdate(), -5),), as_dict=True,
    )

    return {
        "total_costeos": total_costeos,
        "costeos_por_estado": por_estado,
        "valor_cotizado": valor_cotizado,
        "valor_vendido": valor_vendido,
        "valor_facturado": valor_facturado,
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
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

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

    # ── 3. Procesar cada producto ─────────────────────────────────────────────
    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        if not finished_item or float(producto.qty or 0) <= 0:
            continue

        etapas = etapas_por_producto.get(finished_item, [])
        if not etapas:
            errors.append(f"{finished_item}: sin etapas configuradas")
            continue

        # graph_info/etapas_ord ya vienen en orden topológico -- procesa primero
        # las etapas raíz, así el BOM que una etapa referencia como upstream ya
        # existe cuando le toca su turno. Si el costeo nunca usó "recibe_de"
        # (procesos en paralelo), _resolve_stage_graph cae al comportamiento
        # lineal de siempre (cadena estricta por número de etapa).
        graph_info, etapas_ord = _resolve_stage_graph(etapas, doc.get("tabla_salidas_etapa"))
        # Cada entrada es (fila_de_material, qty_por_pieza): la cantidad ya viene
        # repartida por etapa cuando el costeo declaró el reparto explícito (ver
        # _split_materials_by_stage), en vez de asumir que la etapa consume el
        # material completo.
        mats_by_key, mats_sin_etapa = _split_materials_by_stage(
            mats_por_producto.get(finished_item, []), etapas, doc.get("tabla_materiales_etapa")
        )
        root_keys = {k for k, info in graph_info.items() if not info["upstream"]}

        for etapa_cfg in etapas_ord:
            node_key = etapa_cfg.get("node_key")
            g = graph_info.get(node_key, {})
            es_ultima     = g.get("is_terminal", True)
            subensamblaje = etapa_cfg.get("subensamblaje") or ""
            etapa_num_str = str(etapa_cfg.get("etapa") or "")
            # Fracción de esta salida sobre el costo TOTAL de la etapa (100% si la
            # etapa no tiene 'salidas'), derivada de las cantidades producidas.
            # Reparte la materia prima de la etapa entre sus salidas sin
            # duplicar/triplicar el consumo.
            pct = (float(etapa_cfg.get("pct_participacion") or 100)) / 100.0
            # Unidades de ESTA salida por pieza de producto terminado. El BOM se arma
            # para 1 unidad del ítem, así que el material que le toca a la salida
            # (mat x pct) se divide entre las unidades que produce; quien la consuma
            # río abajo pedirá qty_salida de ellas y el total vuelve a cuadrar.
            qty_salida = float(etapa_cfg.get("qty_salida") or 1) or 1

            # Ítem para el que se crea el BOM
            bom_item = finished_item if es_ultima else subensamblaje
            if not bom_item:
                errors.append(
                    f"{finished_item} (etapa {etapa_num_str}): falta el sub-ensamblaje que "
                    "produce esta etapa. Complétalo en 'Preparar Manufactura' antes de crear los BOMs."
                )
                continue

            # ── Ítems del BOM ────────────────────────────────────────────────
            items_bom = []

            # Sub-ensamblajes de las etapas de las que ESTA recibe -- puede ser
            # más de una (procesos en paralelo que convergen, ej. confección +
            # bordado de manga entrando ambos al ensamble final).
            for up in g.get("upstream", []):
                up_sub = up.get("subensamblaje") or ""
                if not up_sub:
                    continue
                up_uom = frappe.db.get_value("Item", up_sub, "stock_uom") or "Nos"
                # Referencia explícita al BOM del subensamblaje previo, para que la
                # explosión multinivel del Production Plan recurra correctamente.
                up_bom = frappe.db.get_value(
                    "BOM", {"item": up_sub, "is_active": 1, "docstatus": ["in", [0, 1]], "company": company}, "name"
                ) or ""
                items_bom.append({
                    "item_code": up_sub,
                    # Cuántas unidades de esa salida lleva una pieza de lo que produce
                    # ESTA etapa (ej. 2 mangas cortadas iguales por prenda).
                    "qty":       float(up.get("qty_salida") or 1) or 1,
                    "uom":       up_uom,
                    "stock_uom": up_uom,
                    "rate":      0,
                    "bom_no":    up_bom,
                })

            # Materias primas de esta etapa. Las materias primas SIN etapa asignada
            # se incluyen en la(s) etapa(s) RAÍZ (sin upstream) -- ahí es donde
            # arranca la producción. La atribución sigue siendo por ETAPA física
            # (parent_stage_key), no por salida individual -- el material lo
            # consume la operación completa, no una salida en particular.
            stage_mats = list(mats_by_key.get(etapa_cfg.get("parent_stage_key"), []))
            if node_key in root_keys:
                stage_mats += mats_sin_etapa

            for mat, mat_qty in stage_mats:
                uom = (mat.internal_uom
                       or frappe.db.get_value("Item", mat.item, "stock_uom")
                       or "Nos")
                # pct sigue aplicando ENCIMA del reparto por etapa: mat_qty es lo que
                # consume la operación completa, y pct lo divide entre las salidas de
                # esa operación (100% si la etapa tiene una sola salida). El /qty_salida
                # lo baja a "por unidad" del ítem para el que se arma este BOM.
                qty = mat_qty * pct / qty_salida
                items_bom.append({
                    "item_code": mat.item,
                    "qty":       qty,
                    "uom":       uom,
                    "stock_uom": uom,
                    "rate":      0,
                })

            if not items_bom:
                errors.append(
                    f"{bom_item} (etapa {etapa_num_str}): no tiene materiales ni sub-ensamblaje "
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
                if frappe.db.has_column("BOM", "salida_id"):
                    bom.salida_id = node_key
                for it in items_bom:
                    bom.append("items", it)
                bom.flags.ignore_permissions = True
                bom.flags.ignore_links       = True
                bom.insert()
                bom.submit()
                created.append(bom.name)
            except Exception as exc:
                errors.append(f"{bom_item} (etapa {etapa_num_str}): {exc}")

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
    """Creates one Subcontracting BOM per stage (etapa), matching the original JS logic:
    - Non-last stage  → finished_good = subensamblaje of that stage
    - Last stage      → finished_good = finished_item of the product
    Skips if a Subcontracting BOM already exists for that finished_good."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

    doc     = frappe.get_doc("Costeo", costeo)
    created, errors, skipped = [], [], []

    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        if not finished_item:
            continue

        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == finished_item]
        if not etapas_prod:
            continue
        graph_info, etapas = _resolve_stage_graph(etapas_prod, doc.get("tabla_salidas_etapa"))

        for etapa in etapas:
            node_key      = etapa.get("node_key")
            servicio      = etapa.servicio
            subensamblaje = etapa.subensamblaje
            es_ultima     = graph_info.get(node_key, {}).get("is_terminal", True)
            finished_good = finished_item if es_ultima else subensamblaje
            # % de esta salida sobre el precio de servicio de la etapa completa (100
            # si la etapa no tiene 'salidas' -- sin cambio de comportamiento).
            pct = (float(etapa.get("pct_participacion") or 100)) / 100.0
            qty_salida = float(etapa.get("qty_salida") or 1) or 1

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

            # Si el proveedor cobra por lote (ej. $19 por 25 confecciones, lote_qty=25,
            # lote_uom="H87 - Pieza" en la etapa del Costeo), el Subcontracting BOM debe
            # reflejar "1 Lote de servicio produce lote_qty [lote_uom] de producto" -- no
            # "1 servicio = 1 pieza" como antes, correcto solo si lote_qty=1.
            lote_qty = flt(etapa.lote_qty) or 1
            if lote_qty > 1:
                finished_good_uom = etapa.lote_uom or frappe.db.get_value("Item", finished_good, "stock_uom") or "Nos"
                svc_uom = LOTE_UOM
                finished_good_qty = lote_qty
            else:
                finished_good_uom = frappe.db.get_value("Item", finished_good, "stock_uom") or "Nos"
                svc_uom = frappe.db.get_value("Item", servicio, "stock_uom") or "Nos"
                finished_good_qty = 1
            # service_item_qty se escala por la participación de esta salida: si es el
            # 33% de la operación, 1 unidad física de servicio completo (1 Lote) se
            # reparte en 0.33 aquí -- así, al sumar el service_qty resultante de las
            # 3 salidas en la OC de subcontratación, da el total real de la operación,
            # no el triple (ver _create_subcontracting_pos_from_stages). El /qty_salida
            # lo deja "por unidad producida", que es la base del Subcontracting BOM:
            # una salida de 2 piezas cuesta la mitad de servicio por pieza.
            service_item_qty = (pct / qty_salida) or 1

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
                if frappe.db.has_column("Subcontracting BOM", "salida_id"):
                    subc.salida_id = node_key
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
            "qty": it.qty, "uom": it.uom, "warehouse": it.warehouse,
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


@frappe.whitelist()
def guardar_solicitud_material(mr: str, items=None, schedule_date=None) -> dict:
    """Guarda ediciones de la MR en borrador (proveedor/precio/cantidad por línea, fecha).
    El precio manual (si se captura) se respeta al generar la OC en lugar del que se
    jalaría solo de la cotización de proveedor / última compra -- ver mr_crear_oc.

    La cantidad se puede mover hasta un 5% de lo que en realidad se necesita
    (qty_original, capturada al crear la solicitud) -- de más (mermas/control de
    calidad) o de menos (ej. comprar en múltiplos/rollos cerrados) -- sin dejar que se
    dispare a lo que sea."""
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
    """Vista por LOTE de la subcontratación: agrupa, por producto, las etapas en su
    orden real (_resolve_stage_graph -- soporta procesos en paralelo que convergen)
    y correlaciona las Subcontracting Order de cada etapa (cada una en su propia OC)
    que comparten el mismo `lote_ref` -- así un lote se puede seguir de principio a
    fin (etapa 1 -> etapa 2 -> ... -> prenda terminada) en vez de tener que saltar
    entre las OC de cada etapa por separado."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

    sales_order = frappe.db.get_value("Production Plan Sales Order", {"parent": plan}, "sales_order")
    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    if not costeo:
        return {"productos": []}

    doc = frappe.get_doc("Costeo", costeo)
    productos_out = []

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

    for producto in doc.costeo_producto:
        fi = producto.finished_item
        if not fi:
            continue
        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == fi]
        if not etapas_prod:
            continue
        graph_info, etapas_ord = _resolve_stage_graph(etapas_prod, doc.get("tabla_salidas_etapa"))

        etapas_out = []
        for etapa in etapas_ord:
            node_key = etapa.get("node_key")
            es_ultima = graph_info.get(node_key, {}).get("is_terminal", True)
            bom_item = fi if es_ultima else (etapa.get("subensamblaje") or "")
            if not bom_item:
                continue
            po = _po_for_bom_item(bom_item, sales_order, costeo)
            etapas_out.append({
                "key": node_key,
                "label": etapa.get("servicio") or f"Etapa {etapa.get('etapa')}",
                "bom_item": bom_item,
                "po": po.name if po else None,
                "po_docstatus": po.docstatus if po else None,
            })

        if not etapas_out:
            continue

        po_names = [e["po"] for e in etapas_out if e["po"]]
        scos = frappe.get_all(
            "Subcontracting Order",
            filters={"purchase_order": ["in", po_names or [""]], "docstatus": ["<", 2]},
            fields=["name", "purchase_order", "lote_ref", "docstatus", "schedule_date"],
            order_by="creation asc",
        ) if po_names else []
        for s in scos:
            s["qty"] = flt(frappe.db.sql(
                "select coalesce(sum(qty), 0) from `tabSubcontracting Order Item` where parent = %s",
                s["name"],
            )[0][0])
            s["transfer_done"] = bool(frappe.db.exists("Stock Entry", {
                "subcontracting_order": s["name"], "purpose": "Send to Subcontractor", "docstatus": 1,
            }))
            scr_names = frappe.get_all(
                "Subcontracting Receipt Item", filters={"subcontracting_order": s["name"]}, pluck="parent",
            )
            s["receipt_validated"] = bool(scr_names and frappe.db.exists(
                "Subcontracting Receipt", {"name": ["in", scr_names], "docstatus": 1}
            ))

        lote_keys = list(dict.fromkeys(
            [s["lote_ref"] or "Sin lote" for s in scos]
            + list(material_pos_by_lote.keys())
            + list(materiales_por_lote.keys())
        ))
        lotes_out = []
        for lote_ref in lote_keys:
            scos_lote = [s for s in scos if (s["lote_ref"] or "Sin lote") == lote_ref]
            by_po = {s["purchase_order"]: s for s in scos_lote}
            lote_etapas = []
            for e in etapas_out:
                s = by_po.get(e["po"])
                lote_etapas.append({
                    **e,
                    "sco": s["name"] if s else None,
                    "sco_docstatus": s["docstatus"] if s else None,
                    "transfer_done": s["transfer_done"] if s else False,
                    "receipt_validated": s["receipt_validated"] if s else False,
                })
            materiales = materiales_por_lote.get(lote_ref)
            lotes_out.append({
                "lote_ref": lote_ref,
                "qty": max((s["qty"] for s in scos_lote), default=0),
                "schedule_date": scos_lote[0]["schedule_date"] if scos_lote else None,
                "etapas": lote_etapas,
                "material_pos": material_pos_by_lote.get(lote_ref, []),
                "material_mr": materiales["mr"] if materiales else None,
                "material_items": materiales["items"] if materiales else [],
                "material_rfqs": rfqs_por_lote.get(lote_ref, []),
                "material_sqs": sqs_por_lote.get(lote_ref, []),
            })

        productos_out.append({"finished_item": fi, "etapas": etapas_out, "lotes": lotes_out})

    return {"productos": productos_out}


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


@frappe.whitelist()
def sub_get_flujo(po: str) -> dict:
    """Estado del flujo de subcontratación de una OC: validada → Subcontracting Order(s)
    → transferencia de material (Stock Entry) → Subcontracting Receipt.

    Una OC puede tener VARIAS Subcontracting Order parciales (lotes escalonados en
    fechas distintas); cada una trae su propio avance de transferencia y recibo."""
    po_doc = frappe.get_doc("Purchase Order", po)
    po_item = po_doc.items[0] if po_doc.items else None
    # En PIEZAS (fg_item_qty), que es la unidad de Subcontracting Order Item.qty con la
    # que se resta abajo -- po_item.qty está en unidades de SERVICIO y en una etapa con
    # varias salidas viene repartido entre ellas (ver sub_crear_sco).
    qty_total = (flt(po_item.get("fg_item_qty")) or flt(po_item.qty)) if po_item else 0
    # ERPNext solo actualiza po_item.subcontracted_quantity al VALIDAR una SCO -- para que
    # el saldo mostrado (y el candado de "no te pases") sea correcto incluso con lotes en
    # borrador, se calcula sumando las SCO existentes (borrador + validadas), no ese campo.
    sco_names = frappe.get_all(
        "Subcontracting Order",
        filters={"purchase_order": po, "docstatus": ["<", 2]},
        pluck="name",
        order_by="creation asc",
    )
    qty_subcontratada = flt(frappe.db.sql(
        """select coalesce(sum(qty), 0) from `tabSubcontracting Order Item`
           where parent in %(scos)s""",
        {"scos": sco_names or [""]},
    )[0][0]) if sco_names else 0
    out = {
        "po_validated": po_doc.docstatus == 1,
        "supplier": po_doc.supplier,
        "qty_total": qty_total,
        "qty_subcontratada": qty_subcontratada,
        "qty_pendiente": qty_total - qty_subcontratada,
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


def _sub_qty_disponible_info(po: str) -> dict:
    """Cuántas unidades del servicio se pueden subcontratar YA, según la materia prima
    que hay en stock ahora mismo -- para sugerir (y limitar) la cantidad de un lote de
    subcontratación sin necesidad de crear la SCO a ciegas y descubrir hasta la
    transferencia que faltaba material (o, peor, tomar de una vez el 100% del saldo de
    la OC sin fijarse en el stock real). Uso interno -- ver sub_qty_disponible (misma
    info por API) y sub_crear_sco (que la usa para no dejar crear un lote más grande
    de lo que el stock real soporta).

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
    sco_draft.flags.ignore_permissions = True
    sco_draft.flags.ignore_mandatory = True
    sco_draft.insert()
    frappe.delete_doc("Subcontracting Order", sco_draft.name, force=True, ignore_permissions=True)

    # En PIEZAS (items), no en unidades de servicio (service_items): required_qty de la
    # materia prima está calculado para las piezas, así que dividir entre el servicio
    # daría un consumo por unidad inflado (x3 en una etapa de 3 salidas) y el chequeo
    # de stock rechazaría lotes que sí alcanzan.
    saldo_pendiente = sum(flt(r.qty) for r in (sco_draft.items or []))
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
def sub_qty_disponible(po: str) -> dict:
    """Ver _sub_qty_disponible_info -- expuesta tal cual por API para la sugerencia
    de cantidad que muestra el formulario de "Nuevo lote"."""
    return _sub_qty_disponible_info(po)


@frappe.whitelist()
def sub_crear_sco(po: str, qty: float = None, schedule_date: str = None, lote_ref: str = None,
                  validar_stock: bool = True) -> dict:
    """Crea una Subcontracting Order (borrador) a partir de la OC validada.

    Sin `qty`, mapea todo el saldo pendiente por subcontratar de la OC (comportamiento
    nativo). Con `qty`/`schedule_date`, crea un LOTE parcial con esa cantidad y fecha de
    entrega — se puede llamar varias veces mientras quede saldo, para escalonar la
    producción en tandas (ERPNext ya soporta varias SCO parciales contra una misma OC).
    Si la OC ya está completamente subcontratada, lanza el error nativo correspondiente.

    `lote_ref` correlaciona esta SCO con las de OTRAS etapas (otras OC) que
    pertenecen al mismo lote de producción -- ver get_lotes_produccion."""
    from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order

    # Siempre en piezas enteras -- una prenda no se subcontrata "a medias", y sin
    # esto una sugerencia o captura con decimales (p. ej. arrastrado de otro cálculo)
    # se colaba tal cual a la SCO.
    if qty:
        qty = round(flt(qty))

    if frappe.db.get_value("Purchase Order", po, "docstatus") != 1:
        frappe.throw(_("Valida la orden de compra primero."))

    existing_scos = frappe.get_all(
        "Subcontracting Order", filters={"purchase_order": po, "docstatus": ["<", 2]}, pluck="name"
    )
    if not qty and existing_scos:
        # Ya hay al menos una SCO (borrador o validada): a partir de la segunda SIEMPRE hay
        # que indicar cantidad -- si no, ERPNext podría mapear otra vez el saldo completo
        # porque subcontracted_quantity solo se actualiza al VALIDAR, no con drafts.
        frappe.throw(_("Ya existe una orden de subcontratación para esta OC. Indica la cantidad del nuevo lote."))

    # Suma lo ya comprometido en SCO existentes (borrador + validadas) -- no basta con
    # subcontracted_quantity porque ERPNext solo la actualiza al VALIDAR una SCO, y
    # aquí puede haber lotes en borrador todavía sin validar.
    # En PIEZAS del producto de la etapa (fg_item_qty), NO en unidades de servicio
    # (qty): en una etapa con varias salidas el servicio viene repartido entre ellas
    # (un corte que produce 3 piezas cobra 1/3 por cada una), así que qty vale una
    # fracción de las piezas y comparar contra ella capaba el lote a ese tercio.
    # Subcontracting Order Item.qty -- con lo que se compara abajo -- sí está en piezas.
    po_item = frappe.db.get_value(
        "Purchase Order Item", {"parent": po}, ["qty", "fg_item_qty"], as_dict=True
    ) or {}
    po_item_qty = flt(po_item.get("fg_item_qty")) or flt(po_item.get("qty"))
    comprometido = flt(frappe.db.sql(
        """select coalesce(sum(qty), 0) from `tabSubcontracting Order Item`
           where parent in %(scos)s""",
        {"scos": existing_scos or [""]},
    )[0][0]) if existing_scos else 0
    saldo_pendiente = po_item_qty - comprometido
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
        for it in sco.get("items") or []:
            it.qty = flt(qty)
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


def _etapa_row_for_po(po: str):
    """Etapa (fila de tabla_etapas_costeo) que corresponde a esta OC de
    subcontratación -- inversa de _po_for_bom_item: usa el mismo fg_item con el que
    _create_subcontracting_pos_from_stages etiquetó la línea de servicio al crearla.
    Regresa {"row": etapa, "is_root": bool} -- is_root=True si la etapa NO recibe
    material de ninguna otra (consume materia prima directa); False si depende del
    semi-terminado de otra etapa (vía 'recibe_de')."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return None
    fg_item = frappe.db.get_value("Purchase Order Item", {"parent": po}, "fg_item")
    if not fg_item:
        return None
    doc = frappe.get_doc("Costeo", costeo)
    etapas_por_producto = {}
    for row in doc.tabla_etapas_costeo:
        etapas_por_producto.setdefault(row.producto_terminado, []).append(row)
    for producto, etapas in etapas_por_producto.items():
        graph_info, ordered = _resolve_stage_graph(etapas, doc.get("tabla_salidas_etapa"))
        for node in ordered:
            node_key = node.get("node_key")
            es_ultima = graph_info.get(node_key, {}).get("is_terminal", True)
            finished_good = producto if es_ultima else (node.get("subensamblaje") or producto)
            if finished_good == fg_item:
                return {"row": node, "is_root": not graph_info.get(node_key, {}).get("upstream")}
    return None


def _stage_material_warehouses(po: str):
    """Devuelve (mp, wip, semi_terminados) para la etapa de esta OC de subcontratación.
    'semi_terminados' es el conjunto de item codes que son la SALIDA de alguna etapa de
    este mismo producto (subensamblaje o producto terminado) -- son los únicos
    materiales que de verdad llegan vía SCO/Recibo de una etapa anterior y por lo tanto
    viven en 'wip'. Cualquier OTRO material del BOM de la etapa (telas, hilos,
    botones…) es materia prima genuina comprada directo y vive en 'mp', SIN IMPORTAR
    si la etapa en sí es raíz o no -- una etapa "no raíz" (que recibe el semiterminado
    de otra) puede perfectamente seguir necesitando avíos propios (ej. botones que se
    cosen hasta la etapa de Confección, no antes)."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return None, None, set()
    mp, wip = frappe.db.get_value("Costeo", costeo, ["almacen_materias_primas", "almacen_trabajo_en_proceso"]) or (None, None)
    etapa_info = _etapa_row_for_po(po)
    semi_terminados = set()
    if etapa_info is not None:
        producto = etapa_info["row"].producto_terminado
        doc = frappe.get_doc("Costeo", costeo)
        etapas_prod = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == producto]
        graph_info, ordered = _resolve_stage_graph(etapas_prod, doc.get("tabla_salidas_etapa"))
        for node in ordered:
            node_key = node.get("node_key")
            es_ultima = graph_info.get(node_key, {}).get("is_terminal", True)
            bom_item = producto if es_ultima else (node.get("subensamblaje") or producto)
            if bom_item:
                semi_terminados.add(bom_item)
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
    clasificada como "depende de otra etapa" sólo por haberse creado después."""
    if not po:
        return None
    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return None
    mp, wip = frappe.db.get_value("Costeo", costeo, ["almacen_materias_primas", "almacen_trabajo_en_proceso"]) or (None, None)
    etapa_info = _etapa_row_for_po(po)
    if etapa_info is not None:
        return (mp if etapa_info["is_root"] else wip) or mp or wip
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


@frappe.whitelist()
def sub_transferir_material(sco: str) -> dict:
    """Crea el Stock Entry 'Send to Subcontractor' EN BORRADOR (igual que el botón nativo
    'Transferencia → Materiales al proveedor' de ERPNext). No lo valida: el usuario revisa
    almacenes y cantidades y lo valida aparte (así no fuerza stock negativo).
    El almacén de origen se pre-llena según la etapa (materia prima / trabajo en proceso)."""
    from erpnext.controllers.subcontracting_controller import make_rm_stock_entry

    doc = frappe.get_doc("Subcontracting Order", sco)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la orden de subcontratación primero."))

    # Reutiliza un borrador existente si ya se generó uno -- de paso, sanea sus
    # cantidades por si quedó de antes de que esto redondeara hacia arriba (o si el
    # required_qty de la SCO que lo originó todavía traía decimales).
    existing = frappe.db.get_value(
        "Stock Entry",
        {"subcontracting_order": sco, "purpose": "Send to Subcontractor", "docstatus": 0},
        "name",
    )
    if existing:
        _redondear_qty_arriba(frappe.get_doc("Stock Entry", existing))
        return {"ok": True, "stock_entry": existing, "docstatus": 0}

    se = make_rm_stock_entry(sco, order_doctype="Subcontracting Order")
    se = frappe.get_doc(se) if isinstance(se, dict) else se
    po = frappe.db.get_value("Subcontracting Order", sco, "purchase_order")
    _aplicar_almacenes_origen_por_material(se, po)
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


@frappe.whitelist()
def lote_abrir(plan: str, lote_ref: str, qty: float, schedule_date: str = None,
               producto: str = None) -> dict:
    """Abre un lote de producción de un jalón: crea y valida la orden de
    subcontratación de TODAS las etapas del producto, con la misma cantidad y
    referencia de lote.

    Es el compromiso completo del lote -- lo que se le encarga a cada taller -- y se
    decide una sola vez (cantidad + fecha), así que no tiene sentido volver a
    capturarlo etapa por etapa. Antes esto eran 2 acciones por etapa (crear + validar);
    con 10 etapas, 20 pasos que no aportaban ningún dato nuevo.

    NO exige materia prima en stock (validar_stock=False): las etapas 2+ reciben su
    insumo de la etapa anterior, que todavía no ha producido nada. El candado de
    existencias vive en la TRANSFERENCIA, donde sí corresponde -- ahí ERPNext bloquea
    solo si el almacén se iría a negativo.

    Las etapas que ya tengan SCO de este lote se saltan, así que es seguro volver a
    llamarlo (por ejemplo si una etapa falló y se corrigió el dato)."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_stage_graph

    qty = flt(qty)
    if qty <= 0:
        frappe.throw(_("Indica la cantidad del lote."))
    if not lote_ref:
        frappe.throw(_("Indica la referencia del lote."))

    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    if not costeo:
        frappe.throw(_("El plan no está ligado a ningún costeo."))
    doc = frappe.get_doc("Costeo", costeo)

    productos = [producto] if producto else [p.finished_item for p in doc.costeo_producto if p.finished_item]
    creadas, saltadas, errores = [], [], []

    for prod in productos:
        etapas = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == prod]
        if not etapas:
            continue
        info, ordenadas = _resolve_stage_graph(etapas, doc.get("tabla_salidas_etapa"))
        for nodo in ordenadas:
            es_ultima = info[nodo["node_key"]]["is_terminal"]
            fg = prod if es_ultima else (nodo.get("subensamblaje") or "")
            if not fg:
                continue
            # La OC de maquila de esta etapa: se identifica por el fg_item con el que
            # _create_subcontracting_pos_from_stages etiquetó su línea de servicio.
            po = frappe.db.get_value(
                "Purchase Order Item",
                {"fg_item": fg, "docstatus": 1},
                "parent",
            )
            if not po or frappe.db.get_value("Purchase Order", po, "costeo") != costeo:
                errores.append(_("{0}: su orden de compra de maquila no está validada.").format(fg))
                continue
            if frappe.db.exists("Subcontracting Order",
                                {"purchase_order": po, "lote_ref": lote_ref, "docstatus": ["<", 2]}):
                saltadas.append(fg)
                continue
            try:
                r = sub_crear_sco(po, qty=qty, schedule_date=schedule_date, lote_ref=lote_ref,
                                  validar_stock=False)
                sub_validar_sco(r["sco"])
                creadas.append({"etapa": fg, "sco": r["sco"]})
            except Exception as exc:
                errores.append(f"{fg}: {exc}")

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
        "items": items,
    }


@frappe.whitelist()
def guardar_documento_compra(doctype: str, name: str, schedule_date=None, valid_till=None,
                             transaction_date=None, posting_date=None, payment_terms_template=None,
                             tc_name=None, items=None, shipping_cost=None) -> dict:
    """Guarda ediciones de un documento de compra en borrador."""
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
