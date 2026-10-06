import frappe
from frappe.utils import flt


def registrar_precios_oficiales(doc, method=None):
    """Al validar una OC, registra/actualiza el precio "oficial" de cada línea CON
    ESE proveedor puntual (Item Price de compra, campo `supplier`) -- es la fuente
    que `costeo_template_api.item_price_oficial_proveedor` / `costeo_api._precio_para_oc`
    prefieren sobre el precio del costeo. Cada OC validada nueva con ese proveedor
    REFRESCA este precio (no solo la primera vez) -- la otra manera de que exista es
    capturarlo a mano en ERPNext (Item Price), lo cual esta función respeta igual:
    si ya existe la fila, solo actualiza `price_list_rate`, no la recrea."""
    if not doc.supplier:
        return

    price_list = doc.buying_price_list or frappe.db.get_value(
        "Price List", {"buying": 1, "enabled": 1}, "name"
    )
    if not price_list:
        return

    for it in doc.items:
        if not it.item_code or not flt(it.rate):
            continue
        uom = it.uom or frappe.db.get_value("Item", it.item_code, "stock_uom")
        if not uom:
            continue
        existing = frappe.db.get_value(
            "Item Price",
            {
                "item_code": it.item_code,
                "price_list": price_list,
                "supplier": doc.supplier,
                "uom": uom,
            },
            "name",
        )
        if existing:
            frappe.db.set_value("Item Price", existing, "price_list_rate", flt(it.rate))
            continue
        price_doc = frappe.new_doc("Item Price")
        price_doc.item_code = it.item_code
        price_doc.price_list = price_list
        price_doc.supplier = doc.supplier
        price_doc.uom = uom
        price_doc.price_list_rate = flt(it.rate)
        price_doc.flags.ignore_permissions = True
        try:
            price_doc.insert()
        except Exception:
            frappe.log_error(
                title="registrar_precios_oficiales",
                message=frappe.get_traceback(),
            )
