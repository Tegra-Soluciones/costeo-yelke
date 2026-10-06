import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Proveedor del flete en los "costos adicionales" (Landed Cost Taxes and Charges:
    la usan la transferencia al taller y el recibo del taller). ERPNext capitaliza ese
    costo al inventario abonando 'Gastos incluidos en la valoración', pero no registra
    a quién se le debe; con el proveedor, al validar se genera la póliza contra su
    cuenta por pagar (ver costeo_yelke.api.contabilidad.crear_polizas_flete)."""
    create_custom_fields(
        {
            "Landed Cost Taxes and Charges": [
                {
                    "fieldname": "proveedor_flete",
                    "label": "Proveedor del flete",
                    "fieldtype": "Link",
                    "options": "Supplier",
                    "insert_after": "description",
                    "in_list_view": 1,
                },
                {
                    "fieldname": "poliza_flete",
                    "label": "Póliza del flete",
                    "fieldtype": "Link",
                    "options": "Journal Entry",
                    "insert_after": "proveedor_flete",
                    "read_only": 1,
                    "no_copy": 1,
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Landed Cost Taxes and Charges")
