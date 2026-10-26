"""Prueba 1 -- escenario de punta a punta en sandbox.local, llamando las MISMAS
funciones que la pantalla, en el mismo orden. Cada fase hace commit al final.
Uso: run.py <fase> [args]"""
import json, sys
import frappe
from frappe.utils import add_days, nowdate, flt

A = "costeo_yelke.api.costeo_api"
ST = "/private/tmp/claude-502/-Users-trabajo-Documents-frappe-bench-v15-apps-costeo-yelke/455962b2-ce0b-409b-b631-99f79fded5f9/scratchpad/e2e_state.json"
BASE = "CST-FERROCARRIL-MEXI-2026-00024"
P1, P2 = "CAMISOLA-PRUEBA-YP", "CAMISOLA-PRUEBA-YP-XXL-3XL"


_PDF = None


def _con_pdf(kw):
    """Toda factura se valida con su PDF (patch v0_2_58): el guion lo adjunta."""
    global _PDF
    if kw.get("doctype") in ("Purchase Invoice", "Sales Invoice") and not frappe.db.get_value(kw["doctype"], kw["name"], "factura_pdf"):
        from frappe.utils.pdf import get_pdf
        _PDF = _PDF or get_pdf("<p>Factura de prueba</p>")
        f = frappe.get_doc({"doctype": "File", "file_name": f"{kw['name']}.pdf", "attached_to_doctype": kw["doctype"],
                            "attached_to_name": kw["name"], "content": _PDF, "is_private": 1}).insert(ignore_permissions=True)
        frappe.db.set_value(kw["doctype"], kw["name"], "factura_pdf", f.file_url)


def api(fn, **kw):
    if fn == "validar_documento":
        _con_pdf(kw)
    mod, _, name = fn.rpartition(".") if "." in fn else (A, ".", fn)
    m = frappe.get_module(mod)
    return getattr(m, name)(**kw)


def load():
    try:
        return json.load(open(ST))
    except Exception:
        return {}


def save(s):
    json.dump(s, open(ST, "w"), indent=1, default=str)


def log(*a):
    print("·", *a, flush=True)


def adjuntar(doctype, name, fname="respaldo.txt"):
    f = frappe.get_doc({"doctype": "File", "file_name": fname, "attached_to_doctype": doctype,
                        "attached_to_name": name, "content": b"archivo de prueba", "is_private": 1})
    f.insert(ignore_permissions=True)
    return f.file_url


def esperar_error(que, fn):
    frappe.db.savepoint("esp")
    try:
        fn()
        log("!! BUG: no bloqueó:", que)
    except Exception as e:
        log("OK bloqueó", que, "->", str(e)[:110])
    frappe.db.rollback(save_point="esp")
    frappe.local.message_log = []


def fase_a():
    s = {}
    # Antes aquí se borraban "los costeos en borrador recientes" para limpiar corridas
    # fallidas: el 15-oct-2026 eso se llevó el ejemplo de tallas extra (00035), que era
    # del usuario. Nunca borrar por fecha: limpiar solo lo que esta corrida creó.
    r = api("duplicate_costeo", name=BASE)
    c = s["costeo"] = r["name"]
    log("costeo duplicado", c)
    api("validar_documento", doctype="Costeo", name=c)
    log("costeo validado", frappe.db.get_value("Costeo", c, ["docstatus", "costeo_status"]))
    q = api("crear_cotizacion", costeo=c)["name"]
    api("validar_documento", doctype="Quotation", name=q)
    s["quotation"] = q
    qd = frappe.get_doc("Quotation", q)
    log("cotización", q, qd.docstatus, qd.grand_total, [(i.item_code, i.qty, i.rate) for i in qd.items])
    so = api("crear_orden_venta", costeo=c, delivery_date=add_days(nowdate(), 40), po_no="OC-CLIENTE-" + frappe.generate_hash(length=6))["name"]
    s["so"] = so
    # Sin la OC del cliente NO debe validar
    esperar_error("OV sin OC del cliente", lambda: api("validar_documento", doctype="Sales Order", name=so))
    url = adjuntar("Sales Order", so, "oc_cliente.txt")
    frappe.db.set_value("Sales Order", so, "oc_cliente_archivo", url)
    # Desglose por talla del producto base: debe cuadrar EXACTO
    from costeo_yelke.api import tallas_ov
    d = tallas_ov.get_desglose_tallas_ov(sales_order=so)
    s["desglose_info"] = str(d)[:400]
    log("desglose OV (get):", str(d)[:300])
    api("validar_documento", doctype="Sales Order", name=so)
    sod = frappe.get_doc("Sales Order", so)
    log("OV validada", so, sod.grand_total, [(i.item_code, i.qty, i.rate, i.prevdoc_docname) for i in sod.items])
    log("cotización status", frappe.db.get_value("Quotation", q, "status"))
    frappe.db.commit()
    save(s)


def fase_b():
    s = load()
    c, so = s["costeo"], s["so"]
    if not frappe.db.exists("Production Plan", {"costeo": c, "docstatus": ["<", 2]}) if frappe.db.has_column("Production Plan", "costeo") else True:
        r = api("preparar_produccion", costeo=c, sales_order=so)
        for st in r["steps"]:
            log("prep", st)
    plan = api("get_plan_detail", costeo=c, sales_order=so)["plan"]
    s["plan"] = plan["name"]
    log("plan", plan["name"], [(p["item_code"], p["planned_qty"]) for p in plan.get("po_items", [])])
    api("plan_obtener_materias_primas", plan=plan["name"], warehouse=None)
    items = [{"name": it["name"], "planned_qty": it["planned_qty"]} for it in plan.get("po_items", [])]
    api("guardar_plan", plan=plan["name"], for_warehouse=None, items=json.dumps(items))
    api("validar_documento", doctype="Production Plan", name=plan["name"])
    log("plan validado")
    api("plan_crear_solicitud_material", plan=plan["name"])
    mr = api("get_solicitud_material", plan=plan["name"])["detail"]
    s["mr"] = mr["name"]
    log("MR", mr["name"], [(i["item_code"], i["qty"], i.get("uom"), i.get("stock_qty")) for i in mr["items"]])
    frappe.db.commit()
    save(s)


def fase_c():
    s = load()
    lotes = [
        {"lote_ref": "Lote 1", "schedule_date": add_days(nowdate(), 10), "piezas": {P1: 400, P2: 20}, "tallas": {}},
        {"lote_ref": "Lote 2", "schedule_date": add_days(nowdate(), 20), "piezas": {P1: 600, P2: 30}, "tallas": {}},
    ]
    mr = api("get_solicitud_material", plan=s["plan"])["detail"]
    api("guardar_solicitud_material", mr=s["mr"], items=json.dumps(mr["items"]), schedule_date=None)
    r = api("mr_dividir_en_lotes_por_piezas", mr=s["mr"], plan=s["plan"], lotes=json.dumps(lotes))
    log("dividir", str(r)[:400])
    api("validar_documento", doctype="Material Request", name=s["mr"])
    mrd = frappe.get_doc("Material Request", s["mr"])
    for i in mrd.items:
        log("  MR línea", i.item_code, i.qty, i.uom, i.stock_qty, i.get("lote_ref"), i.schedule_date)
    frappe.db.commit()
    save(s)


if __name__ == "__main__":
    pass


def paqueteria():
    n = "PAQUETERIA PRUEBA UNO"
    if not frappe.db.exists("Supplier", n):
        frappe.get_doc({"doctype": "Supplier", "supplier_name": n, "supplier_group": "Transporte y paquetería",
                        "es_paqueteria": 1, "retiene_iva_fletes": 1, "supplier_type": "Company"}).insert(ignore_permissions=True)
    return n


def pos_de_lote(s, lote):
    return frappe.get_all("Purchase Order", filters={"costeo": s["costeo"], "is_subcontracted": 0, "docstatus": ["<", 2]},
                          fields=["name", "supplier", "docstatus", "grand_total"], order_by="creation")


def fase_d(lote="Lote 1"):
    s = load()
    r = api("mr_generar_oc_lote", mr=s["mr"], lote_ref=lote)
    log("OC generadas", r.get("purchase_orders"), "neteo", r.get("neteo"), "redondeos", r.get("redondeos"))
    s.setdefault("pos", {})[lote] = r.get("purchase_orders")
    for po in r.get("purchase_orders") or []:
        d = frappe.get_doc("Purchase Order", po)
        log(" ", po, d.supplier, d.grand_total, [(i.item_code, i.qty, i.uom, i.rate, i.stock_qty) for i in d.items])
        esperar_error("validar OC sin revisión", lambda: api("validar_documento", doctype="Purchase Order", name=po))
        api("marcar_revisado_documento", doctype="Purchase Order", name=po)
        api("validar_documento", doctype="Purchase Order", name=po)
    # Generar de nuevo la OC del mismo lote no debe duplicar
    esperar_error("OC duplicada del mismo lote", lambda: api("mr_generar_oc_lote", mr=s["mr"], lote_ref=lote))
    frappe.db.commit()
    save(s)


def fase_e(lote="Lote 1"):
    """Recibos: gabardina en 2 entregas con flete de paquetería; el resto completo."""
    s = load()
    paq = paqueteria()
    for po in s["pos"][lote]:
        d = frappe.get_doc("Purchase Order", po)
        tela = any(i.item_code == "GABARDINA-NARANJA" for i in d.items)
        pr = api("crear_recibo_oc", po=po)
        prn = pr.get("name") or pr.get("receipt") or pr
        log("recibo", po, "->", str(pr)[:160])
        prn = prn if isinstance(prn, str) else None
        if not prn:
            prn = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": po, "docstatus": 0}, pluck="parent")[0]
        doc = api("get_documento_compra", doctype="Purchase Receipt", name=prn)
        items = doc["items"]
        if tela:
            for it in items:
                it["qty"] = 300
            api("guardar_documento_compra", doctype="Purchase Receipt", name=prn, items=json.dumps(items),
                shipping_cost=580, flete_modo="Paquetería externa", flete_proveedor=None, flete_incluye_iva=1)
            esperar_error("recibo con paquetería sin proveedor",
                          lambda: api("validar_documento", doctype="Purchase Receipt", name=prn))
            api("guardar_documento_compra", doctype="Purchase Receipt", name=prn, items=json.dumps(items),
                shipping_cost=580, flete_modo="Paquetería externa", flete_proveedor=paq, flete_incluye_iva=1)
        else:
            api("guardar_documento_compra", doctype="Purchase Receipt", name=prn, items=json.dumps(items), shipping_cost=0)
        api("validar_documento", doctype="Purchase Receipt", name=prn)
        prd = frappe.get_doc("Purchase Receipt", prn)
        log("  PR", prn, [(i.item_code, i.qty, i.received_qty, i.rate, i.valuation_rate) for i in prd.items],
            "flete PI:", prd.get("factura_flete"), "taxes:", [(t.description, t.category, t.tax_amount) for t in prd.taxes])
        if tela:
            est = frappe.get_module(A).estado_recibos_oc(po)
            log("  estado tras 1a entrega", {k: est[k] for k in est if k != "receipts"})
            esperar_error("factura de compra con recibo parcial",
                          lambda: api("crear_factura_compra", source_doctype="Purchase Receipt", source_name=prn))
            r2 = api("crear_recibo_oc", po=po, nuevo=1)
            pr2 = r2.get("name") if isinstance(r2, dict) else r2
            log("  2a entrega", str(r2)[:160])
            r3 = api("crear_recibo_oc", po=po, nuevo=1)
            log("  OK" if r3["name"] == pr2 else "  !! BUG", "nuevo recibo con borrador abierto regresa el borrador:", r3)
            d2 = api("get_documento_compra", doctype="Purchase Receipt", name=pr2)
            log("  2a entrega trae", [(i["item_code"], i["qty"]) for i in d2["items"]])
            api("guardar_documento_compra", doctype="Purchase Receipt", name=pr2, items=json.dumps(d2["items"]), shipping_cost=0)
            api("validar_documento", doctype="Purchase Receipt", name=pr2)
            est = frappe.get_module(A).estado_recibos_oc(po)
            log("  estado tras 2a entrega", {k: est[k] for k in est if k != "receipts"})
            esperar_error("recibo extra con todo recibido", lambda: api("crear_recibo_oc", po=po, nuevo=1))
            s.setdefault("pr_tela", {})[lote] = [prn, pr2]
            s.setdefault("pi_flete", {})[lote] = prd.get("factura_flete")
    frappe.db.commit()
    save(s)


def gl_de(voucher):
    return [(g.account, flt(g.debit, 2), flt(g.credit, 2)) for g in frappe.get_all(
        "GL Entry", filters={"voucher_no": voucher, "is_cancelled": 0}, fields=["account", "debit", "credit"])]


def fase_f(lote="Lote 1"):
    s = load()
    prs = s["pr_tela"][lote]
    ya = frappe.get_all("Purchase Invoice Item", filters={"purchase_receipt": prs[0], "docstatus": ["<", 2]}, pluck="parent")
    r = {"name": ya[0]} if ya else api("crear_factura_compra", source_doctype="Purchase Receipt", source_name=prs[0])
    pi = r.get("name")
    d = frappe.get_doc("Purchase Invoice", pi)
    log("PI tela", pi, d.net_total, d.grand_total, [(i.item_code, i.qty, i.rate, i.purchase_receipt) for i in d.items])
    if d.docstatus == 0:
        d.bill_no = "FOLIO-FILAFIL-" + lote[-1]; d.bill_date = nowdate(); d.save(ignore_permissions=True)
        api("validar_documento", doctype="Purchase Invoice", name=pi)
    log("  GL PI tela", gl_de(pi))
    # Facturas de los otros recibos
    for po in s["pos"][lote]:
        prn = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": po, "docstatus": 1}, pluck="parent")[0]
        if frappe.get_all("Purchase Invoice Item", filters={"purchase_receipt": prn, "docstatus": ["<", 2]}):
            continue
        r = api("crear_factura_compra", source_doctype="Purchase Receipt", source_name=prn)
        dd = frappe.get_doc("Purchase Invoice", r["name"])
        dd.bill_no = "FOLIO-" + po[-3:]; dd.bill_date = nowdate(); dd.save(ignore_permissions=True)
        api("validar_documento", doctype="Purchase Invoice", name=r["name"])
        log("PI", r["name"], dd.supplier, dd.grand_total)
    # Factura del flete
    pf = s["pi_flete"][lote]
    fd = frappe.get_doc("Purchase Invoice", pf)
    log("PI flete", pf, fd.supplier, fd.docstatus, fd.net_total, [(t.account_head, t.tax_amount) for t in fd.taxes], fd.grand_total, fd.flete_costeo)
    esperar_error("PI flete sin folio", lambda: api("validar_documento", doctype="Purchase Invoice", name=pf))
    fd.bill_no = "CFDI-PAQ-1"; fd.bill_date = nowdate(); fd.save(ignore_permissions=True)
    esperar_error("PI flete sin adjunto", lambda: api("validar_documento", doctype="Purchase Invoice", name=pf))
    adjuntar("Purchase Invoice", pf, "cfdi_flete.txt")
    api("validar_documento", doctype="Purchase Invoice", name=pf)
    log("  GL flete", gl_de(pf))
    puente = frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` where is_cancelled=0 and company='YELKE PRUEBAS'
        and account like 'Gastos incluidos en la valoraci%%'""")[0][0]
    log("  saldo cuenta puente (toda la compañía):", puente)
    fc = api("get_facturas_compra", costeo=s["costeo"]) if True else None
    log("bandeja facturas:", str(fc)[:600])
    frappe.db.commit()
    save(s)


def resumen_lote(s, lote):
    r = api("get_lotes_produccion", plan=s["plan"])
    L = next((l for l in r["lotes"] if l["lote_ref"] == lote), None)
    if not L:
        log("lote no encontrado", lote, [l["lote_ref"] for l in r["lotes"]])
        return r, None
    log(f"[{lote}] productos", [(p["finished_item"], p.get("qty")) for p in L.get("productos", [])])
    for p in L["paradas"]:
        log(f"  parada {p['orden']} {p['titulo']:<32} {p['supplier']:<26} sco={p['sco']} ds={p['sco_docstatus']} env={p['transfer_done']} rec={p['receipt_validated']} fg={len(p['fg_items'])}")
    for rm in L.get("ramas") or []:
        log("   rama", rm["pieza"], rm["por_prenda"], [(x["titulo"][:14], x["estado"], x["prendas"]) for x in rm["pasos"]], "lista" if rm["lista"] else "")
    for c in L.get("cadena") or []:
        log("   cadena", c["titulo"], c["estado"], c.get("piezas_listas"), "/", c.get("piezas_total"))
    return r, L


def fase_g(lote="Lote 1"):
    s = load()
    r = api("plan_crear_subcontratacion", plan=s["plan"])
    log("OC subcontratación", str(r)[:300])
    subs = api("get_subcontratos", plan=s["plan"])
    for po in subs.get("ocs") or []:
        if po.get("docstatus") == 0:
            api("marcar_revisado_documento", doctype="Purchase Order", name=po["name"])
            api("validar_documento", doctype="Purchase Order", name=po["name"])
        log("  OC maquila", po["name"], po.get("supplier"), po.get("docstatus"))
    r, L = resumen_lote(s, lote)
    prods = r.get("productos") or []
    cant = {}
    for p in prods:
        q = api("sub_qty_disponible", po=p["root_po"], producto=p["finished_item"])
        log("  disponible", p["finished_item"], {k: q.get(k) for k in ("sugerido", "saldo_pendiente", "limitado_por_stock")})
        cant[p["finished_item"]] = 400 if p["finished_item"] == P1 else 20
    ra = api("lote_abrir", plan=s["plan"], lote_ref=lote, cantidades=cant, schedule_date=add_days(nowdate(), 10))
    log("lote_abrir", str(ra)[:500])
    frappe.db.commit()
    resumen_lote(s, lote)
    save(s)


def recibir_sco(sco, flete=0, qty_factor=1.0):
    r = api("sub_crear_recibo", sco=sco)
    scr = r.get("name") or r.get("scr")
    d = api("sub_get_recibo", scr=scr)
    if d["docstatus"] == 1:
        return scr
    items = d["items"]
    if qty_factor != 1.0:
        for it in items:
            it["qty"] = round(flt(it["qty"]) * qty_factor)
    costos = [{"description": "Flete regreso del taller", "amount": 0}]
    if flete:
        costos = [{"description": "Flete regreso del taller", "amount": flete, "flete_incluye_iva": 1,
                   "proveedor_flete": paqueteria()}]
    api("sub_guardar_recibo", scr=scr, set_warehouse=d["set_warehouse"], rejected_warehouse=d["rejected_warehouse"],
        supplier_warehouse=d["supplier_warehouse"], items=json.dumps(items), costos=json.dumps(costos),
        distribute_additional_costs_based_on="Qty")
    api("validar_documento", doctype="Subcontracting Receipt", name=scr)
    return scr


def sco_estado(sco):
    return frappe.get_module(A).estado_recibos_sco(sco)


def fase_h(lote="Lote 1", maxit="25"):
    s = load()
    flete_puesto = s.get("flete_scr", {}).get(lote)
    for it in range(int(maxit)):
        r, L = resumen_lote(s, lote) if it % 4 == 0 else (None, frappe._dict())
        if not L:
            r = api("get_lotes_produccion", plan=s["plan"])
            L = next(l for l in r["lotes"] if l["lote_ref"] == lote)
        celdas = [(rama["pieza"], p) for rama in L["ramas"] for p in rama["pasos"]]
        cadena = L.get("rama_cadena") or []
        if not all(rm["lista"] for rm in L["ramas"]):
            if it == 0 and cadena and cadena[0]["scos"]:
                esperar_error("enviar a confección sin piezas", lambda: api("sub_enviar_material", sco=cadena[0]["scos"][0]))
            cadena = []
        hecho = False
        # 1) enviar material a lo encargado
        for pieza, p in celdas + [(None, c) for c in cadena]:
            if p["estado"] == "encargado":
                for sco in p["scos"]:
                    if frappe.db.get_value("Subcontracting Order", sco, "docstatus") == 1 and not frappe.db.exists(
                            "Stock Entry", {"subcontracting_order": sco, "docstatus": 1}):
                        e = api("sub_enviar_material", sco=sco)
                        log(f"it{it} enviar", pieza, p["titulo"][:20], sco, "->", e.get("stock_entry"), e.get("scr"),
                            str({k: v for k, v in e.items() if k not in ('ok', 'stock_entry', 'scr')})[:150])
                        hecho = True
        if hecho:
            frappe.db.commit(); continue
        # 2) recibir lo enviado
        for pieza, p in celdas + [(None, c) for c in cadena]:
            if p["estado"] == "enviado":
                for sco in p["scos"]:
                    est = sco_estado(sco)
                    if est["recibido_completo"]:
                        continue
                    fl = 0
                    if not flete_puesto:
                        fl = flete_puesto = 348  # 300 + IVA
                        s.setdefault("flete_scr", {})[lote] = sco
                    if lote == "Lote 2" and not s.get("parcial_hecho") and "Corte" in p["titulo"]:
                        s["parcial_hecho"] = sco
                        scr = recibir_sco(sco, flete=fl, qty_factor=0.5)
                        est = sco_estado(sco)
                        log(f"it{it} recibo PARCIAL", sco, scr, {k: est[k] for k in ("recibido_completo", "recibido_parcial", "pendiente_recibir", "puede_nuevo_recibo")})
                        r2 = api("sub_crear_recibo", sco=sco, nuevo=1)
                        scr2 = r2.get("name") or r2.get("scr")
                        d2 = api("sub_get_recibo", scr=scr2)
                        log("   2o recibo trae", [(i["item_code"][-12:], i["qty"]) for i in d2["items"]][:4], "...")
                        scr = recibir_sco(sco)
                        est = sco_estado(sco)
                        log("   tras 2o recibo", scr, {k: est[k] for k in ("recibido_completo", "pendiente_recibir", "puede_nuevo_recibo")})
                        esperar_error("3er recibo de taller con todo recibido", lambda: api("sub_crear_recibo", sco=sco, nuevo=1))
                    else:
                        scr = recibir_sco(sco, flete=fl)
                    log(f"it{it} recibir", pieza, p["titulo"][:20], sco, "->", scr, "flete" if fl else "")
                    hecho = True
        if hecho:
            frappe.db.commit(); continue
        # 3) encargar lo listo, agrupado por parada
        listos = {}
        for pieza, p in celdas:
            if p["estado"] == "listo":
                listos.setdefault(p["parada_id"], []).append(pieza)
        prendas = sum(flt(p["qty"]) for p in L["productos"])
        for pid, nombres in listos.items():
            e = api("parada_registrar_entrega", plan=s["plan"], lote_ref=lote, parada_id=pid, cantidad=prendas,
                    sub_ensamblaje=json.dumps(nombres))
            log(f"it{it} encargar", pid, nombres, "->", str(e)[:160])
            hecho = True
        if hecho:
            frappe.db.commit(); continue
        log("sin acciones pendientes en ramas/cadena; fin en it", it)
        break
    frappe.db.commit()
    save(s)
    resumen_lote(s, lote)


def fase_g2(lote="Lote 2"):
    s = load()
    antes = frappe.get_all("Purchase Order", filters={"costeo": s["costeo"], "is_subcontracted": 1, "docstatus": ["<", 2]}, pluck="name")
    try:
        r = api("plan_crear_subcontratacion", plan=s["plan"])
        log("plan_crear_subcontratacion 2a vez ->", str(r)[:200])
    except Exception as e:
        log("plan_crear_subcontratacion 2a vez bloqueó:", str(e)[:150])
        frappe.db.rollback()
    despues = frappe.get_all("Purchase Order", filters={"costeo": s["costeo"], "is_subcontracted": 1, "docstatus": ["<", 2]}, pluck="name")
    log("OC maquila antes/después", len(antes), len(despues), "OK" if len(antes) == len(despues) else "!! BUG duplicó")
    cant = {P1: 600, P2: 30}
    # más de lo que queda en la OC: debe bloquear o recortar
    rx = api("lote_abrir", plan=s["plan"], lote_ref="Lote 9", cantidades={P1: 5000})
    log("abrir lote por más del saldo ->", "OK avisa" if rx["errores"] else "!! BUG sin error", str(rx)[:300])
    ra = api("lote_abrir", plan=s["plan"], lote_ref=lote, cantidades=cant, schedule_date=add_days(nowdate(), 20))
    log("lote_abrir", str(ra)[:300])
    frappe.db.commit()


def validar_pi(pi, folio, adjunto=False):
    d = frappe.get_doc("Purchase Invoice", pi)
    if d.docstatus:
        return d
    d.bill_no = folio; d.bill_date = nowdate(); d.save(ignore_permissions=True)
    if adjunto:
        adjuntar("Purchase Invoice", pi, "cfdi.txt")
    api("validar_documento", doctype="Purchase Invoice", name=pi)
    return frappe.get_doc("Purchase Invoice", pi)


def fase_j():
    s = load()
    c, so = s["costeo"], s["so"]
    for po in frappe.get_all("Purchase Order", filters={"costeo": c, "is_subcontracted": 1, "docstatus": 1}, pluck="name"):
        r = api("crear_factura_compra", source_doctype="Purchase Order", source_name=po)
        d = validar_pi(r["name"], "MAQ-" + po[-3:])
        esperado = sum(flt(x.amount) for x in frappe.get_all("Purchase Order Item", filters={"parent": po}, fields=["amount"]))
        log("PI maquila", po, d.name, d.supplier, d.net_total, "OC:", esperado, "OK" if abs(d.net_total - esperado) < 0.05 else "!! DIFERENTE",
            "IVA/ret:", [(t.account_head[:28], t.tax_amount) for t in d.taxes])
    for pf in frappe.get_all("Purchase Invoice", filters={"flete_costeo": c, "docstatus": 0}, pluck="name"):
        d = validar_pi(pf, "CFDI-" + pf[-3:], adjunto=True)
        log("PI flete", pf, d.flete_origen_doctype, d.flete_origen, d.net_total, d.grand_total)
    log("produccion_completa", api("produccion_completa", costeo=c, sales_order=so))
    # Remisión 1: solo Lote 1, con flete al cliente por paquetería
    r = api("crear_remision", costeo=c, sales_order=so, lote_ref="Lote 1")
    dn = r["name"]
    dd = api("get_remision", name=dn)
    log("remisión 1", dn, [(i["item_code"], i["qty"]) for i in dd["items"]])
    esperar_error("remisión con flete sin transportista", lambda: (
        api("actualizar_remision", name=dn, flete_costo=1160, flete_incluye_iva=1, flete_proveedor=""),
        api("validar_remision", name=dn)))
    api("actualizar_remision", name=dn, flete_costo=1160, flete_incluye_iva=1, flete_proveedor=paqueteria())
    v = api("validar_remision", name=dn)
    dnd = frappe.get_doc("Delivery Note", dn)
    log("  validada", v, "flete_costo", dnd.get("flete_costo"), "factura", dnd.get("flete_factura"))
    log("  GL", gl_de(dn))
    r2 = api("crear_remision", costeo=c, sales_order=so)
    dn2 = r2["name"]
    api("actualizar_remision", name=dn2, flete_costo=0)
    api("validar_remision", name=dn2)
    log("remisión 2", dn2, [(i.item_code, i.qty) for i in frappe.get_doc("Delivery Note", dn2).items])
    esperar_error("tercera remisión sin saldo", lambda: api("crear_remision", costeo=c, sales_order=so))
    fv = api("crear_factura_venta", costeo=c, sales_order=so)
    sid = frappe.get_doc("Sales Invoice", fv["name"])
    log("factura venta", sid.name, sid.net_total, sid.grand_total, [(i.item_code, i.qty, i.rate, i.delivery_note) for i in sid.items])
    api("validar_documento", doctype="Sales Invoice", name=sid.name)
    sid.reload()
    log("  overhead JE", sid.get("overhead_journal_entry"), "GL", gl_de(sid.name))
    s["dn"] = [dn, dn2]; s["si"] = sid.name
    frappe.db.commit()
    save(s)
    log("costeo status", frappe.db.get_value("Costeo", c, "costeo_status"), "OV", frappe.db.get_value("Sales Order", so, ["status", "per_delivered", "per_billed"]))


def vouchers_del_costeo(s):
    c = s["costeo"]
    pos = frappe.get_all("Purchase Order", filters={"costeo": c, "docstatus": 1}, pluck="name")
    prs = list({r for r in frappe.get_all("Purchase Receipt Item", filters={"purchase_order": ["in", pos], "docstatus": 1}, pluck="parent")})
    scos = frappe.get_all("Subcontracting Order", filters={"purchase_order": ["in", pos], "docstatus": 1}, pluck="name")
    scrs = list({r for r in frappe.get_all("Subcontracting Receipt Item", filters={"subcontracting_order": ["in", scos], "docstatus": 1}, pluck="parent")})
    ses = frappe.get_all("Stock Entry", filters={"subcontracting_order": ["in", scos], "docstatus": 1}, pluck="name")
    pis = list({r for r in frappe.get_all("Purchase Invoice Item", filters={"purchase_order": ["in", pos], "docstatus": 1}, pluck="parent")})
    pis += frappe.get_all("Purchase Invoice", filters={"flete_costeo": c, "docstatus": 1}, pluck="name")
    pis = list(set(pis))
    return {"PR": prs, "SCR": scrs, "SE": ses, "PI": pis, "DN": s["dn"], "SI": [s["si"]],
            "JE": [frappe.db.get_value("Sales Invoice", s["si"], "overhead_journal_entry")] if frappe.db.get_value("Sales Invoice", s["si"], "overhead_journal_entry") else []}


def fase_k():
    s = load()
    c, so = s["costeo"], s["so"]
    ok = fail = 0

    def chk(nombre, cond, detalle=""):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
        log(("OK  " if cond else "FALLA"), nombre, detalle)

    V = vouchers_del_costeo(s)
    todos = [v for vs in V.values() for v in vs]
    log("vouchers", {k: len(v) for k, v in V.items()})
    # 1) Partida doble por documento
    malos = frappe.db.sql("""select voucher_no, sum(debit)-sum(credit) d from `tabGL Entry` where is_cancelled=0
        and voucher_no in %s group by voucher_no having abs(d) > 0.01""", (todos,))
    chk("partida doble por documento", not malos, malos)
    # 2) Cuentas puente del costeo en cero
    for patron in ("Stock recibidas, pero no facturada%", "Gastos incluidos en la valoraci%"):
        v = flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` g join tabAccount a on a.name=g.account
            where g.is_cancelled=0 and g.voucher_no in %s and a.account_name like %s""", (todos, patron))[0][0], 2)
        chk(f"cuenta puente '{patron[:30]}' en cero", abs(v) < 0.05, v)
    # 3) Inventario: SLE = GL para los documentos del costeo
    sle = flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where is_cancelled=0 and voucher_no in %s", (todos,))[0][0], 2)
    gl_inv = flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` g join tabAccount a on a.name=g.account
        where g.is_cancelled=0 and g.voucher_no in %s and a.account_type='Stock'""", (todos,))[0][0], 2)
    chk("inventario (kardex) = contabilidad", abs(sle - gl_inv) < 0.5, f"SLE {sle} vs GL {gl_inv}")
    # 4) Producto terminado: producido = entregado
    prod = flt(frappe.db.sql("""select sum(actual_qty) from `tabStock Ledger Entry` where is_cancelled=0 and voucher_type='Subcontracting Receipt'
        and voucher_no in %s and item_code in %s and actual_qty>0""", (V["SCR"], (P1, P2)))[0][0])
    ent = flt(frappe.db.sql("""select -sum(actual_qty) from `tabStock Ledger Entry` where is_cancelled=0 and voucher_no in %s""", (tuple(V["DN"]),))[0][0])
    chk("prendas producidas = remisionadas = 1050", prod == ent == 1050, f"{prod} / {ent}")
    # 5) Costo de ventas = valor del producto terminado que salió
    cogs = flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` g where is_cancelled=0 and voucher_no in %s
        and account like 'COSTO DE VENTAS%%'""", (tuple(V["DN"]),))[0][0], 2)
    fg_val = flt(frappe.db.sql("""select sum(stock_value_difference) from `tabStock Ledger Entry` where is_cancelled=0
        and voucher_type='Subcontracting Receipt' and voucher_no in %s and item_code in %s""", (V["SCR"], (P1, P2)))[0][0], 2)
    chk("costo de ventas = valor producido", abs(cogs - fg_val) < 1, f"COGS {cogs} vs producido {fg_val}")
    # 6) Materia prima: comprado vs enviado/consumido
    for item in ("GABARDINA-NARANJA", "CINTA REFLEJANTE GRIS", "BOTON-PASTA-18L-PZA", "BOTON-PASTA-14L-PZA"):
        comprado = flt(frappe.db.sql("select sum(stock_qty) from `tabPurchase Receipt Item` where docstatus=1 and parent in %s and item_code=%s", (V["PR"], item))[0][0])
        consumido = flt(frappe.db.sql("""select sum(consumed_qty) from `tabSubcontracting Receipt Supplied Item` where docstatus=1 and parent in %s and rm_item_code=%s""", (V["SCR"], item))[0][0])
        teorico = {"GABARDINA-NARANJA": 1550, "CINTA REFLEJANTE GRIS": 3570, "BOTON-PASTA-18L-PZA": 13700, "BOTON-PASTA-14L-PZA": 3200}[item]
        chk(f"{item}: consumo = BOM ({teorico})", abs(consumido - teorico) <= 0.01 * len(V["SCR"]) + 1e-6, f"comprado {comprado}, consumido {round(consumido, 3)}")
    # 7) Maquila facturada = OC
    for po in frappe.get_all("Purchase Order", filters={"costeo": c, "is_subcontracted": 1, "docstatus": 1}, fields=["name", "net_total", "per_received", "per_billed", "status"]):
        chk(f"OC maquila {po.name} recibida/facturada 100%", po.per_received >= 99.99 and po.per_billed >= 99.99, (po.per_received, po.per_billed, po.status))
    for po in frappe.get_all("Purchase Order", filters={"costeo": c, "is_subcontracted": 0, "docstatus": 1}, fields=["name", "per_received", "per_billed", "status"]):
        chk(f"OC material {po.name} recibida/facturada 100%", po.per_received >= 99.99 and po.per_billed >= 99.99, (po.per_received, po.per_billed, po.status))
    # 8) Reporte final
    rep = api("get_reporte_final", costeo=c, sales_order=so)
    log("reporte final (resumen):", json.dumps({k: v for k, v in rep.items() if not isinstance(v, (list, dict))}, default=str)[:900])
    for k, v in rep.items():
        if isinstance(v, dict):
            log("   ", k, json.dumps(v, default=str)[:500])
    s["reporte"] = rep
    save(s)
    log(f"RESULTADO: {ok} OK, {fail} FALLAS")


def fase_l():
    s = load()
    c = s["costeo"]
    sal = api("sub_saldo_talleres", costeo=c)
    log("saldo talleres:", json.dumps(sal, default=str)[:900])
    for t in (sal.get("talleres") or sal.get("almacenes") or []):
        wh = t.get("warehouse")
        items = t.get("items") or t.get("materiales") or []
        if not wh or not items:
            continue
        r = api("sub_devolver_material", costeo=c, warehouse=wh, items=json.dumps(items))
        log("devolución", wh, "->", str(r)[:300])
        se = r.get("stock_entry") or r.get("name")
        if se:
            log("   GL", gl_de(se))
    sal2 = api("sub_saldo_talleres", costeo=c)
    log("saldo después:", json.dumps(sal2, default=str)[:400])
    frappe.db.commit()


def fase_f_sin_flete(lote="Lote 2"):
    """fase_f sin la parte del flete (ese ya lo validó fase_j en esta corrida)."""
    s = load()
    prs = s["pr_tela"][lote]
    ya = frappe.get_all("Purchase Invoice Item", filters={"purchase_receipt": prs[0], "docstatus": ["<", 2]}, pluck="parent")
    pi = ya[0] if ya else api("crear_factura_compra", source_doctype="Purchase Receipt", source_name=prs[0])["name"]
    d = frappe.get_doc("Purchase Invoice", pi)
    if d.docstatus == 0:
        d.bill_no = "FOLIO-FILAFIL-" + lote[-1]; d.bill_date = nowdate(); d.save(ignore_permissions=True)
        api("validar_documento", doctype="Purchase Invoice", name=pi)
    log("PI tela", pi, frappe.db.get_value("Purchase Invoice", pi, ["docstatus", "grand_total"]))
    for po in s["pos"][lote]:
        prn = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": po, "docstatus": 1}, pluck="parent")[0]
        if frappe.get_all("Purchase Invoice Item", filters={"purchase_receipt": prn, "docstatus": ["<", 2]}):
            continue
        r = api("crear_factura_compra", source_doctype="Purchase Receipt", source_name=prn)
        dd = frappe.get_doc("Purchase Invoice", r["name"])
        dd.bill_no = "FOLIO-" + po[-3:]; dd.bill_date = nowdate(); dd.save(ignore_permissions=True)
        api("validar_documento", doctype="Purchase Invoice", name=r["name"])
        log("PI", r["name"], dd.supplier, dd.grand_total)
    frappe.db.commit()
