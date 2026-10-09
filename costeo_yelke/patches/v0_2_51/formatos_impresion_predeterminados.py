"""Formatos de impresión de Yelke como predeterminados de su documento. Cotización,
Orden de Venta y Nota de Entrega se crearon a mano en producción y desde 2026-10-09
viven en la app (print_format/), con el mismo nombre para no duplicarlos."""
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

FORMATOS = {
    "Quotation": "Cotización Yelke",
    "Sales Order": "Orden de Venta Yelke",
    "Delivery Note": "Nota de Entrega Yelke",
    "Purchase Order": "Orden de Compra Yelke",
    "Costeo": "Costeo",
}


def execute():
    for doctype, formato in FORMATOS.items():
        if frappe.db.exists("Print Format", formato):
            make_property_setter(doctype, None, "default_print_format", formato, "Data",
                                 for_doctype=True, validate_fields_for_doctype=False)
