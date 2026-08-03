import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Garantiza los campos Link 'costeo' en Quotation y Sales Order.

    El patch previo (v0_0_9) quedó registrado pero el campo no se materializó,
    y Quotation nunca tuvo campo. Sin estos campos el SPA no puede ligar ni
    recuperar la cotización / orden de venta de un Costeo.
    """
    create_custom_fields(
        {
            "Quotation": [
                {
                    "fieldname": "costeo",
                    "label": "Costeo",
                    "fieldtype": "Link",
                    "options": "Costeo",
                    "insert_after": "party_name",
                    "read_only": 1,
                    "print_hide": 1,
                    "no_copy": 1,
                }
            ],
            "Sales Order": [
                {
                    "fieldname": "costeo",
                    "label": "Costeo",
                    "fieldtype": "Link",
                    "options": "Costeo",
                    "insert_after": "customer",
                    "read_only": 1,
                    "print_hide": 1,
                    "no_copy": 1,
                }
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Quotation")
    frappe.clear_cache(doctype="Sales Order")
