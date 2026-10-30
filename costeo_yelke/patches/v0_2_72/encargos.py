"""Encargos (docs/plan-encargos.md): un encargo es un ToDo de Frappe ligado al Costeo
con estos campos propios (api/encargos.py). Se ven en el ToDo del Escritorio en solo
lectura; la app es la que los llena."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    ro = {"read_only": 1, "no_copy": 1}
    create_custom_fields({"ToDo": [
        {"fieldname": "encargo_yelke_sb", "label": "Asignación (Costeo Yelke)", "fieldtype": "Section Break",
         "insert_after": "description", "collapsible": 1, "depends_on": "eval:doc.encargo_yelke"},
        {"fieldname": "encargo_yelke", "label": "Es asignación de la app", "fieldtype": "Check", "insert_after": "encargo_yelke_sb", **ro},
        {"fieldname": "vista_yelke", "label": "Paso", "fieldtype": "Data", "insert_after": "encargo_yelke", **ro},
        {"fieldname": "lote_yelke", "label": "Lote", "fieldtype": "Data", "insert_after": "vista_yelke", **ro},
        {"fieldname": "mensaje_yelke", "label": "Mensaje", "fieldtype": "Small Text", "insert_after": "lote_yelke", **ro},
        {"fieldname": "encargo_yelke_cb", "fieldtype": "Column Break", "insert_after": "mensaje_yelke"},
        {"fieldname": "cierre_yelke", "label": "Cómo se cerró", "fieldtype": "Select", "insert_after": "encargo_yelke_cb",
         "options": "\nAutomático\nManual\nRegresado\nQuitado", **ro},
        {"fieldname": "cerrado_en_yelke", "label": "Cerrado el", "fieldtype": "Datetime", "insert_after": "cierre_yelke", **ro},
        {"fieldname": "nota_cierre_yelke", "label": "Nota al cerrar", "fieldtype": "Small Text", "insert_after": "cerrado_en_yelke", **ro},
        {"fieldname": "visto_yelke", "label": "Tuvo pendiente", "fieldtype": "Check", "insert_after": "nota_cierre_yelke", "hidden": 1, **ro},
        {"fieldname": "avisos_yelke", "label": "Avisos de vencimiento", "fieldtype": "Int", "insert_after": "visto_yelke", "hidden": 1, **ro},
    ]}, update=True)
    frappe.db.add_index("ToDo", ["reference_type", "reference_name", "status"])
    frappe.clear_cache(doctype="ToDo")
