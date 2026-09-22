import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Cada plantilla (ver costeo_template_api.py) ya guarda de qué Costeo/proyecto/
    cliente salió (ver patch v0_2_27) -- agrega también la fecha del Costeo de
    origen (su propio campo 'fecha', no la fecha de creación del registro en el
    sistema), para que 'Mis Plantillas' pueda mostrarla como dato informativo y
    filtrar por ella. Se captura una sola vez al crear/actualizar la plantilla
    (_sync_templates_from_costeo); no cambia si el Costeo de origen se edita
    después."""
    create_custom_fields(
        {
            "Costeo": [
                {
                    "fieldname": "plantilla_origen_fecha",
                    "label": "Plantilla: Fecha de origen",
                    "fieldtype": "Date",
                    "insert_after": "plantilla_origen_cliente",
                    "depends_on": "eval:doc.es_plantilla",
                    "read_only": 1,
                    "description": "Fecha del Costeo de origen -- de cuándo es el proyecto en el que se usó esta plantilla.",
                },
            ]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Costeo")
