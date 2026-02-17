import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


SUBCONTRACT_DEPENDS = "eval:doc.is_subcontracted==1"


def execute():
    """Add HTML builder for flexible manufacturing tables on subcontracted Purchase Orders."""
    create_custom_fields(
        {
            "Purchase Order": [
                {
                    "fieldname": "om_tablas_html",
                    "label": "Editor de Tablas",
                    "fieldtype": "HTML",
                    "insert_after": "om_section_tablas_flexibles",
                    "depends_on": SUBCONTRACT_DEPENDS,
                },
                {
                    "fieldname": "om_tablas_flexibles",
                    "label": "Tablas Flexibles",
                    "fieldtype": "Table",
                    "options": "Orden Manufactura Tabla Flexible",
                    "insert_after": "om_tablas_html",
                    "depends_on": SUBCONTRACT_DEPENDS,
                    "hidden": 1,
                },
            ]
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Purchase Order")
