"""La cuenta bancaria DEL proveedor va en un campo propio (`cuenta_bancaria_proveedor`):
`default_bank_account` es la cuenta de la EMPRESA desde la que se le paga. Los datos de
solo lectura (v0_2_48) pasan a leerse del campo nuevo, en su propia sección."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Supplier": [
        {"fieldname": "sb_cuenta_bancaria_proveedor", "label": "Cuenta bancaria del proveedor",
         "fieldtype": "Section Break", "insert_after": "image"},
        {"fieldname": "cuenta_bancaria_proveedor", "label": "Cuenta bancaria del proveedor", "fieldtype": "Link",
         "options": "Bank Account", "insert_after": "sb_cuenta_bancaria_proveedor",
         "description": "Cuenta donde se le paga. Se da de alta en Cuenta bancaria con Tipo de tercero = Supplier."},
        {"fieldname": "cb_banco", "label": "Banco", "fieldtype": "Data", "read_only": 1,
         "fetch_from": "cuenta_bancaria_proveedor.bank", "insert_after": "cuenta_bancaria_proveedor"},
        {"fieldname": "cb_numero_cuenta", "label": "Número de cuenta", "fieldtype": "Data", "read_only": 1,
         "fetch_from": "cuenta_bancaria_proveedor.bank_account_no", "insert_after": "cb_banco"},
        {"fieldname": "cb_col", "fieldtype": "Column Break", "insert_after": "cb_numero_cuenta"},
        {"fieldname": "cb_clabe", "label": "Cuenta CLABE", "fieldtype": "Data", "read_only": 1,
         "fetch_from": "cuenta_bancaria_proveedor.cuenta_clabe", "insert_after": "cb_col"},
        {"fieldname": "cb_tarjeta", "label": "Número de tarjeta", "fieldtype": "Data", "read_only": 1,
         "fetch_from": "cuenta_bancaria_proveedor.numero_tarjeta", "insert_after": "cb_clabe"},
    ]}, update=True)
    # Si v0_2_48 alcanzó a poner la cuenta DEL proveedor como cuenta de la empresa, se mueve.
    for s in frappe.get_all("Supplier", filters={"default_bank_account": ["is", "set"]},
                            fields=["name", "default_bank_account"]):
        if frappe.db.get_value("Bank Account", s.default_bank_account, "party") == s.name:
            frappe.db.set_value("Supplier", s.name, {"cuenta_bancaria_proveedor": s.default_bank_account,
                                                     "default_bank_account": None}, update_modified=False)
