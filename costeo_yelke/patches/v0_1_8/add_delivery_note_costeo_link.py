import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo Link 'costeo' en Delivery Note, para trazabilidad con el resto del flujo
    (Cotización, Orden de Venta, Factura ya lo tienen)."""
    create_custom_fields(
        {
            "Delivery Note": [{
                "fieldname": "costeo",
                "label": "Costeo",
                "fieldtype": "Link",
                "options": "Costeo",
                "insert_after": "customer",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Delivery Note")
