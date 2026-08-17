import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo 'costeo' en Item Price -- trazabilidad hacia el proyecto de origen de un
    precio acordado (fijado desde 'Fijar Precio' en Costeo/Cotización), para poder
    enlazar cada recordatorio de vigencia de vuelta al proyecto que lo generó."""
    create_custom_fields(
        {
            "Item Price": [{
                "fieldname": "costeo",
                "label": "Costeo",
                "fieldtype": "Link",
                "options": "Costeo",
                "insert_after": "customer",
                "read_only": 1,
                "no_copy": 1,
                "print_hide": 1,
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Item Price")
