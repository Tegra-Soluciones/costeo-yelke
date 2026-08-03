import frappe


def execute():
    frappe.reload_doctype("Costeo")
    frappe.db.sql(
        "UPDATE `tabCosteo` SET costeo_status = 'Borrador' WHERE costeo_status IS NULL OR costeo_status = ''"
    )
