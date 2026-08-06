import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from costeo_yelke.api import item_api


@frappe.whitelist()
def get_costeo_list(limit: int = 50) -> list:
    """Lista de costeos con campos para el pipeline."""
    return frappe.get_list(
        "Costeo",
        fields=["name", "cliente", "fecha", "compañia", "costeo_status", "modified"],
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

    def find_warehouse(candidates):
        for name in candidates:
            wh = frappe.db.get_value(
                "Warehouse",
                {"company": company, "warehouse_name": name, "is_group": 0, "disabled": 0},
                "name",
            )
            if wh:
                return wh
        return ""

    return {
        "centro_de_costos": frappe.db.get_value("Company", company, "cost_center") or "",
        "almacen_materias_primas": find_warehouse(["Materia Prima", "Stores"]),
        "almacen_trabajo_en_proceso": find_warehouse(["Trabajo en Proceso", "Work In Progress"]),
    }


@frappe.whitelist()
def set_costeo_status(costeo: str, status: str) -> dict:
    """Actualiza el estatus del pipeline."""
    allowed = {"Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado", "Cancelado"}
    if status not in allowed:
        frappe.throw(_(f"Estatus inválido: {status}"))
    frappe.db.set_value("Costeo", costeo, "costeo_status", status)
    return {"ok": True, "costeo": costeo, "status": status}


@frappe.whitelist()
def crear_cotizacion(costeo: str, valid_till=None, payment_terms_template=None, tc_name=None, custom_tipo_formato=None) -> dict:
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
    if frappe.db.has_column("Quotation", "custom_tipo_formato"):
        quot.custom_tipo_formato = custom_tipo_formato or "Normal"

    if frappe.db.has_column("Quotation", "costeo"):
        quot.costeo = costeo

    tax_template = _get_sales_tax_template(doc.compañia)
    if tax_template:
        quot.taxes_and_charges = tax_template

    for p in doc.costeo_producto:
        quot.append("items", {
            "item_code": p.finished_item,
            "qty": p.qty,
            "rate": p.unit_sales_price or 0,
        })

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

    company = frappe.db.get_value("Costeo", costeo, "compañia")
    price_list = frappe.db.get_default("selling_price_list") or "Venta estándar"

    if not frappe.db.exists("Item", item_code):
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
            "item_defaults": [{"company": company, "default_price_list": price_list}],
        }
        if description:
            payload["description"] = description
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

    frappe.db.commit()
    return {"item_code": item_code}


@frappe.whitelist()
def actualizar_cotizacion(name: str, valid_till=None, payment_terms_template=None, tc_name=None, custom_tipo_formato=None) -> dict:
    """Actualiza los datos manuales de una cotización en borrador."""
    doc = frappe.get_doc("Quotation", name)
    if doc.docstatus != 0:
        frappe.throw(_("La cotización ya está validada; no se puede editar."))
    doc.valid_till = valid_till or None
    doc.payment_terms_template = payment_terms_template or None
    doc.tc_name = tc_name or None
    if frappe.db.has_column("Quotation", "custom_tipo_formato"):
        doc.custom_tipo_formato = custom_tipo_formato or "Normal"
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

    # Las etapas se procesan por producto y ORDENADAS igual que crear_boms_spa /
    # crear_subcontracting_bom (misma _stage_sort_key_int) -- en la ÚLTIMA etapa
    # de cada producto, esas dos funciones usan finished_item como resultado, NO
    # el texto que haya en "subensamblaje" de esa fila (ese campo se ignora ahí).
    # Si no replicamos el mismo criterio de "última etapa" aquí, el checklist le
    # pide al usuario materializar como "Sub-Ensamblaje" un texto que en realidad
    # es simplemente el producto terminado -- exactamente el caso de una sola
    # etapa (un solo proveedor hace todo) donde no existe un intermedio real.
    advertencias = []
    for producto in doc.costeo_producto:
        fi = producto.finished_item
        if not fi:
            continue
        etapas_prod = sorted(
            [e for e in doc.tabla_etapas_costeo if e.producto_terminado == fi],
            key=_stage_sort_key_int,
        )
        n = len(etapas_prod)
        for i, e in enumerate(etapas_prod):
            es_ultima = (i == n - 1)
            add("servicio_etapa", e.servicio, "Servicios", e.proveedor, e.producto_terminado, unit_price=e.precio_servicio)
            if not es_ultima:
                add("subensamblaje_etapa", e.subensamblaje, "Sub-Ensamblajes", None, e.producto_terminado)
            elif e.subensamblaje and e.subensamblaje != fi:
                advertencias.append(
                    f'En la última etapa de "{fi}", el sub-ensamblaje capturado ("{e.subensamblaje}") '
                    f"se ignora — el resultado de la última etapa siempre es el producto terminado."
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

    frappe.db.commit()
    return {"item_code": item_code}


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
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def get_default_print_format(doctype: str) -> dict:
    """Formato de impresión PREDETERMINADO configurado para el doctype (o 'Standard')."""
    fmt = frappe.get_meta(doctype).default_print_format
    return {"format": fmt or "Standard"}


@frappe.whitelist()
def cancelar_documento(doctype: str, name: str) -> dict:
    """Cancela un documento validado (docstatus 1 -> 2). Paso previo para poder eliminarlo."""
    doc = frappe.get_doc(doctype, name)
    if doc.docstatus == 1:
        doc.flags.ignore_permissions = True
        doc.cancel()
    return {"name": doc.name, "docstatus": doc.docstatus}


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
    """Opciones para los campos manuales de la cotización."""
    payment_terms = frappe.get_all("Payment Terms Template", fields=["name"], order_by="name asc")
    terms = frappe.get_all("Terms and Conditions", fields=["name"], order_by="name asc")
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit=50,
    )
    return {"payment_terms_templates": payment_terms, "terms": terms, "users": users}


@frappe.whitelist()
def crear_orden_venta(costeo: str, delivery_date=None, payment_terms_template=None, tc_name=None) -> dict:
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

    if frappe.db.has_column("Sales Order", "costeo"):
        so.costeo = costeo

    tax_template = _get_sales_tax_template(doc.compañia)
    if tax_template:
        so.taxes_and_charges = tax_template

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
def actualizar_orden_venta(name: str, delivery_date=None, payment_terms_template=None, tc_name=None) -> dict:
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
    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def produccion_completa(costeo: str) -> dict:
    """True si TODAS las OC de subcontratación del costeo ya tienen su Subcontracting Receipt
    validado (producto terminado recibido). Desbloquea la facturación solo al terminar todo."""
    out = {"complete": False, "total": 0, "recibidas": 0}
    if not frappe.db.has_column("Purchase Order", "costeo"):
        return out
    sub_pos = frappe.get_all(
        "Purchase Order",
        filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": ["<", 2]},
        fields=["name", "docstatus"],
    )
    out["total"] = len(sub_pos)
    if not sub_pos:
        return out
    recibidas = 0
    for po in sub_pos:
        if po.docstatus != 1:
            continue  # OC de subcontratación sin validar → esa etapa no está lista
        sco = frappe.db.get_value("Subcontracting Order", {"purchase_order": po.name, "docstatus": 1}, "name")
        if not sco:
            continue
        scr = frappe.db.get_value(
            "Subcontracting Receipt Item", {"subcontracting_order": sco, "docstatus": 1}, "parent"
        )
        if scr:
            recibidas += 1
    out["recibidas"] = recibidas
    out["complete"] = out["total"] > 0 and recibidas == out["total"]
    return out


@frappe.whitelist()
def crear_factura_venta(costeo: str, posting_date=None, payment_terms_template=None, tc_name=None, due_date=None) -> dict:
    """Crea una Factura de Venta (Sales Invoice) en BORRADOR desde la Orden de Venta del costeo."""
    so_name = None
    if frappe.db.has_column("Sales Order", "costeo"):
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
def crear_remision(costeo: str, posting_date=None) -> dict:
    """Crea la Nota de Remisión (Delivery Note) en BORRADOR desde la Orden de Venta
    validada del costeo. Pre-llena el almacén de cada línea con dónde está el stock real."""
    so_name = None
    if frappe.db.has_column("Sales Order", "costeo"):
        so_name = frappe.db.get_value("Sales Order", {"costeo": costeo, "docstatus": 1}, "name")
    if not so_name:
        frappe.throw(_("No hay una orden de venta validada para remisionar."))

    existing = frappe.db.get_value(
        "Delivery Note Item", {"against_sales_order": so_name, "docstatus": ["<", 2]}, "parent"
    )
    if existing:
        return {"name": existing}

    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
    dn = make_delivery_note(so_name)
    if posting_date:
        dn.set_posting_time = 1
        dn.posting_date = posting_date
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
def actualizar_remision(name: str, posting_date=None, items=None, shipping_address_name=None, customer_address=None) -> dict:
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


@frappe.whitelist()
def validar_remision(name: str) -> dict:
    """Valida (submit) la remisión: libera el producto terminado del inventario, genera
    el costo de venta real, y marca el costeo como 'Entregado' -- desbloquea Facturar."""
    doc = frappe.get_doc("Delivery Note", name)
    doc.flags.ignore_permissions = True
    doc.submit()
    costeo = doc.get("costeo")
    if costeo and frappe.db.exists("Costeo", costeo):
        frappe.db.set_value("Costeo", costeo, "costeo_status", "Entregado")
    return {"name": doc.name, "docstatus": doc.docstatus}


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

    # ── 2. Agrupar materias primas por producto + etapa ──────────────────────
    mats_por_producto_etapa: dict = {}
    for d in doc.costeo_producto_detalle:
        if d.finished_item and d.concept_type == "Materia Prima" and d.item:
            key = (d.finished_item, str(d.etapa or ""))
            mats_por_producto_etapa.setdefault(key, []).append(d)

    # ── 3. Procesar cada producto ─────────────────────────────────────────────
    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        if not finished_item or float(producto.qty or 0) <= 0:
            continue

        etapas = etapas_por_producto.get(finished_item, [])
        if not etapas:
            errors.append(f"{finished_item}: sin etapas configuradas")
            continue

        etapas_ord = sorted(etapas, key=_stage_sort_key_int)

        for index, etapa_cfg in enumerate(etapas_ord):
            es_ultima       = (index == len(etapas_ord) - 1)
            etapa_num_str   = str(etapa_cfg.etapa or "")
            subensamblaje   = etapa_cfg.subensamblaje or ""

            # Ítem para el que se crea el BOM
            bom_item = finished_item if es_ultima else subensamblaje
            if not bom_item:
                continue

            # ── Ítems del BOM ────────────────────────────────────────────────
            items_bom = []

            # Sub-ensamblaje de la etapa anterior (si no es la primera)
            if index > 0:
                prev_sub = etapas_ord[index - 1].subensamblaje or ""
                if prev_sub:
                    prev_uom = frappe.db.get_value("Item", prev_sub, "stock_uom") or "Nos"
                    # Referencia explícita al BOM del subensamblaje anterior, para que la
                    # explosión multinivel del Production Plan recurra correctamente.
                    prev_bom = frappe.db.get_value(
                        "BOM", {"item": prev_sub, "is_active": 1, "docstatus": ["in", [0, 1]]}, "name"
                    ) or ""
                    items_bom.append({
                        "item_code": prev_sub,
                        "qty":       1,
                        "uom":       prev_uom,
                        "stock_uom": prev_uom,
                        "rate":      0,
                        "bom_no":    prev_bom,
                    })

            # Materias primas de esta etapa. Las materias primas SIN etapa asignada
            # se incluyen en la PRIMERA etapa (es donde entran a producción).
            stage_mats = list(mats_por_producto_etapa.get((finished_item, etapa_num_str), []))
            if index == 0 and etapa_num_str != "":
                stage_mats += mats_por_producto_etapa.get((finished_item, ""), [])

            for mat in stage_mats:
                uom = (mat.internal_uom
                       or frappe.db.get_value("Item", mat.item, "stock_uom")
                       or "Nos")
                qty = float(mat.internal_qty or mat.supplier_qty or 1)
                items_bom.append({
                    "item_code": mat.item,
                    "qty":       qty,
                    "uom":       uom,
                    "stock_uom": uom,
                    "rate":      0,
                })

            if not items_bom:
                continue

            # ── Verificar si ya existe BOM ───────────────────────────────────
            existing = frappe.db.get_value(
                "BOM",
                {"item": bom_item, "docstatus": ["in", [0, 1]]},
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
            "BOM",
            {"item": finished_item, "is_active": 1, "docstatus": 1},
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
    doc     = frappe.get_doc("Costeo", costeo)
    created, errors, skipped = [], [], []

    for producto in doc.costeo_producto:
        finished_item = producto.finished_item
        if not finished_item:
            continue

        # Stages for this product, sorted numerically
        etapas = sorted(
            [e for e in doc.tabla_etapas_costeo if e.producto_terminado == finished_item],
            key=_stage_sort_key_int,
        )
        if not etapas:
            continue

        n = len(etapas)
        for i, etapa in enumerate(etapas):
            servicio      = etapa.servicio
            subensamblaje = etapa.subensamblaje
            es_ultima     = (i == n - 1)
            finished_good = finished_item if es_ultima else subensamblaje

            if not finished_good or not servicio:
                continue

            # Skip if Subcontracting BOM already exists for this finished_good
            existing = frappe.db.get_value(
                "Subcontracting BOM",
                {"finished_good": finished_good},
                "name",
            )
            if existing:
                skipped.append(f"{finished_good} (ya existe: {existing})")
                continue

            # Require a submitted BOM for the finished_good
            bom_name = frappe.db.get_value(
                "BOM",
                {"item": finished_good, "is_active": 1, "is_default": 1, "docstatus": 1},
                "name",
            )
            if not bom_name:
                errors.append(
                    f"{finished_good}: no existe BOM activo y enviado. "
                    "Crea los BOMs normales primero."
                )
                continue

            finished_good_uom = frappe.db.get_value("Item", finished_good, "stock_uom") or "Nos"
            svc_uom           = frappe.db.get_value("Item", servicio, "stock_uom") or "Nos"

            try:
                subc = frappe.new_doc("Subcontracting BOM")
                subc.finished_good     = finished_good
                subc.finished_good_qty = 1
                subc.finished_good_uom = finished_good_uom
                subc.finished_good_bom = bom_name
                subc.is_active         = 1
                subc.service_item      = servicio
                subc.service_item_qty  = 1
                subc.service_item_uom  = svc_uom
                subc.conversion_factor = 1
                subc.flags.ignore_permissions = True
                subc.flags.ignore_links       = True
                subc.flags.ignore_mandatory   = True
                subc.insert()
                subc.submit()
                created.append(subc.name)
            except Exception as exc:
                errors.append(f"{finished_good} / {servicio}: {exc}")

    frappe.db.commit()
    return {"created": created, "errors": errors, "skipped": skipped}


@frappe.whitelist()
def desbloquear_plan_produccion(costeo: str) -> dict:
    """Crea un Production Plan LIGADO a la Orden de Venta del Costeo.

    Si existe una OV validada ligada al costeo, el plan se construye DESDE esa OV
    (get_items_from='Sales Order' + get_items()), de modo que los po_items arrastren
    sales_order / sales_order_item y se conserve la trazabilidad OV -> plan -> MR/WO.
    Si no hay OV, cae a construir los po_items directamente del costeo.
    """
    doc     = frappe.get_doc("Costeo", costeo)
    company = doc.compañia

    so_name = None
    if frappe.db.has_column("Sales Order", "costeo"):
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
                        "BOM", {"item": row.item_code, "is_active": 1, "docstatus": 1}, "name"
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
            or frappe.db.get_value("BOM", {"item": finished_item, "is_active": 1, "docstatus": 1}, "name")
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


# ── Documentos ligados y envío ────────────────────────────────────────────────

@frappe.whitelist()
def get_costeo_related(costeo: str) -> dict:
    """Documentos generados a partir del Costeo (cotización, orden de venta, remisión, factura)."""
    out = {"quotation": None, "sales_order": None, "delivery_note": None, "sales_invoice": None}

    if frappe.db.has_column("Quotation", "costeo"):
        rows = frappe.get_all(
            "Quotation",
            filters={"costeo": costeo},
            fields=["name", "status", "docstatus", "grand_total", "currency", "contact_email",
                    "valid_till", "payment_terms_template", "tc_name", "custom_tipo_formato"],
            order_by="creation desc",
            limit=1,
        )
        if rows:
            out["quotation"] = rows[0]

    if frappe.db.has_column("Sales Order", "costeo"):
        rows = frappe.get_all(
            "Sales Order",
            filters={"costeo": costeo},
            fields=["name", "status", "docstatus", "grand_total", "currency",
                    "delivery_date", "payment_terms_template", "tc_name", "contact_email"],
            order_by="creation desc",
            limit=1,
        )
        if rows:
            out["sales_order"] = rows[0]

    # Nota de remisión ligada a la OV (vía Delivery Note Item.against_sales_order)
    if out["sales_order"]:
        dn_parent = frappe.db.get_value(
            "Delivery Note Item",
            {"against_sales_order": out["sales_order"]["name"], "docstatus": ["<", 2]},
            "parent",
        )
        if dn_parent:
            out["delivery_note"] = frappe.db.get_value(
                "Delivery Note", dn_parent,
                ["name", "status", "docstatus", "posting_date", "grand_total"],
                as_dict=True,
            )

    # Factura de venta ligada a la OV (vía Sales Invoice Item.sales_order)
    if out["sales_order"]:
        si_parent = frappe.db.get_value(
            "Sales Invoice Item",
            {"sales_order": out["sales_order"]["name"], "docstatus": ["<", 2]},
            "parent",
        )
        if si_parent:
            out["sales_invoice"] = frappe.db.get_value(
                "Sales Invoice", si_parent,
                ["name", "status", "docstatus", "grand_total", "currency", "posting_date",
                 "due_date", "payment_terms_template", "tc_name", "contact_email"],
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


@frappe.whitelist()
def preparar_produccion(costeo: str) -> dict:
    """Ejecuta toda la preparación de producción en un paso (idempotente):
    BOMs → Subcontracting BOMs → Plan → Solicitud de material → OC de subcontratación → Work Orders."""
    existing = get_produccion_docs(costeo)
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
    run("Plan de producción", lambda: desbloquear_plan_produccion(costeo), skip=bool(existing.get("plan")))

    frappe.db.set_value("Costeo", costeo, "costeo_status", "En Producción")
    return {"steps": steps}


@frappe.whitelist()
def get_produccion_docs(costeo: str) -> dict:
    """Documentos de producción ligados al costeo, agrupados para el panel."""
    def q(dt, fields):
        if not frappe.db.has_column(dt, "costeo"):
            return []
        return frappe.get_all(dt, filters={"costeo": costeo}, fields=fields, order_by="creation desc")

    plan = q("Production Plan", ["name", "status", "docstatus"])
    mrs = q("Material Request", ["name", "status", "docstatus", "material_request_type"])
    pos = q("Purchase Order", ["name", "status", "docstatus", "supplier", "supplier_name",
                               "grand_total", "currency", "is_subcontracted", "per_received"])
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
def get_plan_detail(costeo: str) -> dict:
    """Detalle del Production Plan ligado al costeo, para el panel Producir."""
    plan_name = None
    if frappe.db.has_column("Production Plan", "costeo"):
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
        "po_items": [{"item_code": r.item_code, "planned_qty": r.planned_qty, "bom_no": r.bom_no,
                      "sales_order": r.sales_order} for r in pp.get("po_items") or []],
        "sub_assembly_items": [{"production_item": r.production_item, "qty": r.qty,
                                "type_of_manufacturing": r.type_of_manufacturing, "supplier": r.supplier}
                               for r in pp.get("sub_assembly_items") or []],
        "mr_items": [{"item_code": r.item_code, "quantity": r.quantity, "warehouse": r.warehouse, "uom": r.uom}
                     for r in pp.get("mr_items") or []],
    }}


@frappe.whitelist()
def guardar_plan(plan: str, for_warehouse: str = None) -> dict:
    pp = frappe.get_doc("Production Plan", plan)
    if pp.docstatus != 0:
        frappe.throw(_("El plan ya está validado."))
    if for_warehouse:
        pp.for_warehouse = for_warehouse
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
    _asignar_proveedores_a_mrs(pp.get("costeo"), mrs)
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
        } for it in primary.items],
    }
    detail["linked_ocs"] = list(dict.fromkeys(
        frappe.get_all("Purchase Order Item", filters={"material_request": primary.name}, pluck="parent")
    ))
    return {"material_requests": mrs, "detail": detail}


@frappe.whitelist()
def guardar_solicitud_material(mr: str, items=None, schedule_date=None) -> dict:
    """Guarda ediciones de la MR en borrador (proveedor/cantidad por línea, fecha)."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 0:
        frappe.throw(_("La solicitud ya está validada; no se puede editar."))
    if schedule_date:
        doc.schedule_date = schedule_date
    if items:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows if r.get("name")}
        has_sup = frappe.db.has_column("Material Request Item", "supplier")
        for it in doc.items:
            r = by_name.get(it.name)
            if not r:
                continue
            if r.get("qty") is not None:
                it.qty = flt(r.get("qty"))
            if has_sup:
                it.supplier = r.get("supplier") or None
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


@frappe.whitelist()
def mr_crear_oc(mr: str) -> dict:
    """Crea Orden(es) de Compra desde la MR (una OC por proveedor) y jala el precio:
    del Presupuesto de Proveedor si existe, si no de la lista de precios (última compra)."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))
    from costeo_yelke.overrides.material_request import make_purchase_order

    result = make_purchase_order(mr)
    pos = list(dict.fromkeys(
        frappe.get_all("Purchase Order Item", filters={"material_request": mr}, pluck="parent")
    ))
    if not pos and result is not None:
        try:
            result.flags.ignore_permissions = True
            result.insert()
            pos = [result.name]
        except Exception:
            pass

    _aplicar_precios_oc(pos)

    # ligar las OC al costeo (trazabilidad)
    plan = frappe.db.get_value("Material Request Item", {"parent": mr}, "production_plan")
    costeo = frappe.db.get_value("Production Plan", plan, "costeo") if plan else None
    if costeo and frappe.db.has_column("Purchase Order", "costeo"):
        for po in pos:
            frappe.db.set_value("Purchase Order", po, "costeo", costeo, update_modified=False)
    frappe.db.commit()
    return {"ok": True, "purchase_orders": pos}


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
    """OC validadas (materia prima) ligadas al plan + sus recibos de compra."""
    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    ocs = []
    if costeo and frappe.db.has_column("Purchase Order", "costeo"):
        rows = frappe.get_all(
            "Purchase Order",
            filters={"costeo": costeo, "is_subcontracted": 0, "docstatus": 1},
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
    de materias primas del costeo y asegurando los impuestos de compra (IVA)."""
    po_doc = frappe.get_doc("Purchase Order", po)
    if po_doc.docstatus != 1:
        frappe.throw(_("Valida la orden de compra primero."))

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


@frappe.whitelist()
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


@frappe.whitelist()
def guardar_om(po: str, general=None, tallas_caballero=None, tallas_dama=None, procesos=None, tablas=None, archivos=None) -> dict:
    """Guarda la Orden de Manufactura en la OC subcontratada (en borrador)."""
    doc = frappe.get_doc("Purchase Order", po)
    if doc.docstatus != 0:
        frappe.throw(_("La orden ya está validada; no se puede editar."))

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
    return {"ok": True}


@frappe.whitelist()
def get_subcontratos(plan: str) -> dict:
    """OC de subcontratación (maquila) ligadas al plan/costeo."""
    costeo = frappe.db.get_value("Production Plan", plan, "costeo")
    pos = []
    if costeo and frappe.db.has_column("Purchase Order", "costeo"):
        pos = frappe.get_all(
            "Purchase Order",
            filters={"costeo": costeo, "is_subcontracted": 1},
            fields=["name", "supplier", "supplier_name", "docstatus", "status", "grand_total", "per_received"],
            order_by="creation asc",
        )
    return {"ocs": pos}


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
    """Estado del flujo de subcontratación de una OC: validada → Subcontracting Order
    → transferencia de material (Stock Entry) → Subcontracting Receipt."""
    po_doc = frappe.get_doc("Purchase Order", po)
    out = {
        "po_validated": po_doc.docstatus == 1,
        "supplier": po_doc.supplier,
        "sco": None,
        "transfer": {"done": False, "entries": []},
        "receipts": [],
        "warehouses": frappe.get_all(
            "Warehouse",
            filters={"company": po_doc.company, "is_group": 0, "disabled": 0},
            fields=["name", "warehouse_name"],
            order_by="name asc",
        ),
        "address_options": _party_links("Address", po_doc.supplier),
        "contact_options": _party_links("Contact", po_doc.supplier),
    }

    sco_name = frappe.db.get_value("Subcontracting Order", {"purchase_order": po, "docstatus": ["<", 2]}, "name")
    if sco_name:
        sco = frappe.get_doc("Subcontracting Order", sco_name)
        out["sco"] = {
            "name": sco.name,
            "docstatus": sco.docstatus,
            "status": sco.status,
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
        }

        ses = frappe.get_all(
            "Stock Entry",
            filters={"subcontracting_order": sco.name, "purpose": "Send to Subcontractor"},
            fields=["name", "docstatus"],
            order_by="creation asc",
        )
        out["transfer"]["entries"] = ses
        out["transfer"]["done"] = any(s.docstatus == 1 for s in ses)

        scr_parents = list(dict.fromkeys(frappe.get_all(
            "Subcontracting Receipt Item",
            filters={"subcontracting_order": sco.name, "docstatus": ["<", 2]},
            pluck="parent",
        )))
        out["receipts"] = [
            dict(zip(("name", "docstatus", "status"),
                     frappe.db.get_value("Subcontracting Receipt", p, ["name", "docstatus", "status"])))
            for p in scr_parents
        ]
    return out


@frappe.whitelist()
def sub_crear_sco(po: str) -> dict:
    """Crea la Subcontracting Order (borrador) a partir de la OC validada."""
    from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order

    if frappe.db.get_value("Purchase Order", po, "docstatus") != 1:
        frappe.throw(_("Valida la orden de compra primero."))
    existing = frappe.db.get_value("Subcontracting Order", {"purchase_order": po, "docstatus": ["<", 2]}, "name")
    if existing:
        return {"ok": True, "sco": existing}

    sco = make_subcontracting_order(po)
    sco.flags.ignore_permissions = True
    sco.flags.ignore_mandatory = True
    sco.insert()
    return {"ok": True, "sco": sco.name}


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

    if costos is not None:
        rows = json.loads(costos) if isinstance(costos, str) else costos
        doc.set("additional_costs", [])
        default_acc = frappe.get_cached_value("Company", doc.company, "default_expense_account")
        for r in rows:
            amount = flt(r.get("amount"))
            if not (r.get("description") and amount):
                continue
            doc.append("additional_costs", {
                "expense_account": r.get("expense_account") or default_acc,
                "description": r.get("description"),
                "amount": amount,
            })

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


def _stage_source_warehouse(sco_name: str):
    """Almacén de origen recomendado para la transferencia, según la etapa:
    la PRIMERA etapa de subcontratación consume del almacén de materia prima;
    las siguientes (subensamblaje) consumen del almacén de trabajo en proceso."""
    po = frappe.db.get_value("Subcontracting Order", sco_name, "purchase_order")
    if not po:
        return None
    costeo = frappe.db.get_value("Purchase Order", po, "costeo")
    if not costeo:
        return None
    mp, wip = frappe.db.get_value("Costeo", costeo, ["almacen_materias_primas", "almacen_trabajo_en_proceso"]) or (None, None)
    sub_pos = frappe.get_all(
        "Purchase Order",
        filters={"costeo": costeo, "is_subcontracted": 1},
        order_by="creation asc",
        pluck="name",
    )
    is_first = bool(sub_pos) and sub_pos[0] == po
    return (mp if is_first else wip) or mp or wip


def _aplicar_almacen_origen(se, warehouse):
    """Fija el almacén de origen en la cabecera y en todas las líneas del Stock Entry."""
    if not warehouse:
        return
    se.from_warehouse = warehouse
    for it in se.items:
        it.s_warehouse = warehouse


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

    # Reutiliza un borrador existente si ya se generó uno
    existing = frappe.db.get_value(
        "Stock Entry",
        {"subcontracting_order": sco, "purpose": "Send to Subcontractor", "docstatus": 0},
        "name",
    )
    if existing:
        return {"ok": True, "stock_entry": existing, "docstatus": 0}

    se = make_rm_stock_entry(sco, order_doctype="Subcontracting Order")
    se = frappe.get_doc(se) if isinstance(se, dict) else se
    _aplicar_almacen_origen(se, _stage_source_warehouse(sco))
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
    }


@frappe.whitelist()
def sub_guardar_transferencia(stock_entry: str, from_warehouse=None, to_warehouse=None, items=None) -> dict:
    """Guarda almacenes de origen/destino y cantidades del Stock Entry en borrador."""
    doc = frappe.get_doc("Stock Entry", stock_entry)
    if doc.docstatus != 0:
        frappe.throw(_("La transferencia ya está validada."))

    if from_warehouse:
        doc.from_warehouse = from_warehouse
        for it in doc.items:
            it.s_warehouse = from_warehouse
    if to_warehouse:
        doc.to_warehouse = to_warehouse
        for it in doc.items:
            it.t_warehouse = to_warehouse

    if items is not None:
        rows = json.loads(items) if isinstance(items, str) else items
        by_name = {r.get("name"): r for r in rows}
        for it in doc.items:
            r = by_name.get(it.name)
            if not r:
                continue
            if r.get("qty") is not None:
                it.qty = flt(r.get("qty"))
            if r.get("s_warehouse"):
                it.s_warehouse = r.get("s_warehouse")
            if r.get("t_warehouse"):
                it.t_warehouse = r.get("t_warehouse")

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
    }


@frappe.whitelist()
def sub_guardar_recibo(scr: str, set_warehouse=None, rejected_warehouse=None, supplier_warehouse=None, items=None) -> dict:
    """Guarda los almacenes y cantidades del Subcontracting Receipt en borrador."""
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

    doc.flags.ignore_permissions = True
    doc.save()
    return {"ok": True}


@frappe.whitelist()
def mr_crear_rfq(mr: str) -> dict:
    """Crea una Solicitud de Cotización (RFQ) desde la MR, con los proveedores de las líneas."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))
    from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

    rfq = make_request_for_quotation(mr)
    if frappe.db.has_column("Material Request Item", "supplier"):
        sups = list(dict.fromkeys(
            frappe.get_all("Material Request Item", filters={"parent": mr, "supplier": ["is", "set"]}, pluck="supplier")
        ))
        for s in sups:
            rfq.append("suppliers", {"supplier": s})
    rfq.flags.ignore_permissions = True
    rfq.flags.ignore_mandatory = True
    rfq.insert()
    return {"ok": True, "rfq": rfq.name}


@frappe.whitelist()
def mr_crear_presupuesto_proveedor(mr: str) -> dict:
    """Crea un Presupuesto de Proveedor (Supplier Quotation) desde la MR."""
    doc = frappe.get_doc("Material Request", mr)
    if doc.docstatus != 1:
        frappe.throw(_("Valida la solicitud primero."))
    from erpnext.stock.doctype.material_request.material_request import make_supplier_quotation

    sq = make_supplier_quotation(mr)
    if not sq.get("supplier") and frappe.db.has_column("Material Request Item", "supplier"):
        first_sup = frappe.db.get_value("Material Request Item", {"parent": mr, "supplier": ["is", "set"]}, "supplier")
        if first_sup:
            sq.supplier = first_sup
    sq.flags.ignore_permissions = True
    sq.flags.ignore_mandatory = True
    sq.insert()
    return {"ok": True, "supplier_quotation": sq.name}


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
        "items": items,
    }


@frappe.whitelist()
def guardar_documento_compra(doctype: str, name: str, schedule_date=None, valid_till=None,
                             transaction_date=None, posting_date=None, payment_terms_template=None,
                             tc_name=None, items=None) -> dict:
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

    doc.flags.ignore_permissions = True
    doc.save()
    return {"name": doc.name}


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
    y las liga al Production Plan a nivel de línea (production_plan + sub-assembly)."""
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
    stage_rows = _build_stage_subcontracting_rows(source)
    if not stage_rows:
        frappe.throw(_(
            "No hay etapas de subcontratación con proveedor y servicio. "
            "Configúralas en 'Etapas de Manufactura'."
        ))

    result = _create_subcontracting_pos_from_stages(source, stage_rows)
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
    return {"ok": True, "sent_to": recipient_list, "attachment": used}
