import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Dos campos:
    - 'lote_ref' en Material Request Item: divide la solicitud en lotes ANTES de
      generar ninguna Orden de Compra (la OC de cada lote se genera después, desde
      su propia pantalla, ya no automáticamente al validar la solicitud).
    - 'enviado_el' en Purchase Order: cuándo se envió al proveedor (por correo,
      desde el botón Enviar) -- para mostrar un estatus "Enviado" además de
      Borrador/Validado."""
    create_custom_fields(
        {
            "Material Request Item": [{
                "fieldname": "lote_ref",
                "label": "Lote de producción",
                "fieldtype": "Data",
                "insert_after": "schedule_date",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            }],
            "Purchase Order": [{
                "fieldname": "enviado_el",
                "label": "Enviado al proveedor el",
                "fieldtype": "Datetime",
                "insert_after": "lote_ref",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Material Request Item")
    frappe.clear_cache(doctype="Purchase Order")
