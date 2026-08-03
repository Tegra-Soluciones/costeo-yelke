import frappe


def execute():
    """Completa 'mexico_tax_type' (obligatorio para timbrado CFDI) en las filas de
    plantillas de impuestos de venta que quedaron sin asignar. Sin esto, cualquier
    documento que copie la plantilla (Delivery Note, Sales Order, etc.) truena al
    guardar con 'MandatoryError: mexico_tax_type'. Se infiere del nombre de la cuenta
    (IVA/ISR/IEPS) contra el catálogo de Tax Type."""
    if not frappe.db.has_column("Sales Taxes and Charges", "mexico_tax_type"):
        return

    rows = frappe.get_all(
        "Sales Taxes and Charges",
        filters={"parenttype": "Sales Taxes and Charges Template", "mexico_tax_type": ["in", ["", None]]},
        fields=["name", "account_head", "description"],
    )
    tax_types = set(frappe.get_all("Tax Type", pluck="name"))
    fixed = 0
    for row in rows:
        text = f"{row.account_head or ''} {row.description or ''}".upper()
        match = next((t for t in tax_types if t.upper() in text), None)
        if match:
            frappe.db.set_value("Sales Taxes and Charges", row.name, "mexico_tax_type", match, update_modified=False)
            fixed += 1

    if fixed:
        frappe.db.commit()
