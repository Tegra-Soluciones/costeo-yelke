import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


MATERIAL_REQUEST_SUPPLIER_FIELDS = {
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
}


def ensure_material_request_supplier_fields():
    """Ensure supplier fields used by Costeo exist on MR planning and MR items."""
    create_custom_fields(
        MATERIAL_REQUEST_SUPPLIER_FIELDS,
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Material Request Plan Item")
    frappe.clear_cache(doctype="Material Request Item")


def after_install():
    ensure_material_request_supplier_fields()

