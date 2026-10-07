"""Cuenta bancaria de proveedores: CLABE y número de tarjeta en Bank Account, y los
datos de la cuenta por defecto del proveedor a la vista en su ficha (solo lectura,
traídos de `default_bank_account`). La sincronización vive en api/bank_account_api.py."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Bank Account": [
            {"fieldname": "cuenta_clabe", "label": "Cuenta CLABE", "fieldtype": "Data", "length": 18,
             "insert_after": "bank_account_no", "description": "18 dígitos"},
            {"fieldname": "numero_tarjeta", "label": "Número de tarjeta", "fieldtype": "Data",
             "insert_after": "cuenta_clabe"},
        ],
        "Supplier": [
            {"fieldname": "cb_banco", "label": "Banco", "fieldtype": "Data", "read_only": 1,
             "fetch_from": "default_bank_account.bank", "insert_after": "default_bank_account"},
            {"fieldname": "cb_numero_cuenta", "label": "Número de cuenta", "fieldtype": "Data", "read_only": 1,
             "fetch_from": "default_bank_account.bank_account_no", "insert_after": "cb_banco"},
            {"fieldname": "cb_clabe", "label": "Cuenta CLABE", "fieldtype": "Data", "read_only": 1,
             "fetch_from": "default_bank_account.cuenta_clabe", "insert_after": "cb_numero_cuenta"},
            {"fieldname": "cb_tarjeta", "label": "Número de tarjeta", "fieldtype": "Data", "read_only": 1,
             "fetch_from": "default_bank_account.numero_tarjeta", "insert_after": "cb_clabe"},
        ],
    }, update=True)
