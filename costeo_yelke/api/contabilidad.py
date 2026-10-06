"""Cierre contable del ciclo de producción subcontratada (hooks de documentos).

Nace de la auditoría de YELKE TEXTILES (2026-10-01): el inventario cuadraba al centavo
pero el ciclo no se cerraba en contabilidad. Aquí vive todo lo que corre SOLO al
validar/cancelar documentos nativos (doc_events en hooks.py), sin pasar por el SPA:

- Recibo de taller validado -> su Recepción de servicio nativa (cierra la OC de
  maquila y es la base para facturarle al maquilero) + pólizas de flete + cierre de
  producción si ya se terminó todo.
- Fletes capturados como "costos adicionales" (transferencia al taller / recibo del
  taller): ERPNext los capitaliza al inventario abonando "Gastos incluidos en la
  valoración", pero nadie registraba a QUIÉN se le debe -- aquí se genera la póliza
  contra el proveedor del flete.
- Freno a recepciones que exceden la OC y a borrar documentos cancelados (folios).
"""

import frappe
from frappe import _
from frappe.utils import flt

# Tolerancia de recepción contra la OC. La tolerancia grande del artículo (100%,
# ver item_api.ALLOWANCE_PAQUETE_COMPLETO) existe solo para que la OC pueda pedir el
# paquete completo contra la solicitud de material; recibir más que la OC no.
TOLERANCIA_RECEPCION_PCT = 5


# ─────────────────────────────────────────────────────────────────────────────
# Recibo de taller (Subcontracting Receipt)
# ─────────────────────────────────────────────────────────────────────────────

def _po_de_scr(doc):
    return next((it.purchase_order for it in doc.items if it.get("purchase_order")), None)


def _costeo_de_scr(doc):
    po = _po_de_scr(doc)
    if not po or not frappe.db.has_column("Purchase Order", "costeo"):
        return None
    return frappe.db.get_value("Purchase Order", po, "costeo")


def asegurar_recepcion_servicio(scr_name):
    """Recepción de compra nativa del SERVICIO de un recibo de taller ya validado
    (mapeo de ERPNext `make_purchase_receipt`). Es lo que marca la OC de maquila como
    recibida y lo que después se factura. Idempotente: si ya existe, la regresa."""
    existente = frappe.db.get_value(
        "Purchase Receipt", {"subcontracting_receipt": scr_name, "docstatus": ["<", 2]}, ["name", "docstatus"],
        as_dict=True,
    )
    if existente:
        if existente.docstatus == 0:
            pr = frappe.get_doc("Purchase Receipt", existente.name)
            pr.flags.ignore_permissions = True
            pr.submit()
        return existente.name

    from erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt import (
        make_purchase_receipt,
    )
    pr = make_purchase_receipt(scr_name)
    if not pr.get("items"):
        return None
    pr.flags.ignore_permissions = True
    pr.insert()
    pr.submit()
    return pr.name


def despues_de_validar_recibo_taller(doc, method=None):
    """doc_events: Subcontracting Receipt on_submit."""
    if doc.get("is_return"):
        return
    crear_polizas_flete(doc)
    try:
        asegurar_recepcion_servicio(doc.name)
    except Exception:
        # No se frena la recepción del trabajo terminado por esto: la facturación de la
        # maquila vuelve a intentar crearla (ver costeo_api.crear_factura_compra).
        frappe.log_error(title="costeo_yelke: no se pudo crear la recepción de servicio",
                         message=f"Recibo {doc.name}\n\n{frappe.get_traceback()}")
        frappe.msgprint(_("El recibo quedó validado, pero no se pudo crear su recepción de servicio; "
                          "se reintentará al facturar la maquila."), indicator="orange", alert=True)
    costeo = _costeo_de_scr(doc)
    if costeo:
        cerrar_produccion_si_completa(costeo)


def cuenta_servicio_recibo_taller(doc, method=None):
    """doc_events: Subcontracting Receipt validate -- cuenta a la que se abona la maquila.

    ERPNext la resuelve con ``get_item_defaults(...) or get_item_group_defaults(...)``,
    pero get_item_defaults SIEMPRE regresa un dict con datos del artículo (aunque no
    tenga cuenta para la compañía), así que el grupo de artículo nunca se consulta y
    cae a la cuenta de gastos default de la compañía (Costo de ventas). La factura del
    maquilero, en cambio, sí carga a la cuenta del grupo Servicios ("Gastos incluidos
    en la valoración"): el recibo abonaba una cuenta y la factura cargaba otra, y
    ninguna de las dos quedaba en cero (costo de ventas subestimado por toda la maquila).

    Aquí se resuelve como ERPNext pretende: artículo -> grupo -> marca, cada uno solo
    si de verdad trae cuenta para la compañía. Sin ninguna, se queda lo que puso ERPNext."""
    if doc.get("is_return") or doc.docstatus == 2:
        return
    from erpnext.setup.doctype.brand.brand import get_brand_defaults
    from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
    from erpnext.stock.doctype.item.item import get_item_defaults

    cache = {}
    for row in doc.get("items") or []:
        if not row.get("purchase_order_item"):
            continue
        servicio = frappe.db.get_value("Purchase Order Item", row.purchase_order_item, "item_code")
        if not servicio:
            continue
        if servicio not in cache:
            cache[servicio] = next((
                d.get("expense_account") for d in (
                    get_item_defaults(servicio, doc.company),
                    get_item_group_defaults(servicio, doc.company),
                    get_brand_defaults(servicio, doc.company),
                ) if d and d.get("expense_account")
            ), None)
        cuenta = cache[servicio]
        if cuenta and row.service_expense_account != cuenta:
            row.service_expense_account = cuenta


def al_cancelar_recibo_taller(doc, method=None):
    """doc_events: Subcontracting Receipt on_cancel -- deshace lo que generó al validar."""
    for pr in frappe.get_all("Purchase Receipt", filters={"subcontracting_receipt": doc.name, "docstatus": 1},
                             pluck="name"):
        d = frappe.get_doc("Purchase Receipt", pr)
        d.flags.ignore_permissions = True
        d.cancel()
    cancelar_polizas_flete(doc)


# ─────────────────────────────────────────────────────────────────────────────
# Pólizas de flete (costos adicionales con proveedor)
# ─────────────────────────────────────────────────────────────────────────────

def _aplica_flete(doc):
    if doc.doctype == "Stock Entry":
        return doc.purpose == "Send to Subcontractor"
    return doc.doctype == "Subcontracting Receipt" and not doc.get("is_return")


def validar_proveedor_flete(doc, method=None):
    """doc_events before_submit: todo costo adicional con monto debe decir a quién se
    le paga -- si no, el flete se capitaliza al inventario y la deuda nunca se registra."""
    if not _aplica_flete(doc) or not frappe.db.has_column("Landed Cost Taxes and Charges", "proveedor_flete"):
        return
    for r in doc.get("additional_costs") or []:
        if flt(r.amount) > 0 and not r.get("proveedor_flete"):
            frappe.throw(_("Costo adicional '{0}' de {1}: indica el proveedor al que se le paga (transportista).")
                         .format(r.description or "", frappe.format(r.amount, {"fieldtype": "Currency"})))


def crear_polizas_flete(doc, method=None):
    """Una póliza por fila de costo adicional con monto y proveedor: cargo a la MISMA
    cuenta que el documento abonó al capitalizar el flete (expense_account de la fila,
    normalmente 'Gastos incluidos en la valoración') contra la cuenta por pagar del
    proveedor. Así esa cuenta puente queda en cero y la deuda queda registrada."""
    if not _aplica_flete(doc) or not frappe.db.has_column("Landed Cost Taxes and Charges", "proveedor_flete"):
        return
    from costeo_yelke.api.costeo_api import _payable_account_para_proveedor

    cost_center = frappe.get_cached_value("Company", doc.company, "cost_center")
    for r in doc.get("additional_costs") or []:
        monto = flt(r.get("base_amount") or r.amount)
        if monto <= 0 or not r.get("proveedor_flete") or r.get("poliza_flete"):
            continue
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = doc.company
        je.posting_date = doc.posting_date
        je.user_remark = _("Flete '{0}' — {1} {2}").format(r.description or "", _(doc.doctype), doc.name)
        je.append("accounts", {
            "account": r.expense_account,
            "debit_in_account_currency": monto,
            "cost_center": cost_center,
        })
        je.append("accounts", {
            "account": _payable_account_para_proveedor(doc.company, r.proveedor_flete),
            "credit_in_account_currency": monto,
            "party_type": "Supplier",
            "party": r.proveedor_flete,
            "cost_center": cost_center,
        })
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()
        frappe.db.set_value("Landed Cost Taxes and Charges", r.name, "poliza_flete", je.name, update_modified=False)


def cancelar_polizas_flete(doc, method=None):
    if not frappe.db.has_column("Landed Cost Taxes and Charges", "poliza_flete"):
        return
    for r in doc.get("additional_costs") or []:
        if r.get("poliza_flete") and frappe.db.get_value("Journal Entry", r.poliza_flete, "docstatus") == 1:
            je = frappe.get_doc("Journal Entry", r.poliza_flete)
            je.flags.ignore_permissions = True
            je.cancel()


def al_validar_transferencia(doc, method=None):
    """doc_events: Stock Entry on_submit (solo Send to Subcontractor)."""
    crear_polizas_flete(doc)


def al_cancelar_transferencia(doc, method=None):
    """doc_events: Stock Entry on_cancel."""
    if _aplica_flete(doc):
        cancelar_polizas_flete(doc)


# ─────────────────────────────────────────────────────────────────────────────
# Cierre de producción
# ─────────────────────────────────────────────────────────────────────────────

def cerrar_produccion_si_completa(costeo):
    """Con TODA la maquila del costeo recibida: cierra su Production Plan (libera la
    reserva de materia prima que ERPNext le sigue apartando, porque en subcontratación
    nunca se crean Work Orders que la consuman) y detiene sus Solicitudes de Material
    abiertas (libera el 'pendiente de pedir' que queda cuando un lote compra el
    paquete completo y el siguiente compra de menos). Idempotente."""
    from costeo_yelke.api.costeo_api import produccion_completa

    if not produccion_completa(costeo).get("complete"):
        return False
    cerrado = False
    if frappe.db.has_column("Production Plan", "costeo"):
        for pp in frappe.get_all("Production Plan",
                                 filters={"costeo": costeo, "docstatus": 1, "status": ["not in", ["Closed", "Completed"]]},
                                 pluck="name"):
            frappe.get_doc("Production Plan", pp).set_status(close=True)
            cerrado = True
    if frappe.db.has_column("Material Request", "costeo"):
        for mr in frappe.get_all("Material Request",
                                 filters={"costeo": costeo, "docstatus": 1,
                                          "status": ["in", ["Pending", "Partially Ordered", "Partially Received"]]},
                                 pluck="name"):
            frappe.get_doc("Material Request", mr).update_status("Stopped")
            cerrado = True
    return cerrado


# ─────────────────────────────────────────────────────────────────────────────
# Recepciones de compra
# ─────────────────────────────────────────────────────────────────────────────

def validar_recepcion_contra_oc(doc, method=None):
    """doc_events: Purchase Receipt validate. Lo recibido (otras recepciones + esta) no
    puede pasar de lo pedido en la OC más una tolerancia chica -- solo para OC del
    flujo de costeo. Las recepciones de servicio que nacen de un recibo de taller ya
    vienen exactas del mapeo nativo."""
    if doc.get("is_return") or doc.get("subcontracting_receipt"):
        return
    if not frappe.db.has_column("Purchase Order", "costeo"):
        return
    por_fila = {}
    for it in doc.items:
        if it.get("purchase_order_item") and it.get("purchase_order"):
            por_fila.setdefault(it.purchase_order_item, []).append(it)
    for po_item, filas in por_fila.items():
        po = filas[0].purchase_order
        if not frappe.db.get_value("Purchase Order", po, "costeo"):
            continue
        pedido = flt(frappe.db.get_value("Purchase Order Item", po_item, "stock_qty"))
        otras = flt(frappe.db.sql(
            """select sum(stock_qty) from `tabPurchase Receipt Item`
               where purchase_order_item=%s and docstatus=1 and parent!=%s""",
            (po_item, doc.name or ""),
        )[0][0])
        esta = sum(flt(f.stock_qty or (flt(f.qty) * flt(f.conversion_factor or 1))) for f in filas)
        limite = pedido * (1 + TOLERANCIA_RECEPCION_PCT / 100.0)
        if otras + esta > limite + 0.0001:
            frappe.throw(_("{0}: se recibirían {1} pero la OC {2} pide {3} (tolerancia {4}%).").format(
                filas[0].item_code, round(otras + esta, 3), po, round(pedido, 3), TOLERANCIA_RECEPCION_PCT))


# ─────────────────────────────────────────────────────────────────────────────
# Folios
# ─────────────────────────────────────────────────────────────────────────────

def bloquear_borrado_cancelado(doc, method=None):
    """doc_events on_trash: un documento contable/de inventario cancelado NO se borra.
    Si se borra el último de su serie, Frappe libera el folio y el siguiente documento
    lo reutiliza, quedando dos documentos distintos con el mismo número en el libro de
    inventario. Scripts de limpieza de pruebas pueden saltarlo con
    frappe.flags.permitir_borrar_cancelados = True."""
    if doc.docstatus == 2 and not frappe.flags.get("permitir_borrar_cancelados"):
        frappe.throw(_("{0} {1} está cancelado: no se borra para no reutilizar su folio.")
                     .format(_(doc.doctype), doc.name))
