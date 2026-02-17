import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Add supplier link on Warehouse for supplier-owned warehouses."""
    create_custom_fields(
        {
            "Warehouse": [
                {
                    "fieldname": "proveedor_asociado",
                    "label": "Proveedor Asociado",
                    "fieldtype": "Link",
                    "options": "Supplier",
                    "insert_after": "warehouse_type",
                    "depends_on": "eval:!doc.is_group",
                    "description": "Usar cuando el almacen pertenece a un proveedor.",
                }
            ]
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Warehouse")
