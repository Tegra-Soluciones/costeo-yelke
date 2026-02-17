import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Expose supplier on Production Plan raw materials and Material Request items."""
    create_custom_fields(
        {
            "Material Request Plan Item": [
                {
                    "fieldname": "supplier",
                    "label": "Proveedor",
                    "fieldtype": "Link",
                    "options": "Supplier",
                    "insert_after": "item_name",
                    "in_list_view": 1,
                }
            ],
            "Material Request Item": [
                {
                    "fieldname": "supplier",
                    "label": "Proveedor",
                    "fieldtype": "Link",
                    "options": "Supplier",
                    "insert_after": "item_name",
                    "in_list_view": 1,
                }
            ],
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Material Request Plan Item")
    frappe.clear_cache(doctype="Material Request Item")
