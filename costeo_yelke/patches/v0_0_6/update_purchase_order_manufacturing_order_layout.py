import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


SUBCONTRACT_DEPENDS = "eval:doc.is_subcontracted==1"


def execute():
    """Refine OM layout/UX in Purchase Order for fixed size tables."""
    create_custom_fields(
        {
            "Purchase Order": [
                {
                    "fieldname": "om_section_tallas_caballero",
                    "label": "Tallas Caballero",
                    "fieldtype": "Section Break",
                    "insert_after": "om_ubicacion",
                    "depends_on": SUBCONTRACT_DEPENDS,
                },
                {
                    "fieldname": "om_tallas_caballero",
                    "label": "Tallas Caballero",
                    "fieldtype": "Table",
                    "options": "Orden Manufactura Talla Caballero",
                    "insert_after": "om_section_tallas_caballero",
                    "depends_on": SUBCONTRACT_DEPENDS,
                    "cannot_add_rows": 1,
                    "cannot_delete_rows": 1,
                },
                {
                    "fieldname": "om_prendas_caballero_total",
                    "label": "Prendas (Total)",
                    "fieldtype": "Int",
                    "insert_after": "om_tallas_caballero",
                    "read_only": 1,
                    "depends_on": SUBCONTRACT_DEPENDS,
                },
                {
                    "fieldname": "om_section_tallas_dama",
                    "label": "Tallas Dama",
                    "fieldtype": "Section Break",
                    "insert_after": "om_prendas_caballero_total",
                    "depends_on": SUBCONTRACT_DEPENDS,
                },
                {
                    "fieldname": "om_tallas_dama",
                    "label": "Tallas Dama",
                    "fieldtype": "Table",
                    "options": "Orden Manufactura Talla Dama",
                    "insert_after": "om_section_tallas_dama",
                    "depends_on": SUBCONTRACT_DEPENDS,
                    "cannot_add_rows": 1,
                    "cannot_delete_rows": 1,
                },
                {
                    "fieldname": "om_prendas_dama_total",
                    "label": "Prendas (Total)",
                    "fieldtype": "Int",
                    "insert_after": "om_tallas_dama",
                    "read_only": 1,
                    "depends_on": SUBCONTRACT_DEPENDS,
                },
            ]
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Purchase Order")
