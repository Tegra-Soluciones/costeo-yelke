import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """'costeo' + 'lote_ref' en Request for Quotation y Supplier Quotation: para
    poder generar (y luego listar) una Solicitud de Cotización / Presupuesto de
    Proveedor por LOTE y por PROVEEDOR, igual que ya se hace con la Orden de
    Compra de materiales -- así la pantalla de cada lote puede mostrar el
    documento ya creado en vez de volver a generarlo."""
    fields = [{
        "fieldname": "costeo",
        "label": "Costeo",
        "fieldtype": "Link",
        "options": "Costeo",
        "insert_after": "company",
        "read_only": 1,
        "print_hide": 1,
        "no_copy": 1,
    }, {
        "fieldname": "lote_ref",
        "label": "Lote de producción",
        "fieldtype": "Data",
        "insert_after": "costeo",
        "read_only": 1,
        "print_hide": 1,
        "no_copy": 1,
    }]
    create_custom_fields(
        {"Request for Quotation": fields, "Supplier Quotation": fields},
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Request for Quotation")
    frappe.clear_cache(doctype="Supplier Quotation")
