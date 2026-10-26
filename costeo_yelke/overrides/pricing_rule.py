import frappe
from frappe import _
from frappe.utils import flt


def precio_minimo_del_costeo(doc, method=None):
    """validate de Pricing Rule: una tabla de precios por volumen (venta, tipo Rate) nunca
    baja del precio de venta con que se costeó el artículo -- el del último costeo vivo
    donde aparece (producto base o variante de talla, cada uno con SU precio).

    Va en el doctype y no solo en la pantalla de alta para que aplique igual desde la
    ficha de Producto, el escritorio de ERPNext o cualquier API. Un artículo que no viene
    de ningún costeo no tiene piso."""
    if not doc.selling or doc.disable or doc.rate_or_discount != "Rate" or not flt(doc.rate):
        return
    if doc.apply_on != "Item Code":
        return
    for fila in doc.get("items") or []:
        piso = _precio_costeo(fila.item_code)
        if piso and flt(doc.rate, 2) < piso:
            frappe.throw(
                _("{0}: el precio por volumen ({1}) no puede ser menor al precio de venta del costeo ({2}).").format(
                    fila.item_code, frappe.format_value(flt(doc.rate), "Currency"), frappe.format_value(piso, "Currency")),
                title=_("Precio por debajo del costeo"),
            )


def _precio_costeo(item_code):
    if not item_code:
        return 0
    fila = frappe.db.sql("""
        select cp.unit_sales_price
        from `tabCosteo Producto` cp
        join `tabCosteo` c on c.name = cp.parent
        where cp.parenttype = 'Costeo' and cp.finished_item = %s and c.docstatus < 2
          and ifnull(cp.unit_sales_price, 0) > 0
        order by c.modified desc
        limit 1
    """, item_code)
    return flt(fila[0][0], 2) if fila else 0
