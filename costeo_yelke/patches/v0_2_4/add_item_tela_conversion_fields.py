import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Gramaje (g/m²) y ancho (m) del rollo, para el conversor de precio $/kg -> $/m
    de telas en el Costeo -- se guardan en el Item (no en el renglón del Costeo) para
    no volver a capturarlos cada vez que esa misma tela se usa en otro costeo."""
    create_custom_fields(
        {
            "Item": [
                {
                    "fieldname": "costeo_tela_section",
                    "label": "Conversión de tela",
                    "fieldtype": "Section Break",
                    "insert_after": "weight_uom",
                    "collapsible": 1,
                    "depends_on": "eval:doc.is_stock_item",
                },
                {
                    "fieldname": "gramaje",
                    "label": "Gramaje (g/m²)",
                    "fieldtype": "Float",
                    "precision": "2",
                    "insert_after": "costeo_tela_section",
                    "description": "Gramos por metro cuadrado de la tela -- usado para convertir su precio de $/kg a $/m.",
                },
                {
                    "fieldname": "costeo_tela_column_break",
                    "fieldtype": "Column Break",
                    "insert_after": "gramaje",
                },
                {
                    "fieldname": "ancho",
                    "label": "Ancho de rollo (m)",
                    "fieldtype": "Float",
                    "precision": "2",
                    "insert_after": "costeo_tela_column_break",
                    "description": "Ancho del rollo de tela en metros -- usado para convertir su precio de $/kg a $/m.",
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
