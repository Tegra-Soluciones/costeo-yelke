"""«Entrega estimada al cliente» en la remisión: cuándo llega (puede ser futura, p. ej.
dos días de paquetería). Solo informativa e impresa; la fecha del documento
(posting_date) es la de salida del almacén y no puede ser futura
(api/contabilidad.sin_fecha_futura)."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Delivery Note": [
        {"fieldname": "entrega_estimada", "label": "Entrega estimada al cliente", "fieldtype": "Date",
         "insert_after": "posting_date", "allow_on_submit": 1,
         "description": "Cuándo llega al cliente. Solo informativa; se imprime en la remisión."},
    ]}, update=True)
    frappe.clear_cache(doctype="Delivery Note")
