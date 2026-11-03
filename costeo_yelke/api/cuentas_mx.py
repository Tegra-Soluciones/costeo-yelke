"""IVA de la operación en México, en base a flujo de efectivo.

Para el SAT el IVA cuenta cuando se paga (compras) o se cobra (ventas), no cuando se
factura. Cada compañía lleva cuatro cuentas:

    IVA ACREDITABLE PENDIENTE DE PAGO  (activo)  -- factura de compra registrada
    IVA ACREDITABLE PAGADO             (activo)  -- ya se le pagó al proveedor
    IVA TRASLADADO NO COBRADO          (pasivo)  -- factura de venta registrada
    IVA TRASLADADO COBRADO             (pasivo)  -- el cliente ya pagó

Todo es automático:

- La cuenta del documento la pone `corregir_cuenta_iva` al validar cualquier compra
  o venta: el renglón de IVA va a la PENDIENTE de su lado sin importar qué cuenta de
  IVA traiga (la genérica "IVA", la del otro lado, una copiada de una orden vieja).
- Al pagar o cobrar, `sincronizar_iva` pasa a PAGADO / COBRADO la parte del IVA que
  corresponde a lo pagado de cada factura, con una póliza ligada a la factura. El
  cálculo es por estado (lo pagado según el Payment Ledger contra lo ya pasado), así
  que cubre pagos parciales, cancelaciones, anticipos y conciliaciones: cada vez
  deja la diferencia, nunca suma dos veces.

Las facturas de antes, con la cuenta genérica, se pasan igual al pagarse: su IVA sale
de la genérica. Las retenciones (4% de fletes) se quedan en su cuenta.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

ACRED_PENDIENTE = "IVA ACREDITABLE PENDIENTE DE PAGO"
ACRED_PAGADO = "IVA ACREDITABLE PAGADO"
TRAS_NO_COBRADO = "IVA TRASLADADO NO COBRADO"
TRAS_COBRADO = "IVA TRASLADADO COBRADO"
GENERICA = "IVA"
CXC_CLIENTES = "CUENTAS POR COBRAR CLIENTES"

# Cuentas de IVA que un renglón puede traer y que se corrigen a la pendiente de su
# lado (las dos primeras son de catálogos que ya existían; las retenciones no).
FAMILIA_IVA = {GENERICA, "IVA ACREDITABLE", "IVA TRASLADADO", "IVA ACREDITABLE o PAGADO A PROVEEDORES",
               "IVA POR TRASLADAR o COBRADO", ACRED_PENDIENTE, ACRED_PAGADO, TRAS_NO_COBRADO, TRAS_COBRADO}

COMPRAS = ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice")
VENTAS = ("Quotation", "Sales Order", "Delivery Note", "Sales Invoice")
FACTURAS = ("Purchase Invoice", "Sales Invoice")


def cuenta(company, nombre):
    return frappe.db.get_value("Account", {"company": company, "account_name": nombre, "is_group": 0})


# ── La cuenta de cada documento ──────────────────────────────────────────────
def corregir_cuenta_iva(doc, method=None):
    """doc_events validate (compras y ventas): el IVA va a la cuenta PENDIENTE de su
    lado. Solo cambia la cuenta del renglón; importes y tasas quedan igual."""
    if not doc.get("company") or not doc.get("taxes"):
        return
    destino = cuenta(doc.company, ACRED_PENDIENTE if doc.doctype in COMPRAS else TRAS_NO_COBRADO)
    if not destino:
        return
    for t in doc.taxes:
        if t.account_head and t.account_head != destino and \
                frappe.get_cached_value("Account", t.account_head, "account_name") in FAMILIA_IVA:
            t.account_head = destino


# ── Pagado / cobrado ─────────────────────────────────────────────────────────
def _lado(doctype):
    """(pendiente, realizado, signo): signo +1 si la cuenta pendiente es deudora."""
    if doctype == "Purchase Invoice":
        return ACRED_PENDIENTE, ACRED_PAGADO, 1
    return TRAS_NO_COBRADO, TRAS_COBRADO, -1


def _iva_de_factura(doctype, name, company, signo):
    """IVA registrado por la factura y la cuenta donde quedó (la pendiente o, en una
    factura de antes, la genérica)."""
    for nombre in (_lado(doctype)[0], GENERICA):
        acc = cuenta(company, nombre)
        if not acc:
            continue
        monto = signo * flt(frappe.db.sql(
            """select sum(debit - credit) from `tabGL Entry` where is_cancelled = 0 and account = %s
               and voucher_type = %s and voucher_no = %s""", (acc, doctype, name))[0][0])
        if abs(monto) >= 0.005:
            return round(monto, 2), acc
    return 0.0, None


def _fraccion_pagada(doctype, name):
    """Qué parte de la factura ya se pagó/cobró, según el Payment Ledger: pagos y
    pólizas aplicados a ella (no las notas de crédito, que no son pago)."""
    filas = frappe.get_all("Payment Ledger Entry", filters={"against_voucher_type": doctype, "against_voucher_no": name,
                                                            "delinked": 0},
                           fields=["voucher_type", "voucher_no", "amount_in_account_currency", "posting_date"])
    total = sum(flt(f.amount_in_account_currency) for f in filas if f.voucher_no == name and f.voucher_type == doctype)
    pagos = [f for f in filas if f.voucher_type in ("Payment Entry", "Journal Entry") and f.voucher_no != name]
    if not total:
        return 0.0, None
    fraccion = -sum(flt(f.amount_in_account_currency) for f in pagos) / total
    ultima = max((getdate(f.posting_date) for f in pagos), default=None)
    return min(max(fraccion, 0.0), 1.0), ultima


def _ya_realizado(doctype, name, realizado, signo):
    if not realizado:
        return 0.0
    return round(signo * flt(frappe.db.sql(
        """select sum(g.debit - g.credit) from `tabGL Entry` g join `tabJournal Entry` j on j.name = g.voucher_no
           where g.is_cancelled = 0 and g.voucher_type = 'Journal Entry' and g.account = %s
           and j.docstatus = 1 and j.iva_factura_doctype = %s and j.iva_factura = %s""",
        (realizado, doctype, name))[0][0]), 2)


def _tc_fiscal_del_pago(voucher_type, voucher_no, tc_factura):
    """Tipo de cambio con el que se acredita (o traslada) el IVA de ese pago: el «Tipo de
    cambio para el IVA» capturado en el pago (el FIX del DOF del día anterior, art. 20
    CFF) o, si se dejó vacío, el del propio pago. Una póliza manual, el de su renglón."""
    if voucher_type == "Payment Entry":
        pe = frappe.db.get_value("Payment Entry", voucher_no, ["payment_type", "source_exchange_rate", "target_exchange_rate",
                                                               "tc_iva"] if frappe.db.has_column("Payment Entry", "tc_iva")
                                 else ["payment_type", "source_exchange_rate", "target_exchange_rate"], as_dict=True)
        if pe:
            # El lado del tercero: a él se le paga (paid_to) o él paga (paid_from).
            return flt(pe.get("tc_iva")) or flt(pe.target_exchange_rate if pe.payment_type == "Pay" else pe.source_exchange_rate) \
                or tc_factura
    return tc_factura


def _iva_al_tc_de_los_pagos(doctype, name, iva):
    """Factura en moneda extranjera: el IVA de lo pagado, en pesos, al tipo de cambio de
    CADA pago (art. 5 LIVA: se acredita lo efectivamente pagado, convertido a la fecha
    del pago) en lugar del de la factura. None si la factura es en pesos."""
    inv = frappe.db.get_value(doctype, name, ["currency", "conversion_rate", "company"], as_dict=True)
    if not inv or inv.currency == frappe.get_cached_value("Company", inv.company, "default_currency") \
            or not flt(inv.conversion_rate):
        return None
    iva_moneda = iva / flt(inv.conversion_rate)
    filas = frappe.get_all("Payment Ledger Entry", filters={"against_voucher_type": doctype, "against_voucher_no": name,
                                                            "delinked": 0},
                           fields=["voucher_type", "voucher_no", "amount_in_account_currency"])
    total = sum(flt(f.amount_in_account_currency) for f in filas if f.voucher_no == name and f.voucher_type == doctype)
    if not total:
        return None
    por_pago = {}
    for f in filas:
        if f.voucher_type in ("Payment Entry", "Journal Entry") and f.voucher_no != name:
            por_pago[(f.voucher_type, f.voucher_no)] = por_pago.get((f.voucher_type, f.voucher_no), 0.0) + flt(f.amount_in_account_currency)
    monto = 0.0
    for (vt, vn), importe in por_pago.items():
        fraccion = -importe / total
        if abs(fraccion) < 1e-9:
            continue  # la póliza de diferencia cambiaria de ERPNext: no es pago
        monto += iva_moneda * fraccion * _tc_fiscal_del_pago(vt, vn, flt(inv.conversion_rate))
    return round(monto, 2)


def _ya_salio(doctype, name, origen, signo):
    """Lo que ya salió de la cuenta pendiente (o genérica) por las pólizas de IVA."""
    if not origen:
        return 0.0
    return round(-signo * flt(frappe.db.sql(
        """select sum(g.debit - g.credit) from `tabGL Entry` g join `tabJournal Entry` j on j.name = g.voucher_no
           where g.is_cancelled = 0 and g.voucher_type = 'Journal Entry' and g.account = %s
           and j.docstatus = 1 and j.iva_factura_doctype = %s and j.iva_factura = %s""",
        (origen, doctype, name))[0][0]), 2)


def sincronizar_iva(doctype, name):
    """Deja en PAGADO / COBRADO exactamente la parte del IVA de la factura que ya se
    pagó; si sobra o falta (pago nuevo, pago cancelado), una póliza con la diferencia.

    Factura en moneda extranjera: de la PENDIENTE sale lo que registró la factura (a su
    tipo de cambio) y a PAGADO / COBRADO entra el IVA al tipo de cambio de cada pago
    (_iva_al_tc_de_los_pagos); la diferencia va a la cuenta de diferencia cambiaria de
    la compañía. En pesos las dos cantidades son la misma, como siempre."""
    if doctype not in FACTURAS or not frappe.db.has_column("Journal Entry", "iva_factura"):
        return
    inv = frappe.db.get_value(doctype, name, ["docstatus", "company", "is_return"], as_dict=True)
    if not inv or inv.is_return:
        return
    pendiente_nombre, realizado_nombre, signo = _lado(doctype)
    realizado = cuenta(inv.company, realizado_nombre)
    if not realizado:
        return
    iva, origen = _iva_de_factura(doctype, name, inv.company, signo)
    if not origen:
        origen = cuenta(inv.company, pendiente_nombre)
    fraccion, fecha = _fraccion_pagada(doctype, name) if inv.docstatus == 1 else (0.0, None)
    objetivo = iva if fraccion >= 0.99995 else round(iva * fraccion, 2)
    objetivo_real = objetivo
    if inv.docstatus == 1 and fraccion > 0:
        fiscal = _iva_al_tc_de_los_pagos(doctype, name, iva)
        if fiscal is not None:
            objetivo_real = fiscal
    dif_real = round(objetivo_real - _ya_realizado(doctype, name, realizado, signo), 2)
    dif_orig = round(objetivo - _ya_salio(doctype, name, origen, signo), 2)
    if abs(dif_real) < 0.01 and abs(dif_orig) < 0.01:
        return
    # Compras (activo): cargo a PAGADO, abono a PENDIENTE. Ventas (pasivo): al revés.
    # Con diferencias negativas (pago cancelado) se invierte solo. Lo que no cuadra entre
    # las dos es tipo de cambio: a la cuenta de diferencia cambiaria.
    cargo_real, abono_orig = dif_real * signo, dif_orig * signo
    renglones = [
        {"account": realizado, "debit_in_account_currency": max(cargo_real, 0), "credit_in_account_currency": max(-cargo_real, 0)},
        {"account": origen, "debit_in_account_currency": max(-abono_orig, 0), "credit_in_account_currency": max(abono_orig, 0)},
    ]
    cambiaria = round(abono_orig - cargo_real, 2)
    if abs(cambiaria) >= 0.01:
        cta = frappe.get_cached_value("Company", inv.company, "exchange_gain_loss_account")
        if not cta:
            frappe.throw(_("Falta la cuenta de diferencia cambiaria de {0}.").format(inv.company))
        renglones.append({"account": cta, "debit_in_account_currency": max(cambiaria, 0),
                          "credit_in_account_currency": max(-cambiaria, 0)})
    renglones = [r for r in renglones if r["debit_in_account_currency"] or r["credit_in_account_currency"]]
    je = frappe.get_doc({
        "doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": inv.company,
        "posting_date": fecha if ((dif_real > 0 or dif_orig > 0) and fecha) else nowdate(),
        "iva_factura_doctype": doctype, "iva_factura": name,
        "user_remark": _("IVA {0} -- {1} {2} ({3:.2f}% pagado)").format(
            _("efectivamente pagado") if doctype == "Purchase Invoice" else _("efectivamente cobrado"),
            _(doctype), name, fraccion * 100),
        "accounts": renglones,
    })
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()


def _facturas_de_pago(doc):
    if doc.doctype == "Payment Entry":
        return {(r.reference_doctype, r.reference_name) for r in doc.get("references") or []
                if r.reference_doctype in FACTURAS}
    if doc.doctype == "Journal Entry" and not doc.get("iva_factura"):
        return {(r.reference_type, r.reference_name) for r in doc.get("accounts") or []
                if r.reference_type in FACTURAS and r.reference_name}
    return set()


def al_mover_pago(doc, method=None):
    """doc_events on_submit / on_cancel de Payment Entry y Journal Entry."""
    for dt, name in _facturas_de_pago(doc):
        sincronizar_iva(dt, name)


def al_mover_factura(doc, method=None):
    """doc_events on_submit / on_cancel de las facturas: anticipos aplicados al
    validarla, o devolver todo a pendiente si se cancela."""
    if method == "on_cancel":
        # Las pólizas de IVA de esta factura se cancelan con ella.
        for je in frappe.get_all("Journal Entry", filters={"docstatus": 1, "iva_factura_doctype": doc.doctype,
                                                           "iva_factura": doc.name}, pluck="name"):
            j = frappe.get_doc("Journal Entry", je)
            j.flags.ignore_permissions = True
            j.cancel()
        return
    sincronizar_iva(doc.doctype, doc.name)


def revisar_iva_pendiente():
    """Cada hora: lo que se concilia con la herramienta de conciliación de pagos no
    dispara eventos, así que aquí se emparejan las facturas que lo necesiten."""
    if not frappe.db.has_column("Journal Entry", "iva_factura"):
        return
    for dt in FACTURAS:
        for name in frappe.get_all(dt, filters={"docstatus": 1, "is_return": 0,
                                                "modified": [">=", frappe.utils.add_days(nowdate(), -3)]},
                                   pluck="name"):
            try:
                sincronizar_iva(dt, name)
            except Exception:
                frappe.log_error(title=f"IVA pagado/cobrado: {dt} {name}")
