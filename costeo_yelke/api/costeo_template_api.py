# -*- coding: utf-8 -*-
"""API de Plantillas de Costeo y refresco de precios.

Una "Plantilla de Costeo" es un Costeo marcado con ``es_plantilla = 1`` que guarda
la estructura reutilizable de una familia de prenda (productos, materiales y etapas)
SIN cliente y SIN precios envejecidos. Al crear un costeo nuevo desde la plantilla se
clona la estructura y se refrescan los precios desde las listas de compra vigentes.

El refresco replica la agregación del formulario (modules/90_calculations.js):
  - Total de fila T2 = (consumo / factor_conversion) * precio_unitario
  - material_cost  = suma de totales T2 con concept_type "Materia Prima"
  - services_cost  = suma de totales T2 "Servicio" + suma de precio_servicio de etapas (T3)
  - shipping_cost  = se conserva (captura manual)
  - base = material + servicios + envio; overhead = base * overhead_pct/100
  - total_unit_cost = base + overhead; precio_venta = total / (1 - margen)
"""

import math

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

# Tablas del Plan de Produccion embebido que NO deben viajar con la plantilla/copia.
PP_TABLES = [
    "sales_orders",
    "material_requests",
    "po_items",
    "prod_plan_references",
    "sub_assembly_items",
    "mr_items",
    "warehouses",
]


# ---------------------------------------------------------------------------
# Precios
# ---------------------------------------------------------------------------
def _get_buying_rate(item_code, supplier=None):
    """Mejor precio de compra conocido para un item.

    Prioridad: Item Price (buying) del proveedor -> Item Price (buying) cualquiera
    -> ultima tarifa de compra del Item.
    """
    if not item_code:
        return None

    if supplier:
        rows = frappe.get_all(
            "Item Price",
            filters={"item_code": item_code, "buying": 1, "supplier": supplier},
            fields=["price_list_rate"],
            order_by="valid_from desc, modified desc",
            limit=1,
        )
        if rows and rows[0].price_list_rate:
            return flt(rows[0].price_list_rate)

    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "buying": 1},
        fields=["price_list_rate"],
        order_by="valid_from desc, modified desc",
        limit=1,
    )
    if rows and rows[0].price_list_rate:
        return flt(rows[0].price_list_rate)

    last_rate = frappe.db.get_value("Item", item_code, "last_purchase_rate")
    return flt(last_rate) if last_rate else None


def _recompute_t2_row(row):
    qty = flt(row.internal_qty)
    factor = flt(row.conversion_factor) or 1
    price = flt(row.unit_price)

    supplier_qty = qty / factor if factor else 0
    row.supplier_qty = supplier_qty
    row.min_supplier_qty = math.ceil(supplier_qty) if supplier_qty else 0
    row.total = supplier_qty * price


def _recompute_aggregates(doc):
    detalles = doc.get("costeo_producto_detalle") or []
    etapas = doc.get("tabla_etapas_costeo") or []

    for prod in doc.get("costeo_producto") or []:
        finished = prod.finished_item
        material = 0.0
        services = 0.0

        for det in detalles:
            if det.finished_item != finished:
                continue
            concept = (det.concept_type or "").strip()
            if concept in ("Materia Prima", ""):
                material += flt(det.total)
            elif concept == "Servicio":
                services += flt(det.total)
            # "Envío" no se agrega: shipping_cost es captura manual.

        for etapa in etapas:
            if etapa.producto_terminado == finished and etapa.servicio and etapa.precio_servicio:
                services += flt(etapa.precio_servicio)

        prod.material_cost = material
        prod.services_cost = services

        base = material + services + flt(prod.shipping_cost)
        prod.overhead_amt = base * (flt(prod.overhead_pct) / 100.0)
        prod.total_unit_cost = base + flt(prod.overhead_amt)

        margin = flt(prod.margin_pct) / 100.0
        if 0 <= margin < 1 and prod.total_unit_cost:
            prod.unit_sales_price = prod.total_unit_cost / (1 - margin)
        prod.total_sales_price = flt(prod.unit_sales_price) * flt(prod.qty)


def _refresh_costeo_prices(doc, only_missing=False):
    """Actualiza precios de materia prima (T2) y de maquila (T3) y recomputa agregados.

    ``only_missing`` = solo rellena precios en 0 (no pisa lo capturado a mano).
    Devuelve cuantos precios se actualizaron.
    """
    updated = 0

    for row in doc.get("costeo_producto_detalle") or []:
        if row.item:
            rate = _get_buying_rate(row.item, row.get("supplier"))
            if rate is not None and (not only_missing or not flt(row.unit_price)):
                row.unit_price = rate
                updated += 1
        _recompute_t2_row(row)

    for row in doc.get("tabla_etapas_costeo") or []:
        if row.servicio:
            rate = _get_buying_rate(row.servicio, row.get("proveedor"))
            if rate is not None and (not only_missing or not flt(row.precio_servicio)):
                row.precio_servicio = rate
                updated += 1

    _recompute_aggregates(doc)
    return updated


def _reset_production_plan(doc):
    for fieldname in PP_TABLES:
        doc.set(fieldname, [])
    doc.pp_tab_unlocked = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_costeo_templates():
    """Lista de plantillas de costeo con conteo de productos."""
    templates = frappe.get_all(
        "Costeo",
        filters={"es_plantilla": 1},
        fields=["name", "nombre_plantilla", "familia_prenda", "compañia", "modified"],
        order_by="modified desc",
    )
    for tpl in templates:
        tpl["productos"] = frappe.db.count("Costeo Producto", {"parent": tpl["name"]})
    return templates


@frappe.whitelist()
def get_familias():
    """Familias de prenda ya usadas (catálogo auto-organizado para autocompletar)."""
    rows = frappe.db.sql(
        "SELECT DISTINCT familia_prenda FROM `tabCosteo` "
        "WHERE familia_prenda IS NOT NULL AND familia_prenda != '' ORDER BY familia_prenda"
    )
    return [r[0] for r in rows]


@frappe.whitelist()
def delete_template(name):
    """Elimina una plantilla."""
    if not frappe.db.get_value("Costeo", name, "es_plantilla"):
        frappe.throw(_("El documento {0} no es una plantilla.").format(name))
    frappe.delete_doc("Costeo", name, force=True, ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist()
def create_costeo_from_template(template, cliente, compania=None, fecha=None):
    """Crea un Costeo nuevo desde una plantilla, con precios frescos."""
    tpl = frappe.get_doc("Costeo", template)
    if not cint(tpl.get("es_plantilla")):
        frappe.throw(_("El documento {0} no es una plantilla.").format(template))

    new_doc = frappe.copy_doc(tpl)
    new_doc.es_plantilla = 0
    new_doc.nombre_plantilla = None
    # La plantilla no trae cantidad; se arranca en 1 para que el usuario la ajuste.
    for p in new_doc.get("costeo_producto") or []:
        if not flt(p.qty):
            p.qty = 1
    new_doc.cliente = cliente
    if compania:
        new_doc.set("compañia", compania)
    new_doc.fecha = fecha or nowdate()
    new_doc.costeo_status = "Borrador"
    _reset_production_plan(new_doc)
    _refresh_costeo_prices(new_doc)

    new_doc.flags.ignore_permissions = True
    new_doc.insert()
    return {"name": new_doc.name, "cliente": cliente}


@frappe.whitelist()
def save_as_template(costeo, nombre=None, familia_prenda=None):
    """Guarda un Costeo existente como plantilla reutilizable (sin cliente)."""
    src = frappe.get_doc("Costeo", costeo)
    tpl = frappe.copy_doc(src)
    tpl.es_plantilla = 1
    tpl.nombre_plantilla = (nombre or src.get("nombre_plantilla") or src.get("familia_prenda")
                            or _("Plantilla de {0}").format(src.name))
    if familia_prenda:
        tpl.familia_prenda = familia_prenda
    tpl.cliente = None
    tpl.costeo_status = "Borrador"
    # La cantidad es específica de cada pedido; no se guarda en la plantilla.
    for p in tpl.get("costeo_producto") or []:
        p.qty = 0
    _reset_production_plan(tpl)

    tpl.flags.ignore_permissions = True
    tpl.flags.ignore_mandatory = True
    tpl.insert()
    return {"name": tpl.name, "nombre": tpl.nombre_plantilla}


@frappe.whitelist()
def refresh_costeo_prices(costeo, only_missing=0):
    """Refresca precios de un Costeo existente contra las listas de compra vigentes."""
    doc = frappe.get_doc("Costeo", costeo)
    updated = _refresh_costeo_prices(doc, only_missing=cint(only_missing))
    doc.flags.ignore_permissions = True
    doc.save()
    return {"ok": True, "updated": updated, "costeo": doc.name}
