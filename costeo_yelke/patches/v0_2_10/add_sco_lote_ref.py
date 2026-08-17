import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo 'lote_ref' en Subcontracting Order: correlaciona las SCO de distintas
    etapas (cada una en su propia Orden de Compra) que pertenecen al mismo lote de
    producción -- así la vista de Producir puede agrupar "Bordado lote 1",
    "Confección lote 1", "Sublimado lote 1" como un solo lote que avanza paso a
    paso hacia la prenda terminada, en vez de mostrarlas sueltas por etapa."""
    create_custom_fields(
        {
            "Subcontracting Order": [{
                "fieldname": "lote_ref",
                "label": "Lote de producción",
                "fieldtype": "Data",
                "insert_after": "purchase_order",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Subcontracting Order")
