import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """El overhead (nóminas, luz, internet, renta -- indirectos que un contador fija
    como % aparte) se estaba reportando solo en el Reporte final del Costeo, sin
    registrarse en contabilidad -- ver validar_documento en costeo_api.py, que ahora
    lo contabiliza como póliza (Journal Entry) al validar la Factura de Venta."""
    create_custom_fields(
        {
            "Sales Invoice": [
                {
                    "fieldname": "overhead_journal_entry",
                    "label": "Póliza de overhead",
                    "fieldtype": "Link",
                    "options": "Journal Entry",
                    "insert_after": "due_date",
                    "read_only": 1,
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Sales Invoice")
