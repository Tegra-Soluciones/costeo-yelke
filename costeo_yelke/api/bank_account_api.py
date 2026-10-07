"""Cuentas bancarias de proveedores (ver patch v0_2_48).

- validate: limpia espacios y valida que la CLABE tenga 18 dígitos y la tarjeta 15-16.
- on_update: si la cuenta es de un proveedor (party_type = Supplier) y es la marcada
  como default o el proveedor aún no tiene una, queda como su `cuenta_bancaria_proveedor`
  (NO `default_bank_account`: esa es la cuenta de la empresa, ver v0_2_50);
  y si ya era la suya, se refrescan los datos que se muestran en la ficha del proveedor
  (los fetch_from solo se recalculan al guardar el proveedor).
"""
import re

import frappe
from frappe import _


def validar(doc, method=None):
    for campo in ("cuenta_clabe", "numero_tarjeta"):
        if doc.get(campo):
            doc.set(campo, re.sub(r"[\s-]", "", doc.get(campo)))
    if doc.get("cuenta_clabe") and not re.fullmatch(r"\d{18}", doc.cuenta_clabe):
        frappe.throw(_("La cuenta CLABE debe tener 18 dígitos."))
    if doc.get("numero_tarjeta") and not re.fullmatch(r"\d{15,16}", doc.numero_tarjeta):
        frappe.throw(_("El número de tarjeta debe tener 15 o 16 dígitos."))


def sincronizar_proveedor(doc, method=None):
    if doc.party_type != "Supplier" or not doc.party or not frappe.db.exists("Supplier", doc.party):
        return
    actual = frappe.db.get_value("Supplier", doc.party, "cuenta_bancaria_proveedor")
    if doc.is_default or not actual or actual == doc.name:
        frappe.db.set_value("Supplier", doc.party, {
            "cuenta_bancaria_proveedor": doc.name,
            "cb_banco": doc.bank,
            "cb_numero_cuenta": doc.bank_account_no,
            "cb_clabe": doc.get("cuenta_clabe"),
            "cb_tarjeta": doc.get("numero_tarjeta"),
        })
