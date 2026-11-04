"""Proveedores y clientes en moneda extranjera, y sus cuentas bancarias por moneda.

Contabilidad (lo que ERPNext necesita para calcular solo la diferencia cambiaria):
un proveedor en dólares lleva su cuenta por pagar en DÓLARES, por compañía. Así el
saldo de sus facturas se guarda en USD; al pagarlas en pesos al tipo de cambio del
banco, ERPNext compara contra el tipo de cambio de la factura y registra la ganancia o
pérdida cambiaria en la cuenta de la compañía (exchange_gain_loss_account). Con la
cuenta por pagar en pesos (lo de antes) el saldo quedaba fijo en pesos y la diferencia
no se calculaba. Lo mismo para un cliente en dólares con su cuenta por cobrar.

`cuentas_por_moneda` (before_validate de Supplier y Customer) lo deja así solo: según la
moneda por defecto del tercero pone o quita la cuenta en esa moneda en su tabla
«Cuentas». Nunca cambia una compañía donde el tercero ya tiene movimientos en otra
cuenta (ERPNext no deja mezclar monedas en el saldo de un tercero).

Cuentas bancarias del tercero (Bank Account con Tipo de tercero/Tercero): son
informativas — a dónde se le paga o de dónde paga. Llevan `moneda` y en cada pago
(`cuenta_del_tercero_por_moneda`, validate de Payment Entry) se elige la del tercero en
la moneda del DINERO que se mueve: una factura en dólares pagada en pesos va a su cuenta
en pesos.
"""
import frappe
from frappe import _
from frappe.utils import cint

TIPOS = {
    # tipo de cuenta, campo de la compañía con la cuenta por omisión, nombre base
    "Supplier": ("Payable", "default_payable_account", "CUENTAS POR PAGAR PROVEEDORES"),
    "Customer": ("Receivable", "default_receivable_account", "CUENTAS POR COBRAR CLIENTES"),
}


def _moneda_compania(company):
    return frappe.get_cached_value("Company", company, "default_currency")


def cuenta_en_moneda(company, party_type, moneda, crear=True):
    """La cuenta por pagar (o cobrar) de la compañía en esa moneda; si no existe, se crea
    junto a la de por omisión («CUENTAS POR PAGAR PROVEEDORES USD - YT»)."""
    account_type, campo, base = TIPOS[party_type]
    existente = frappe.db.get_value("Account", {"company": company, "account_type": account_type,
                                                "account_currency": moneda, "is_group": 0, "disabled": 0}, "name")
    if existente or not crear:
        return existente
    default = frappe.get_cached_value("Company", company, campo)
    padre = frappe.db.get_value("Account", default, "parent_account") if default else None
    if not padre:
        return None
    acc = frappe.get_doc({"doctype": "Account", "account_name": f"{base} {moneda}", "company": company,
                          "parent_account": padre, "account_type": account_type, "account_currency": moneda})
    acc.flags.ignore_permissions = True
    acc.insert()
    return acc.name


def _movimientos_en_otra(party_type, party, company, cuenta):
    return frappe.db.exists("GL Entry", {"party_type": party_type, "party": party, "company": company,
                                         "is_cancelled": 0, "account": ["!=", cuenta]})


def cuentas_por_moneda(doc, method=None):
    """before_validate de Supplier / Customer: su cuenta por pagar/cobrar en la moneda del tercero."""
    if doc.doctype not in TIPOS or not doc.name:
        return
    moneda = doc.get("default_currency")
    for company in frappe.get_all("Company", pluck="name"):
        propia = _moneda_compania(company)
        fila = next((r for r in doc.get("accounts") or [] if r.company == company), None)
        if moneda and moneda != propia:
            cuenta = cuenta_en_moneda(company, doc.doctype, moneda)
            if not cuenta or (fila and fila.account == cuenta):
                continue
            if _movimientos_en_otra(doc.doctype, doc.name, company, cuenta):
                frappe.msgprint(_("{0} ya tiene movimientos en {1}: su cuenta en {2} no se cambió en esa compañía.")
                                .format(doc.name, company, moneda), indicator="orange", alert=True)
                continue
            if fila:
                fila.account = cuenta
            else:
                doc.append("accounts", {"company": company, "account": cuenta})
        elif fila and fila.account:
            # Regresó a la moneda de la compañía: fuera la cuenta en dólares (vuelve la de
            # por omisión), si todavía no tiene movimientos ahí.
            if frappe.db.get_value("Account", fila.account, "account_currency") != propia \
                    and not frappe.db.exists("GL Entry", {"party_type": doc.doctype, "party": doc.name,
                                                          "company": company, "is_cancelled": 0}):
                doc.remove(fila)


def documento_en_moneda_del_proveedor(doc, method=None):
    """before_validate de OC / presupuesto / recepción / factura de compra en borrador:
    con un proveedor cuya cuenta por pagar está en otra moneda (dólares), el documento
    va en esa moneda -- ERPNext no deja otra («sólo puede realizarse con la divisa»).
    Los documentos nacen en pesos (el mapeo desde la solicitud de material no mira al
    proveedor); aquí se pasan a su moneda con el tipo de cambio del día, conservando
    el valor de cada precio."""
    if doc.docstatus != 0 or not doc.get("supplier") or not doc.get("company"):
        return
    from erpnext.accounts.party import get_party_account_currency

    moneda = get_party_account_currency("Supplier", doc.supplier, doc.company)
    if not moneda or moneda == doc.get("currency") or moneda == _moneda_compania(doc.company):
        return
    from costeo_yelke.api.costeo_api import _aplicar_moneda

    _aplicar_moneda(doc, moneda)


def moneda_cuenta_bancaria(doc, method=None):
    """validate de Bank Account: la de la empresa toma la moneda de su cuenta contable;
    la de un tercero, la que se capture (pesos si nadie dice otra)."""
    if not doc.meta.has_field("moneda"):
        return
    if cint(doc.get("is_company_account")) and doc.get("account"):
        doc.moneda = frappe.db.get_value("Account", doc.account, "account_currency") or doc.moneda
    if not doc.get("moneda"):
        doc.moneda = (_moneda_compania(doc.company) if doc.get("company") else None) or "MXN"


def cuenta_del_tercero_por_moneda(doc, method=None):
    """validate de Payment Entry: «Cuenta bancaria del tercero» = la suya en la moneda del
    dinero (lo que sale del banco al pagar, lo que entra al cobrar). La predeterminada
    gana entre varias de la misma moneda. Si no tiene ninguna en esa moneda, se deja."""
    if doc.get("party_type") not in TIPOS or not doc.get("party") or not frappe.db.has_column("Bank Account", "moneda"):
        return
    moneda = doc.get("paid_from_account_currency") if doc.payment_type == "Pay" else doc.get("paid_to_account_currency")
    if not moneda:
        return
    cuentas = frappe.get_all("Bank Account", filters={"party_type": doc.party_type, "party": doc.party, "disabled": 0},
                             fields=["name", "moneda", "is_default"], order_by="is_default desc, creation asc")
    actual = next((c for c in cuentas if c.name == doc.get("party_bank_account")), None)
    if actual and actual.moneda == moneda:
        return
    en_moneda = [c for c in cuentas if c.moneda == moneda]
    if en_moneda:
        doc.party_bank_account = en_moneda[0].name


@frappe.whitelist()
def get_cuentas_bancarias(party_type: str, party: str) -> list:
    """Para la ficha del proveedor/cliente: todas sus cuentas bancarias."""
    if party_type not in TIPOS or not frappe.has_permission(party_type, "read", party):
        return []
    campos = ["name", "account_name", "bank", "bank_account_no", "is_default", "disabled"]
    for extra in ("moneda", "cuenta_clabe", "numero_tarjeta"):
        if frappe.db.has_column("Bank Account", extra):
            campos.append(extra)
    return frappe.get_all("Bank Account", filters={"party_type": party_type, "party": party}, fields=campos,
                          order_by="disabled asc, is_default desc, creation asc")
