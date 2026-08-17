import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Expone un precio editable por material en la Solicitud de Material -- antes solo
    se podia ajustar el proveedor ahi; el precio se jalaba solo (cotizacion de proveedor
    o ultima compra) hasta crear la OC. Si el proveedor por defecto queda mal, ahora se
    puede corregir el precio en el mismo paso, y ese precio manual se respeta al generar
    la OC (ver mr_crear_oc)."""
    create_custom_fields(
        {
            "Material Request Item": [
                {
                    "fieldname": "rate",
                    "label": "Precio",
                    "fieldtype": "Currency",
                    "insert_after": "supplier",
                    "in_list_view": 1,
                }
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Material Request Item")
