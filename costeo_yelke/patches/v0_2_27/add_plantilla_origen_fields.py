import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Cada plantilla (ver costeo_template_api.py) guarda de dónde salió -- el
    Costeo, el 'título' (el nombre de proyecto libre que captura el usuario, ver
    patch v0_2_17) y el cliente de ese Costeo -- para que 'Mis Plantillas' pueda
    mostrar en qué proyecto se usó cada una y filtrar por cliente/proyecto. Se
    captura una sola vez al crear la plantilla (save_as_template); no cambia si el
    Costeo de origen se edita después."""
    create_custom_fields(
        {
            "Costeo": [
                {
                    "fieldname": "plantilla_origen_costeo",
                    "label": "Plantilla: Costeo de origen",
                    "fieldtype": "Data",
                    "insert_after": "nombre_plantilla",
                    "depends_on": "eval:doc.es_plantilla",
                    "hidden": 1,
                    "description": "Nombre del Costeo del que se cortó esta plantilla.",
                },
                {
                    "fieldname": "plantilla_origen_titulo",
                    "label": "Plantilla: Proyecto de origen",
                    "fieldtype": "Data",
                    "insert_after": "plantilla_origen_costeo",
                    "depends_on": "eval:doc.es_plantilla",
                    "read_only": 1,
                    "description": "Título del Costeo de origen -- en qué proyecto se usó esta plantilla.",
                },
                {
                    "fieldname": "plantilla_origen_cliente",
                    "label": "Plantilla: Cliente de origen",
                    "fieldtype": "Link",
                    "options": "Customer",
                    "insert_after": "plantilla_origen_titulo",
                    "depends_on": "eval:doc.es_plantilla",
                    "read_only": 1,
                },
            ]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Costeo")
