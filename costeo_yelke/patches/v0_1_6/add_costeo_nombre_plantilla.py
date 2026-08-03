import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Nombre para identificar plantillas reutilizables de costeo."""
    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "nombre_plantilla",
                "label": "Nombre de plantilla",
                "fieldtype": "Data",
                "insert_after": "es_plantilla",
                "depends_on": "eval:doc.es_plantilla",
                "description": "Nombre para identificar esta plantilla reutilizable.",
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Costeo")
