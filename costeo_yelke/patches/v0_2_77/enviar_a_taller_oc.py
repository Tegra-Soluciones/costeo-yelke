"""«Enviar a» en la orden de compra (api/envio_oc.py): el taller y la dirección a los
que el proveedor puede mandar el material directo. Solo se imprime; no cambia el
recibo ni el inventario."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Purchase Order": [
        {"fieldname": "enviar_a_taller", "label": "Enviar a (taller)", "fieldtype": "Link",
         "options": "Supplier", "insert_after": "schedule_date", "allow_on_submit": 1,
         "depends_on": "eval:!doc.is_subcontracted",
         "description": "El proveedor manda el material directo a este taller. Vacío = a Yelke. Solo se imprime en la orden."},
        {"fieldname": "enviar_a_direccion", "label": "Dirección de envío al taller", "fieldtype": "Link",
         "options": "Address", "insert_after": "enviar_a_taller", "allow_on_submit": 1,
         "depends_on": "eval:doc.enviar_a_taller"},
    ]}, update=True)
    frappe.clear_cache(doctype="Purchase Order")
