import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo 'titulo' en Costeo -- texto libre que captura el usuario para identificar
    el proyecto a simple vista (el nombramiento automático CST-CLIENTE-AÑO-##### sigue
    igual, es solo el ID del documento). Se marca como title_field del doctype para que
    en cualquier parte donde Frappe muestre "el título" de un Costeo (listas nativas,
    links, breadcrumbs) use este campo en vez del ID -- la vista de lista del SPA
    (CosteoListPage.vue) también lo usa como texto principal."""
    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "titulo",
                "label": "Título",
                "fieldtype": "Data",
                "insert_after": "section_break_gusc",
                "in_list_view": 1,
                "description": "Texto libre para identificar el proyecto (el nombre del documento no cambia).",
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.make_property_setter({
        "doctype": "Costeo",
        "doctype_or_field": "DocType",
        "property": "title_field",
        "value": "titulo",
        "property_type": "Data",
    })
    frappe.clear_cache(doctype="Costeo")
