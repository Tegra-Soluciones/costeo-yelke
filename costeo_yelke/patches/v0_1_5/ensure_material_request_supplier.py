import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Garantiza el campo 'supplier' en Material Request Item y Material Request Plan Item.

    El patch v0_0_3 quedó registrado pero los campos no se materializaron. Sin ellos
    el SPA no puede pre-llenar el proveedor por materia prima ni crear una OC por proveedor.
    """
    create_custom_fields(
        {
            "Material Request Item": [{
                "fieldname": "supplier",
                "label": "Proveedor",
                "fieldtype": "Link",
                "options": "Supplier",
                "insert_after": "warehouse",
            }],
            "Material Request Plan Item": [{
                "fieldname": "supplier",
                "label": "Proveedor",
                "fieldtype": "Link",
                "options": "Supplier",
                "insert_after": "warehouse",
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Material Request Item")
    frappe.clear_cache(doctype="Material Request Plan Item")
