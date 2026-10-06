import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Lote de producción en la remisión (Delivery Note). La remisión de un lote se
    arma con lo que el taller final entregó de ESE lote; el campo deja saber qué ya se
    remisionó de cada lote para no entregar dos veces lo mismo (ver
    costeo_api._entrega_de_lote / crear_remision)."""
    create_custom_fields(
        {
            "Delivery Note": [
                {
                    "fieldname": "lote_ref",
                    "label": "Lote de producción",
                    "fieldtype": "Data",
                    "insert_after": "costeo",
                    "read_only": 1,
                    "no_copy": 1,
                    "in_standard_filter": 1,
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Delivery Note")
