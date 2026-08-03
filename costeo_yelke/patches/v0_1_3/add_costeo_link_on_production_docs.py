import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo Link 'costeo' en los documentos de producción, para que el panel
    Producir del SPA pueda recuperar y gestionar lo que generó cada Costeo."""
    targets = {
        "Production Plan": "company",
        "Material Request": "company",
        "Purchase Order": "supplier",
        "Work Order": "company",
    }
    fields = {
        dt: [{
            "fieldname": "costeo",
            "label": "Costeo",
            "fieldtype": "Link",
            "options": "Costeo",
            "insert_after": after,
            "read_only": 1,
            "print_hide": 1,
            "no_copy": 1,
        }]
        for dt, after in targets.items()
    }
    create_custom_fields(fields, ignore_validate=True, update=True)
    for dt in targets:
        frappe.clear_cache(doctype=dt)
