"""Toda factura del sistema es para contabilidad y uso interno: las de venta se timbran
en otro sistema y las de compra llegan como PDF/XML del proveedor. Por eso cada factura
(compra y venta) lleva SU archivo: el PDF es obligatorio para validarla y el XML,
opcional.

Los campos NO son `reqd`: la factura nace en BORRADOR y un archivo solo se puede colgar
de un documento que ya existe. La obligatoriedad vive en el `before_submit`
(costeo_yelke.api.contabilidad.validar_archivos_factura), que tampoco se salta desde el
escritorio de ERPNext. `no_copy`: el archivo es de UNA factura.
"""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def _campos(despues_de):
    return [
        {"fieldname": "factura_pdf", "label": "Factura (PDF)", "fieldtype": "Attach",
         "insert_after": despues_de, "no_copy": 1,
         "description": "El PDF de la factura. Obligatorio para validarla."},
        {"fieldname": "factura_xml", "label": "Factura (XML)", "fieldtype": "Attach",
         "insert_after": "factura_pdf", "no_copy": 1,
         "description": "El XML del CFDI, si se tiene. Opcional."},
    ]


def execute():
    create_custom_fields({
        "Purchase Invoice": _campos("bill_date"),
        "Sales Invoice": _campos("due_date"),
    }, update=True)
