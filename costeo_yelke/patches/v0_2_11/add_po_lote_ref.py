import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo 'lote_ref' en Purchase Order (materia prima) -- el mismo concepto que ya
    existe en Subcontracting Order, para poder mostrar en la pantalla de un lote tanto
    su OC de materia prima + recibo como su cadena de subcontratación, agrupadas."""
    create_custom_fields(
        {
            "Purchase Order": [{
                "fieldname": "lote_ref",
                "label": "Lote de producción",
                "fieldtype": "Data",
                "insert_after": "material_request",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Purchase Order")
