"""Banco en pesos de cada compañía (auditoría del 2026-10-29), idempotente:

YELKE TEXTILES solo tenía "Banco en dólares (por definir)" como banco: ERPNext la
proponía en cada cobro y pago (moneda USD contra facturas en pesos). Por compañía:

1. Si no hay ningún banco en su moneda, se crea "Banco en pesos" junto a los demás
   bancos (se puede renombrar después con el nombre real del banco).
2. Ese banco queda como el banco de la compañía si no tenía uno.
3. Las formas de pago de tipo banco (transferencia, cheque, tarjeta, giro) apuntan a
   él en las compañías donde no tenían cuenta.

No da de alta "Cuentas bancarias" (número, CLABE): esos datos los captura Yelke.
"""
import frappe

NOMBRE = "Banco en pesos"


def execute():
    for c in frappe.get_all("Company", fields=["name", "default_currency", "default_bank_account"]):
        try:
            banco = _banco_moneda_local(c)
            if not banco:
                continue
            if not c.default_bank_account or \
                    frappe.db.get_value("Account", c.default_bank_account, "account_currency") != c.default_currency:
                frappe.db.set_value("Company", c.name, "default_bank_account", banco)
            _formas_de_pago(c.name, banco)
        except Exception:
            frappe.log_error(title=f"v0_2_73 cuenta_banco_mxn: {c.name}")
    frappe.clear_cache()


def _banco_moneda_local(c):
    existente = frappe.db.get_value("Account", {"company": c.name, "account_type": "Bank", "is_group": 0, "disabled": 0,
                                                "account_currency": c.default_currency}, "name", order_by="lft asc")
    if existente:
        return existente
    padre = frappe.db.get_value("Account", {"company": c.name, "account_type": "Bank", "is_group": 1},
                                "name", order_by="lft asc")
    if not padre:
        return None
    acc = frappe.get_doc({"doctype": "Account", "company": c.name, "account_name": NOMBRE, "parent_account": padre,
                          "is_group": 0, "root_type": "Asset", "account_type": "Bank",
                          "account_currency": c.default_currency})
    acc.flags.ignore_permissions = True
    acc.insert()
    return acc.name


def _formas_de_pago(company, banco):
    for mop in frappe.get_all("Mode of Payment", filters={"type": "Bank", "enabled": 1}, pluck="name"):
        if frappe.db.exists("Mode of Payment Account", {"parent": mop, "company": company}):
            continue
        doc = frappe.get_doc("Mode of Payment", mop)
        doc.append("accounts", {"company": company, "default_account": banco})
        doc.flags.ignore_permissions = True
        doc.save()
