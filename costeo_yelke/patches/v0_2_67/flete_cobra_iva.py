"""Flete que cobra el MISMO proveedor en su factura: a veces su CFDI le pone IVA al
envío y a veces no. Con la casilla marcada se agrega el renglón "IVA del flete" (16%
sobre el renglón del flete, nativo de ERPNext: "On Previous Row Amount"); ver
api/fletes.ajustar_iva_flete. En la factura de compra se hereda del recibo y se puede
corregir contra el CFDI."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    campo = {"fieldname": "flete_cobra_iva", "label": "El proveedor cobra IVA sobre el envío", "fieldtype": "Check",
             "default": "1", "depends_on": "eval:doc.flete_modo!='Paquetería externa'",
             "description": "Solo cuando el envío lo cobra el mismo proveedor en su factura."}
    create_custom_fields({
        "Purchase Order": [dict(campo, insert_after="flete_importe_capturado")],
        "Purchase Receipt": [dict(campo, insert_after="flete_importe_capturado")],
        "Purchase Invoice": [dict(campo, insert_after="flete_origen", depends_on=None)],
    }, update=True)
    for dt in ("Purchase Order", "Purchase Receipt", "Purchase Invoice"):
        frappe.clear_cache(doctype=dt)
