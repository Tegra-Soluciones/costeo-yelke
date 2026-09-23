import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo 'referencia_entrega' en Subcontracting Order: etiqueta de texto libre
    (ej. "Puños", "Mangas") para cuando un taller entrega el trabajo de un lote
    en VARIAS TANDAS -- cada tanda es un sub-ensamblaje físico distinto que el
    usuario decidió explícitamente NO registrar como Artículo/variante (ver
    costeo_api.parada_registrar_entrega). Puramente informativa, para poder
    distinguir una entrega de otra a simple vista en la bitácora de un lote."""
    create_custom_fields(
        {
            "Subcontracting Order": [{
                "fieldname": "referencia_entrega",
                "label": "Referencia de la entrega",
                "fieldtype": "Data",
                "insert_after": "lote_ref",
                "allow_on_submit": 1,
                "print_hide": 1,
                "no_copy": 1,
                "description": "Texto libre para distinguir esta entrega de otras del mismo lote/parada (ej. 'Puños', 'Mangas') -- no crea ni liga ningún Artículo.",
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Subcontracting Order")
