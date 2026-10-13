import frappe


def execute():
    """La póliza de overhead es de UNA factura: al corregir (amend) una factura
    cancelada, el campo copiado apuntaba a la póliza ya cancelada y ERPNext no dejaba
    guardar la corrección ("Cannot link cancelled document"). La nueva genera la suya
    al validarse."""
    cf = frappe.db.get_value("Custom Field", {"dt": "Sales Invoice", "fieldname": "overhead_journal_entry"})
    if cf:
        frappe.db.set_value("Custom Field", cf, "no_copy", 1)
        frappe.clear_cache(doctype="Sales Invoice")
