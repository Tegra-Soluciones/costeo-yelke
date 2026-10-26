import json, traceback
import frappe
from costeo_yelke.api import costeo_api as A
frappe.set_user("Administrator")
errs, n = [], 0
def t(nombre, fn, *a, **k):
    global n
    n += 1
    frappe.db.savepoint("sm")
    try:
        fn(*a, **k)
    except Exception as e:
        errs.append((nombre, a, k, f"{type(e).__name__}: {str(e)[:200]}"))
    finally:
        try: frappe.db.rollback(save_point="sm")
        except Exception: frappe.db.rollback()
        frappe.local.message_log = []

t("get_costeo_list", A.get_costeo_list)
t("dashboard_metrics", A.dashboard_metrics)
t("get_permisos_validacion_yelke", A.get_permisos_validacion_yelke)
for c in frappe.get_all("Costeo", pluck="name"):
    co = frappe.db.get_value("Costeo", c, "compañia")
    t("get_company_defaults", A.get_company_defaults, co) if "company" in A.get_company_defaults.__code__.co_varnames[:1] else None
    for fn in ("get_costeo_related", "get_historial_costeo", "get_flujo_operaciones", "get_articulos_pendientes",
               "get_revisiones_costeo", "listar_variantes_de_costeo",
               "get_reporte_final", "produccion_completa", "posicion_material_costeo", "sub_saldo_talleres"):
        f = getattr(A, fn)
        t(fn, f, c)
    sos = frappe.get_all("Sales Order", filters={"costeo": c, "docstatus": ["<", 2]}, pluck="name")
    for so in sos or [None]:
        t("get_produccion_docs", A.get_produccion_docs, c, so)
        t("get_plan_detail", A.get_plan_detail, c, so)
        t("get_facturas_compra", A.get_facturas_compra, c) if not so else None
        t("get_reporte_final_so", A.get_reporte_final, c, so)
    for plan in frappe.get_all("Production Plan", filters={"costeo": c, "docstatus": ["<", 2]}, pluck="name"):
        for fn in ("get_solicitud_material", "get_recibos", "get_subcontratos", "get_lotes_produccion"):
            t(fn, getattr(A, fn), plan)
        from costeo_yelke.api import tallas_lote
        t("get_tallas_de_lotes", tallas_lote.get_tallas_de_lotes, plan)
    for po in frappe.get_all("Purchase Order", filters={"costeo": c, "docstatus": ["<", 2]}, fields=["name", "is_subcontracted", "docstatus"]):
        t("get_documento_compra PO", A.get_documento_compra, "Purchase Order", po.name)
        if po.is_subcontracted:
            t("sub_get_flujo", A.sub_get_flujo, po.name)
            t("get_om", A.get_om, po.name)
            from costeo_yelke.api import om_general
            t("om_de_oc", om_general.om_de_oc, po.name)
        else:
            t("estado_recibos_oc", A.estado_recibos_oc, po.name)
for pr in frappe.get_all("Purchase Receipt", filters={"docstatus": ["<", 2]}, pluck="name", limit=60):
    t("get_documento_compra PR", A.get_documento_compra, "Purchase Receipt", pr)
for pi in frappe.get_all("Purchase Invoice", filters={"docstatus": ["<", 2]}, pluck="name", limit=60):
    t("get_factura_compra", A.get_factura_compra, pi)
for dn in frappe.get_all("Delivery Note", filters={"docstatus": ["<", 2]}, pluck="name", limit=30):
    t("get_remision", A.get_remision, dn)
for scr in frappe.get_all("Subcontracting Receipt", filters={"docstatus": ["<", 2]}, pluck="name", limit=60):
    t("sub_get_recibo", A.sub_get_recibo, scr)
for se in frappe.get_all("Stock Entry", filters={"docstatus": ["<", 2], "purpose": "Send to Subcontractor"}, pluck="name", limit=40):
    t("sub_get_transferencia", A.sub_get_transferencia, se)
for sco in frappe.get_all("Subcontracting Order", filters={"docstatus": 1}, pluck="name", limit=60):
    t("estado_recibos_sco", A.estado_recibos_sco, sco)
print("llamadas:", n, "errores:", len(errs))
vistos = set()
for e in errs:
    k = (e[0], e[3][:80])
    if k in vistos: continue
    vistos.add(k)
    print("ERR", e[0], e[1][:2], e[3])
