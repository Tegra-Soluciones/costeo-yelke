"""Formatos Yelke como predeterminados de recibos, movimientos de material, solicitudes
de material y facturas (mismo diseño que los de venta y compra, ver patch v0_2_51)."""
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

FORMATOS = {
    "Purchase Receipt": "Recibo de Compra Yelke",
    "Subcontracting Receipt": "Recibo de Taller Yelke",
    "Stock Entry": "Movimiento de Material Yelke",
    "Material Request": "Solicitud de Material Yelke",
    "Purchase Invoice": "Factura de Compra Yelke",
    "Sales Invoice": "Factura de Venta Yelke",
}


def execute():
    for doctype, formato in FORMATOS.items():
        if frappe.db.exists("Print Format", formato):
            make_property_setter(doctype, None, "default_print_format", formato, "Data",
                                 for_doctype=True, validate_fields_for_doctype=False)
