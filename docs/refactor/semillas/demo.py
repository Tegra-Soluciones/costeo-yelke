"""Ejemplo completo para la demostración de los últimos cambios (sandbox.local).
Reutiliza las fases de e2e.py con su propio archivo de estado y agrega:
tallas en la OV y en los lotes, compra en dólares y PDFs reales adjuntos."""
import json
import frappe
from frappe.utils import add_days, nowdate, flt
import e2e
from e2e import api, log, load, save, P1, P2

e2e.ST = "/private/tmp/claude-502/-Users-trabajo-Documents-frappe-bench-v15-apps-costeo-yelke/71ca1590-ba17-4578-bee2-05e63df7e159/scratchpad/demo_state.json"
TITULO = "EJEMPLO COMPLETO · ÚLTIMOS CAMBIOS"
TALLAS = {"S - CAB-LETRA": (150, 60, 90), "M - CAB-LETRA": (300, 120, 180),
          "L - CAB-LETRA": (350, 140, 210), "XL - CAB-LETRA": (200, 80, 120)}


def pdf(dt, dn, nombre, titulo, cuerpo):
    from frappe.utils.pdf import get_pdf
    html = (f"<div style='font-family:Arial;padding:30px'><h2 style='color:#af282f'>{titulo}</h2>"
            f"<p>{cuerpo}</p><p style='color:#888'>Documento de ejemplo para la demostración.</p></div>")
    f = frappe.get_doc({"doctype": "File", "file_name": nombre, "attached_to_doctype": dt, "attached_to_name": dn,
                        "content": get_pdf(html), "is_private": 1}).insert(ignore_permissions=True)
    return f.file_url


def _con_pdf(kw):
    """Las facturas del ejemplo llevan un PDF legible con su folio."""
    dt, dn = kw.get("doctype"), kw.get("name")
    if dt in ("Purchase Invoice", "Sales Invoice") and not frappe.db.get_value(dt, dn, "factura_pdf"):
        d = frappe.get_doc(dt, dn)
        quien = d.get("supplier_name") or d.get("customer_name")
        url = pdf(dt, dn, f"Factura {dn}.pdf", f"Factura {d.get('bill_no') or dn}",
                  f"{quien} · Total {d.grand_total:,.2f} {d.currency}")
        frappe.db.set_value(dt, dn, "factura_pdf", url)


e2e._con_pdf = _con_pdf


def fase_a():
    s = {}
    c = s["costeo"] = api("duplicate_costeo", name=e2e.BASE)["name"]
    frappe.db.set_value("Costeo", c, "titulo", TITULO)
    api("validar_documento", doctype="Costeo", name=c)
    q = api("crear_cotizacion", costeo=c)["name"]
    api("validar_documento", doctype="Quotation", name=q)
    s["quotation"] = q
    so = api("crear_orden_venta", costeo=c, delivery_date=add_days(nowdate(), 40), po_no="OC-FXE-2026-0915")["name"]
    s["so"] = so
    e2e.esperar_error("OV sin OC del cliente", lambda: api("validar_documento", doctype="Sales Order", name=so))
    url = pdf("Sales Order", so, "OC cliente FERROCARRIL OC-FXE-2026-0915.pdf", "Orden de compra OC-FXE-2026-0915",
              "FERROCARRIL MEXICANO SA DE CV · 1,000 camisolas de gabardina naranja + 50 en tallas XXL-3XL")
    frappe.db.set_value("Sales Order", so, "oc_cliente_archivo", url)
    from costeo_yelke.api import tallas_ov
    row = next(r["row"] for r in tallas_ov.get_desglose_tallas_ov(sales_order=so) if r["item_code"] == P1)
    filas = [{"talla": t, "qty": q[0]} for t, q in TALLAS.items()]
    tallas_ov.guardar_desglose_tallas_ov(so, row, json.dumps(filas))
    api("validar_documento", doctype="Sales Order", name=so)
    log("OV", so, "validada con OC del cliente y desglose", {t: q[0] for t, q in TALLAS.items()})
    frappe.db.commit()
    save(s)


def fase_c():
    s = load()
    mr = api("get_solicitud_material", plan=s["plan"])["detail"]
    api("guardar_solicitud_material", mr=s["mr"], items=json.dumps(mr["items"]), schedule_date=None)
    lotes = [
        {"lote_ref": "Lote 1", "schedule_date": add_days(nowdate(), 10), "piezas": {P1: 400, P2: 20},
         "tallas": {P1: {t: q[1] for t, q in TALLAS.items()}}},
        {"lote_ref": "Lote 2", "schedule_date": add_days(nowdate(), 20), "piezas": {P1: 600, P2: 30},
         "tallas": {P1: {t: q[2] for t, q in TALLAS.items()}}},
    ]
    api("mr_dividir_en_lotes_por_piezas", mr=s["mr"], plan=s["plan"], lotes=json.dumps(lotes))
    api("validar_documento", doctype="Material Request", name=s["mr"])
    log("solicitud validada en 2 lotes con reparto por talla")
    frappe.db.commit()
    save(s)


def fase_usd():
    """Lote 2: la cinta de MOROTEX se compra en dólares."""
    s = load()
    r = api("mr_generar_oc_lote", mr=s["mr"], lote_ref="Lote 2")
    s.setdefault("pos", {})["Lote 2"] = r["purchase_orders"]
    for po in r["purchase_orders"]:
        d = frappe.get_doc("Purchase Order", po)
        if d.supplier == "MOROTEX":
            api("guardar_documento_compra", doctype="Purchase Order", name=po, currency="USD", conversion_rate=18.30)
            d.reload()
            log("OC en dólares", po, d.currency, d.conversion_rate, d.grand_total, "USD =", d.base_grand_total, "MXN")
            s["po_usd"] = po
        api("marcar_revisado_documento", doctype="Purchase Order", name=po)
        api("validar_documento", doctype="Purchase Order", name=po)
    frappe.db.commit()
    save(s)


def fase_factura_usd():
    s = load()
    po = s["po_usd"]
    prn = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": po, "docstatus": 1}, pluck="parent")[0]
    pi = api("crear_factura_compra", source_doctype="Purchase Receipt", source_name=prn)["name"]
    api("actualizar_factura_compra", name=pi, bill_no="MOR-USD-2231", bill_date=nowdate(), conversion_rate=18.05)
    api("validar_documento", doctype="Purchase Invoice", name=pi)
    d = frappe.get_doc("Purchase Invoice", pi)
    log("factura en dólares", pi, d.currency, d.conversion_rate, d.grand_total, "USD =", d.base_grand_total, "MXN")
    log("  GL", e2e.gl_de(pi))
    frappe.db.commit()
