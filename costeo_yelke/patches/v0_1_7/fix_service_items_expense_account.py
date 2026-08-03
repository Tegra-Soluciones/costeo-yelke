import frappe


def execute():
    """Corrige la cuenta de gasto de los ítems de Servicio (maquila de subcontratación):
    deben capitalizar su costo vía 'Expenses Included In Valuation', no vía el gasto por
    defecto de la compañía (que en producción suele ser 'Costo de Ventas' y contamina esa
    cuenta ANTES de que exista una venta real)."""
    from costeo_yelke.api.item_api import _valuation_expense_account

    # Solo ítems que REALMENTE se usaron como servicio en una Orden de Subcontratación
    # (no todo el grupo "Servicios": ese grupo también tiene ítems de otras apps —p. ej.
    # licencias de software— que no deben tocarse).
    if not frappe.db.exists("DocType", "Subcontracting Order Service Item"):
        return
    service_items = frappe.get_all(
        "Subcontracting Order Service Item", pluck="item_code", distinct=True
    )
    service_items = [s for s in service_items if s]
    if not service_items:
        return

    defaults = frappe.get_all(
        "Item Default",
        filters={"parent": ["in", list(service_items)], "expense_account": ["in", ["", None]]},
        fields=["name", "parent", "company"],
    )
    fixed = 0
    for row in defaults:
        acc = _valuation_expense_account(row.company)
        if acc:
            frappe.db.set_value("Item Default", row.name, "expense_account", acc, update_modified=False)
            fixed += 1

    if fixed:
        frappe.db.commit()
