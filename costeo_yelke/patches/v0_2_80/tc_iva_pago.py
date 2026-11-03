"""«Tipo de cambio para el IVA» en la entrada de pago (api/cuentas_mx.py): el FIX del DOF
del día anterior al pago (art. 20 CFF) con el que se acredita o traslada el IVA de una
factura en moneda extranjera. Vacío = el tipo de cambio del propio pago."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Payment Entry": [
        {"fieldname": "tc_iva", "label": "Tipo de cambio para el IVA (DOF)", "fieldtype": "Float",
         "precision": "6", "insert_after": "target_exchange_rate", "allow_on_submit": 0,
         "depends_on": "eval:doc.paid_from_account_currency && doc.paid_to_account_currency && doc.paid_from_account_currency != doc.paid_to_account_currency",
         "description": "FIX del DOF del día anterior al pago, para el IVA de facturas en moneda extranjera. Vacío = el tipo de cambio de este pago."},
    ]}, update=True)
    frappe.clear_cache(doctype="Payment Entry")
