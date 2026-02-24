import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Add Costeo link field on Sales Order."""
    create_custom_fields(
        {
            "Sales Order": [
                {
                    "fieldname": "costeo",
                    "label": "Costeo",
                    "fieldtype": "Link",
                    "options": "Costeo",
                    "insert_after": "customer",
                    "read_only": 1,
                }
            ]
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Sales Order")
