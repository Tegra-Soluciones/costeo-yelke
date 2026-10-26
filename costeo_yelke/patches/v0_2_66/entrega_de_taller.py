"""A dónde manda el taller lo que termina (ver api/entregas_taller.py): la casilla
"Indicar a dónde entregar" y la tabla con cada destino, en la orden de maquila.
allow_on_submit: se puede corregir con la orden ya validada, antes de enviarla."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SUBCONTRACT_DEPENDS = "eval:doc.is_subcontracted==1"


def execute():
    frappe.reload_doc("costeo_yelke", "doctype", "orden_manufactura_entrega")
    create_custom_fields({
        "Purchase Order": [
            {"fieldname": "om_section_entrega", "label": "Al terminar, entregar a", "fieldtype": "Section Break",
             "insert_after": "om_archivos", "depends_on": SUBCONTRACT_DEPENDS, "collapsible": 1,
             "allow_on_submit": 1},
            {"fieldname": "om_indicar_entrega", "label": "Indicar a dónde entregar", "fieldtype": "Check",
             "insert_after": "om_section_entrega", "default": "1", "depends_on": SUBCONTRACT_DEPENDS,
             "allow_on_submit": 1,
             "description": "Sale en la orden de maquila. Sin filas capturadas se toma del flujo de producción."},
            {"fieldname": "om_entregas", "label": "Entregas", "fieldtype": "Table",
             "options": "Orden Manufactura Entrega", "insert_after": "om_indicar_entrega",
             "depends_on": "eval:doc.is_subcontracted==1 && doc.om_indicar_entrega", "allow_on_submit": 1},
        ],
    }, update=True)
    frappe.clear_cache(doctype="Purchase Order")
