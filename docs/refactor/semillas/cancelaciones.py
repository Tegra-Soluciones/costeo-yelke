import frappe; frappe.init(site="sandbox.local", sites_path="/Users/trabajo/Trabajo/frappe-bench-v15/sites"); frappe.connect()
import json, frappe
from costeo_yelke.api import costeo_api as A
frappe.set_user("Administrator")
s = json.load(open("/private/tmp/claude-502/-Users-trabajo-Documents-frappe-bench-v15-apps-costeo-yelke/455962b2-ce0b-409b-b631-99f79fded5f9/scratchpad/e2e_state.json"))
def caso(nombre, fn):
    frappe.db.savepoint("c")
    try:
        r = fn()
        print("·", nombre, "->", r)
    except Exception as e:
        print("·", nombre, "BLOQUEÓ ->", type(e).__name__, str(e)[:220])
    try: frappe.db.rollback(save_point="c")
    except Exception as e: print("   !! savepoint perdido (hubo commit interno):", e); 
    frappe.local.message_log = []

def cancelar_dn():
    dn = s["dn"][0]
    pi = frappe.db.get_value("Delivery Note", dn, "flete_factura")
    ds_pi = frappe.db.get_value("Purchase Invoice", pi, "docstatus")
    # la factura de venta está validada: ERPNext no deja cancelar la remisión antes que la factura
    A.cancelar_documento("Delivery Note", dn)
    return dict(dn=frappe.db.get_value("Delivery Note", dn, "docstatus"), pi_flete=pi, pi_antes=ds_pi, pi_existe=frappe.db.exists("Purchase Invoice", pi))
caso("cancelar remisión con factura de venta validada", cancelar_dn)

def cancelar_si_y_dn():
    si = s["si"]
    je = frappe.db.get_value("Sales Invoice", si, "overhead_journal_entry")
    A.cancelar_documento("Sales Invoice", si)
    je_ds = frappe.db.get_value("Journal Entry", je, "docstatus") if je else None
    dn = s["dn"][0]
    pi = frappe.db.get_value("Delivery Note", dn, "flete_factura")
    A.cancelar_documento("Delivery Note", dn)
    return dict(si=frappe.db.get_value("Sales Invoice", si, "docstatus"), overhead_je=je_ds,
                dn=frappe.db.get_value("Delivery Note", dn, "docstatus"), pi_flete_borrador_borrada=not frappe.db.exists("Purchase Invoice", pi),
                ov=frappe.db.get_value("Sales Order", s["so"], ["per_delivered", "per_billed"]),
                costeo=frappe.db.get_value("Costeo", s["costeo"], "costeo_status"))
caso("cancelar factura de venta y luego remisión", cancelar_si_y_dn)

def cancelar_pr_facturado():
    pr = s["pr_tela"]["Lote 1"][0]
    A.cancelar_documento("Purchase Receipt", pr)
    return frappe.db.get_value("Purchase Receipt", pr, "docstatus")
caso("cancelar recibo de compra ya facturado", cancelar_pr_facturado)

def cancelar_cadena_pr():
    pi = frappe.db.get_value("Purchase Invoice Item", {"purchase_receipt": s["pr_tela"]["Lote 2"][0], "docstatus": 1}, "parent")
    A.cancelar_documento("Purchase Invoice", pi)
    pr = s["pr_tela"]["Lote 2"][0]
    fl = frappe.db.get_value("Purchase Receipt", pr, "factura_flete")
    fl_ds = frappe.db.get_value("Purchase Invoice", fl, "docstatus")
    A.cancelar_documento("Purchase Receipt", pr)
    est = A.estado_recibos_oc(s["pos"]["Lote 2"][2] if len(s["pos"]["Lote 2"]) > 2 else s["pos"]["Lote 2"][0])
    return dict(pr=frappe.db.get_value("Purchase Receipt", pr, "docstatus"), flete=fl, flete_ds=frappe.db.get_value("Purchase Invoice", fl, "docstatus"),
                flete_antes=fl_ds, msgs=[m[:120] for m in frappe.local.message_log][:2], pendiente=est["pendiente_recibir"])
caso("cancelar factura + recibo de tela (flete ya validado)", cancelar_cadena_pr)

def cancelar_scr_final():
    scr = frappe.db.get_value("Subcontracting Receipt Item", {"subcontracting_order": "SC-ORD-2026-00121", "docstatus": 1}, "parent")
    A.cancelar_documento("Subcontracting Receipt", scr)
    return frappe.db.get_value("Subcontracting Receipt", scr, "docstatus")
caso("cancelar recibo de confección con producto ya remisionado", cancelar_scr_final)
