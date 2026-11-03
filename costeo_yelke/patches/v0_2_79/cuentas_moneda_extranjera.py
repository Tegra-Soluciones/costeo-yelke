"""Terceros en moneda extranjera y cuentas bancarias por moneda (api/moneda_terceros.py).

- Bank Account: campo Moneda; las de la empresa toman la de su cuenta contable, las de
  terceros quedan en pesos.
- Supplier / Customer: lista de todas sus cuentas bancarias en la ficha.
- Cuentas por pagar / cobrar en USD por compañía, y los terceros en dólares ligados a ellas.
- Cuentas bancarias de proveedores que estaban en su ficha pero sin Tercero: se ligan.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from costeo_yelke.api.moneda_terceros import TIPOS, cuenta_en_moneda, cuentas_por_moneda


def execute():
    create_custom_fields({
        "Bank Account": [
            {"fieldname": "moneda", "label": "Moneda", "fieldtype": "Link", "options": "Currency",
             "insert_after": "bank", "default": "MXN", "in_list_view": 1, "in_standard_filter": 1,
             "description": "Moneda de la cuenta. En cada pago se usa la del tercero en la moneda del dinero."},
        ],
        "Supplier": [
            {"fieldname": "cuentas_bancarias_html", "label": "Cuentas bancarias", "fieldtype": "HTML",
             "insert_after": "cb_tarjeta"},
        ],
        "Customer": [
            {"fieldname": "sb_cuentas_bancarias_cliente", "label": "Cuentas bancarias del cliente",
             "fieldtype": "Section Break", "insert_after": "default_bank_account"},
            {"fieldname": "cuentas_bancarias_html", "label": "Cuentas bancarias", "fieldtype": "HTML",
             "insert_after": "sb_cuentas_bancarias_cliente"},
        ],
    }, update=True)
    frappe.clear_cache(doctype="Bank Account")

    for ba in frappe.get_all("Bank Account", fields=["name", "is_company_account", "account", "moneda"]):
        if ba.moneda and not ba.is_company_account:
            continue
        moneda = (frappe.db.get_value("Account", ba.account, "account_currency") if ba.is_company_account and ba.account
                  else None) or ba.moneda or "MXN"
        frappe.db.set_value("Bank Account", ba.name, "moneda", moneda, update_modified=False)

    # Cuentas que el proveedor tiene en su ficha pero sin Tercero (no salían en los pagos).
    for s in frappe.get_all("Supplier", filters={"cuenta_bancaria_proveedor": ["is", "set"]},
                            fields=["name", "cuenta_bancaria_proveedor"]):
        ba = frappe.db.get_value("Bank Account", s.cuenta_bancaria_proveedor, ["party_type", "party", "is_company_account"], as_dict=True)
        if ba and not ba.party and not ba.is_company_account:
            frappe.db.set_value("Bank Account", s.cuenta_bancaria_proveedor, {"party_type": "Supplier", "party": s.name},
                                update_modified=False)

    for company in frappe.get_all("Company", pluck="name"):
        for party_type in TIPOS:
            cuenta_en_moneda(company, party_type, "USD")

    # Terceros que ya están en otra moneda: su cuenta por pagar/cobrar en esa moneda.
    for party_type in TIPOS:
        for nombre in frappe.get_all(party_type, filters={"default_currency": ["not in", ["MXN", "", None]]}, pluck="name"):
            doc = frappe.get_doc(party_type, nombre)
            antes = [(r.company, r.account) for r in doc.accounts]
            cuentas_por_moneda(doc)
            if [(r.company, r.account) for r in doc.accounts] != antes:
                doc.flags.ignore_permissions = True
                doc.flags.ignore_mandatory = True
                doc.save()
