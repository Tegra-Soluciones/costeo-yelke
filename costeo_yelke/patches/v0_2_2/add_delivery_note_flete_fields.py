import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Costo de envío al cliente en la remisión. ERPNext no tiene un campo nativo para
    esto en Delivery Note -- la tabla 'taxes' (Sales Taxes and Charges) no sirve porque
    la app mexico_einvoice la vuelve obligatoriamente clasificada como IVA/ISR/IEPS
    (mexico_tax_type, reqd=1) para el timbrado CFDI, y un flete no es un impuesto.
    En vez de eso, se captura aquí y se registra como póliza contable (Journal Entry)
    al validar la remisión -- ver validar_remision en costeo_api.py."""
    create_custom_fields(
        {
            "Delivery Note": [
                {
                    "fieldname": "flete_proveedor",
                    "label": "Proveedor de transporte",
                    "fieldtype": "Link",
                    "options": "Supplier",
                    "insert_after": "shipping_address_name",
                },
                {
                    "fieldname": "flete_costo",
                    "label": "Costo de envío",
                    "fieldtype": "Currency",
                    "insert_after": "flete_proveedor",
                },
                {
                    "fieldname": "flete_journal_entry",
                    "label": "Póliza de flete",
                    "fieldtype": "Link",
                    "options": "Journal Entry",
                    "insert_after": "flete_costo",
                    "read_only": 1,
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Delivery Note")
