"""Desglose por talla de cada renglón de la Orden de Venta (JSON). Lo escribe
api/tallas_ov.py y lo lee la Orden de Manufactura para su desglose de tallas."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Sales Order Item": [{
        "fieldname": "desglose_tallas", "label": "Desglose por talla", "fieldtype": "Long Text",
        "insert_after": "description", "hidden": 1, "read_only": 1, "no_copy": 0,
        "description": "JSON del desglose por talla; la versión legible va en la descripción.",
    }]}, update=True)
