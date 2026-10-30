"""Panel de Dirección: detalle de un documento por aprobar, proyectos y resumen
(docs/plan-panel-direccion.md §4). Las acciones (aprobar, regresar...) viven en
api/aprobaciones.py; aquí solo se lee.

Lo que se muestra de cada documento es lo que decide su aprobación: montos,
contraparte, margen o costo, y las alertas que ya conoce el sistema.
"""
import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, nowdate

from costeo_yelke.api.aprobaciones import (
    DOCUMENTOS_CON_APROBACION, EN_APROBACION, _etiqueta, _nombre, _ruta_doc, _tarjetas, _campos,
    compania_de, estado_aprobacion,
)
from costeo_yelke.roles import (
    nivel_aprobacion, puede_aprobar_documentos, puede_aprobar_precios, puede_revisar_documentos,
    puede_ver_panel_direccion,
)

_CAIDA_MARGEN = 5  # puntos: avisar si el margen baja esto o más contra la versión anterior


def _exigir_bandeja():
    if not (puede_aprobar_documentos() or puede_revisar_documentos() or puede_aprobar_precios()):
        frappe.throw(_("No tienes acceso al panel de aprobaciones."), frappe.PermissionError)


def _exigir_director():
    if not puede_ver_panel_direccion():
        frappe.throw(_("Esta vista es solo para Dirección."), frappe.PermissionError)


def _m(etiqueta, valor, moneda=None):
    return {"etiqueta": etiqueta, "valor": flt(valor), "tipo": "moneda", "moneda": moneda or "MXN"}


def _t(etiqueta, valor):
    return {"etiqueta": etiqueta, "valor": valor if valor not in (None, "") else "—", "tipo": "texto"}


def _f(etiqueta, valor):
    return {"etiqueta": etiqueta, "valor": str(valor) if valor else None, "tipo": "fecha"}


def _p(etiqueta, valor):
    return {"etiqueta": etiqueta, "valor": flt(valor), "tipo": "porcentaje"}


def _renglones(doc, moneda):
    return [{
        "descripcion": it.get("item_name") or it.item_code,
        "cantidad": flt(it.qty), "unidad": (it.get("uom") or "").split(" - ")[-1],
        "precio": flt(it.rate), "importe": flt(it.amount), "moneda": moneda,
    } for it in doc.get("items") or []]


def _adjuntos(doc, campos=()):
    archivos = frappe.get_all("File", filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name,
                                               "is_folder": 0},
                              fields=["file_name", "file_url"], order_by="creation asc")
    vistos = {a.file_url for a in archivos}
    for campo in campos:
        url = doc.get(campo)
        if url and url not in vistos:
            archivos.append(frappe._dict(file_name=url.rsplit("/", 1)[-1], file_url=url))
    return [{"nombre": a.file_name, "url": a.file_url} for a in archivos]


def _impuestos(doc, moneda):
    return [_m(t.description or t.account_head, t.tax_amount if t.get("add_deduct_tax") != "Deduct" else -flt(t.tax_amount), moneda)
            for t in doc.get("taxes") or [] if flt(t.tax_amount)]


def _margen_costeo(costeo):
    filas = frappe.get_all("Costeo Producto", filters={"parent": costeo}, fields=["margin_pct"])
    vals = [flt(f.margin_pct) for f in filas if flt(f.margin_pct)]
    return sum(vals) / len(vals) if vals else None


def _uom(u):
    return (u or "").split(" - ")[-1]


def _desglose_costeo(costeo, moneda):
    """De qué está hecho cada producto del costeo, por prenda: el costo unitario por
    concepto, la lista de materiales (con su cantidad por prenda y proveedor) y los
    servicios de cada etapa (con su taller). Es lo que Dirección necesita para decidir
    si el precio y el margen tienen sentido."""
    productos = frappe.get_all(
        "Costeo Producto", filters={"parent": costeo},
        fields=["finished_item", "talla_grupo_label", "variante_talla_de", "qty", "material_cost", "services_cost",
                "shipping_cost", "labeling_cost", "packaging_cost", "overhead_pct", "overhead_amt", "total_unit_cost",
                "unit_sales_price", "margin_pct", "total_sales_price"], order_by="idx asc")
    detalle = frappe.get_all(
        "Costeo Producto Detalle", filters={"parent": costeo},
        fields=["finished_item", "concept_type", "item", "tipo_material", "internal_qty", "internal_uom", "unit_price",
                "total", "supplier", "subensamblaje"], order_by="idx asc")
    etapas = frappe.get_all(
        "Etapas Costeo", filters={"parent": costeo},
        fields=["producto_terminado", "etapa", "servicio", "proveedor", "precio_servicio", "lote_qty", "subensamblaje"],
        order_by="idx asc")
    codigos = {d.item for d in detalle if d.item} | {e.servicio for e in etapas if e.servicio} | {p.finished_item for p in productos}
    nombres = dict(frappe.get_all("Item", filters={"name": ["in", list(codigos)]}, fields=["name", "item_name"],
                                  as_list=True)) if codigos else {}
    nombre = lambda c: nombres.get(c) or c

    salida = []
    for p in productos:
        costos = [(_("Materia prima"), p.material_cost), (_("Servicios (maquila)"), p.services_cost),
                  (_("Envío"), p.shipping_cost), (_("Etiquetado"), p.labeling_cost), (_("Empaque"), p.packaging_cost),
                  (_("Overhead {0} %").format(round(flt(p.overhead_pct), 2)), p.overhead_amt)]
        materiales = [{
            "descripcion": nombre(d.item), "tipo": d.tipo_material or (_("Envío") if d.concept_type == "Envío" else ""),
            "cantidad": flt(d.internal_qty), "unidad": _uom(d.internal_uom), "precio_unitario": flt(d.unit_price),
            "total": flt(d.total), "proveedor": d.supplier, "pieza": d.subensamblaje,
        } for d in detalle if d.finished_item == p.finished_item and d.concept_type in ("Materia Prima", "Envío")]
        servicios = [{
            # Los artículos de servicio suelen llamarse igual que su código ("SERVICIO-DE-CORTE").
            "descripcion": nombre(e.servicio).replace("-", " ") if nombre(e.servicio) == e.servicio else nombre(e.servicio),
            "etapa": e.etapa, "pieza": e.subensamblaje, "proveedor": e.proveedor,
            "total": flt(e.precio_servicio) / (flt(e.lote_qty) if flt(e.lote_qty) > 1 else 1),
        } for e in etapas if e.producto_terminado == p.finished_item]
        salida.append({
            "producto": nombre(p.finished_item), "talla": p.talla_grupo_label, "cantidad": cint(p.qty), "moneda": moneda,
            "costo_unitario": flt(p.total_unit_cost), "precio": flt(p.unit_sales_price), "margen": flt(p.margin_pct),
            "venta_total": flt(p.total_sales_price),
            "costos": [{"concepto": c, "monto": flt(m)} for c, m in costos if flt(m)],
            "materiales": materiales, "servicios": servicios,
        })
    return salida


def _resumen_costeo(doc):
    moneda = frappe.db.get_value("Company", doc.get("compañia") or doc.get("company"), "default_currency") or "MXN"
    productos = doc.get("costeo_producto") or []
    venta = sum(flt(p.total_sales_price) for p in productos)
    prendas = sum(cint(p.qty) for p in productos)
    margen = _margen_costeo(doc.name)
    alertas, resumen = [], [_t(_("Cliente"), doc.get("cliente")), _t(_("Título"), doc.get("titulo")),
                            _t(_("Prendas"), f"{prendas:,}"), _m(_("Venta total"), venta, moneda)]
    if margen is not None:
        resumen.append(_p(_("Margen promedio"), margen))
    anterior = doc.get("amended_from")
    if anterior:
        resumen.append(_t(_("Revisión de"), anterior))
        previo = _margen_costeo(anterior)
        if margen is not None and previo is not None and previo - margen >= _CAIDA_MARGEN:
            alertas.append({"tono": "wait", "texto": _("El margen bajó de {0} % a {1} % contra la versión anterior.")
                            .format(round(previo, 1), round(margen, 1))})
    if doc.get("motivo_revision"):
        resumen.append(_t(_("Motivo de la revisión"), doc.motivo_revision))
    return resumen, [], alertas, moneda


def _resumen_venta(doc):
    moneda = doc.currency
    resumen = [_t(_("Cliente"), doc.get("customer_name") or doc.get("party_name") or doc.get("customer")),
               _m(_("Subtotal"), doc.net_total, moneda), *_impuestos(doc, moneda), _m(_("Total"), doc.grand_total, moneda)]
    alertas = []
    if doc.get("costeo"):
        margen = _margen_costeo(doc.costeo)
        if margen is not None:
            resumen.append(_p(_("Margen del costeo"), margen))
        resumen.append(_t(_("Costeo"), doc.costeo))
    if doc.doctype == "Quotation":
        resumen.append(_f(_("Vigente hasta"), doc.get("valid_till")))
    else:
        resumen.append(_f(_("Entrega"), doc.delivery_date))
        if doc.delivery_date and getdate(doc.delivery_date) < getdate(nowdate()):
            alertas.append({"tono": "wait", "texto": _("La fecha de entrega ({0}) ya pasó.")
                            .format(frappe.utils.formatdate(doc.delivery_date))})
        cotizacion = next((it.prevdoc_docname for it in doc.items if it.get("prevdoc_docname")), None)
        if cotizacion:
            resumen.append(_t(_("Cotización"), cotizacion))
        if doc.meta.has_field("oc_cliente_archivo"):
            resumen.append(_t(_("OC del cliente"), _("adjunta") if doc.get("oc_cliente_archivo") else _("— sin adjuntar")))
            if not doc.get("oc_cliente_archivo"):
                alertas.append({"tono": "bad", "texto": _("Falta adjuntar la OC del cliente. Sin ella no se puede aprobar.")})
    return resumen, _renglones(doc, moneda), alertas, moneda


def _resumen_compra(doc):
    moneda = doc.currency
    empresa = frappe.db.get_value("Company", doc.company, "default_currency")
    sub = doc.doctype == "Purchase Order" and doc.get("is_subcontracted")
    resumen = [_t(_("Taller") if sub else _("Proveedor"), doc.get("supplier_name") or doc.supplier)]
    if doc.doctype == "Purchase Invoice" and doc.get("bill_no"):
        resumen.append(_t(_("Folio del proveedor"), doc.bill_no))
    resumen += [_m(_("Subtotal"), doc.net_total, moneda), *_impuestos(doc, moneda), _m(_("Total"), doc.grand_total, moneda)]
    if empresa and moneda != empresa:
        resumen.append(_t(_("Tipo de cambio"), f"1 {moneda} = {flt(doc.conversion_rate, 4)} {empresa}"))
        resumen.append(_m(_("Total en {0}").format(empresa), doc.base_grand_total, empresa))
    if doc.doctype == "Purchase Order":
        resumen.append(_f(_("Entrega"), doc.schedule_date))
        if doc.get("lote_ref"):
            resumen.append(_t(_("Lote"), doc.lote_ref))
    if doc.get("costeo"):
        resumen.append(_t(_("Costeo"), doc.costeo))
    if doc.doctype == "Purchase Invoice":
        respaldo = sorted({it.purchase_order for it in doc.items if it.get("purchase_order")}
                          | {it.purchase_receipt for it in doc.items if it.get("purchase_receipt")})
        if doc.get("flete_origen"):
            respaldo.append(doc.flete_origen)
        if respaldo:
            resumen.append(_t(_("Respaldo"), ", ".join(respaldo)))
    alertas = []
    if (doc.doctype == "Purchase Invoice" and doc.meta.has_field("factura_pdf") and not doc.get("factura_pdf")
            and not frappe.db.get_value("Supplier", doc.supplier, "sin_alta_sat")):  # sin alta en el SAT: no emite factura
        alertas.append({"tono": "bad", "texto": _("Falta el PDF de la factura. Sin él no se puede aprobar.")})
    return resumen, _renglones(doc, moneda), alertas, moneda


def _resumen_precios(costeo):
    filas = frappe.get_all("Item Price", filters={"costeo": costeo, "precio_acordado_validado": 0},
                           fields=["item_code", "item_name", "customer", "price_list_rate", "currency",
                                   "valid_from", "valid_upto", "owner", "modified"], order_by="item_code asc")
    costos = {p.finished_item: flt(p.total_unit_cost) for p in frappe.get_all(
        "Costeo Producto", filters={"parent": costeo}, fields=["finished_item", "total_unit_cost"])}
    renglones, alertas = [], []
    for f in filas:
        costo = costos.get(f.item_code)
        margen = (1 - costo / flt(f.price_list_rate)) * 100 if costo and flt(f.price_list_rate) else None
        renglones.append({"descripcion": f.item_name or f.item_code, "cantidad": None, "unidad": "",
                          "precio": flt(f.price_list_rate), "importe": flt(f.price_list_rate), "moneda": f.currency,
                          "nota": (_("costo {0} · margen {1} %").format(frappe.utils.fmt_money(costo, currency=f.currency),
                                                                         round(margen, 1)) if margen is not None else "")})
        if margen is not None and margen < 0:
            alertas.append({"tono": "bad", "texto": _("{0}: el precio está por debajo del costo.").format(f.item_name or f.item_code)})
    primero = filas[0] if filas else frappe._dict()
    resumen = [_t(_("Cliente"), primero.get("customer")), _t(_("Precios"), str(len(filas))),
               _f(_("Vigente desde"), primero.get("valid_from")), _f(_("Vigente hasta"), primero.get("valid_upto")),
               _t(_("Costeo"), costeo)]
    return resumen, renglones, alertas, primero.get("currency") or "MXN", primero


@frappe.whitelist()
def get_resumen_documento(doctype: str, name: str, tipo: str = None) -> dict:
    """Ficha del detalle en el panel. `tipo='precio'` = los precios acordados del costeo."""
    _exigir_bandeja()
    if tipo == "precio":
        resumen, renglones, alertas, moneda, primero = _resumen_precios(name)
        compania = compania_de("Costeo", name)
        return {
            "doctype": "Costeo", "name": name, "tipo": "precio", "etiqueta": _("Precio acordado"),
            "compania": compania, "desglose": _desglose_costeo(name, moneda),
            "titulo": primero.get("customer") or name, "monto": None, "moneda": moneda,
            "por_nombre": _nombre(primero.owner) if primero.get("owner") else None, "enviado_en": primero.get("modified"),
            "resumen": [_t(_("Compañía"), compania), *resumen], "renglones": renglones, "adjuntos": [], "alertas": alertas,
            "ruta": _ruta_doc("Costeo", name), "estado": {"aplica": True, "nivel": "simple", "estado": "Pendiente",
                                                          "puede_aprobar": puede_aprobar_precios(),
                                                          "puede_regresar": puede_aprobar_precios()},
        }
    if not nivel_aprobacion(doctype):
        frappe.throw(_("{0} no pasa por aprobación.").format(_(doctype)))
    doc = frappe.get_doc(doctype, name)
    if doctype == "Costeo":
        resumen, renglones, alertas, moneda = _resumen_costeo(doc)
        adjuntos = _adjuntos(doc)
    elif doctype in ("Quotation", "Sales Order"):
        resumen, renglones, alertas, moneda = _resumen_venta(doc)
        adjuntos = _adjuntos(doc, ("oc_cliente_archivo",))
    else:
        resumen, renglones, alertas, moneda = _resumen_compra(doc)
        adjuntos = _adjuntos(doc, ("factura_pdf", "factura_xml"))
    tarjeta = (_tarjetas(doctype, frappe.get_all(doctype, filters={"name": name}, fields=_campos(doctype))) or [{}])[0]
    if doc.get("cambio_tras_envio"):
        alertas.insert(0, {"tono": "wait", "texto": _("Cambió después de enviarse a aprobación. Revisa la actividad.")})
    compania = tarjeta.get("compania") or compania_de(doctype, name)
    return {**tarjeta, "compania": compania, "resumen": [_t(_("Compañía"), compania), *resumen],
            "renglones": renglones, "adjuntos": adjuntos, "alertas": alertas,
            "desglose": _desglose_costeo(name, moneda) if doctype == "Costeo" else [],
            "moneda": moneda, "ruta": _ruta_doc(doctype, name), "estado": estado_aprobacion(doctype, name)}


# ─────────────────────────────────────────────────────────────────────────────
# Proyectos y resumen (solo Director)
# ─────────────────────────────────────────────────────────────────────────────

_ETAPA = {"Borrador": 1, "Cotizado": 2, "Orden de Venta": 3, "En Producción": 4, "Entregado": 5, "Completado": 6}


@frappe.whitelist()
def get_proyectos() -> dict:
    """Un renglón por costeo vivo (y los completados del último mes): etapa del ciclo,
    entregado, encargos a taller recibidos y alertas de lo que está atascado."""
    _exigir_director()
    hace_un_mes = frappe.utils.add_days(nowdate(), -30)
    costeos = frappe.get_all(
        "Costeo",
        filters={"docstatus": 1, "costeo_status": ["!=", "Cancelado"]},
        or_filters=[["costeo_status", "!=", "Completado"], ["modified", ">=", hace_un_mes]],
        fields=["name", "titulo", "cliente", "costeo_status", "modified", "compañia"],
        order_by="modified desc", limit=60,
    )
    nombres = [c.name for c in costeos]
    if not nombres:
        return {"proyectos": []}
    ovs = {}
    for so in frappe.get_all("Sales Order", filters={"costeo": ["in", nombres], "docstatus": 1},
                             fields=["name", "costeo", "grand_total", "currency", "delivery_date", "per_delivered",
                                     "per_billed", "total_qty"], order_by="creation desc"):
        ovs.setdefault(so.costeo, so)
    cots = {}
    for q in frappe.get_all("Quotation", filters={"costeo": ["in", nombres], "docstatus": ["<", 2]},
                            fields=["name", "costeo", "grand_total", "currency"], order_by="creation desc"):
        cots.setdefault(q.costeo, q)
    encargos = {}
    for po in frappe.get_all("Purchase Order", filters={"costeo": ["in", nombres], "is_subcontracted": 1, "docstatus": 1},
                             fields=["name", "costeo", "per_received"]):
        e = encargos.setdefault(po.costeo, [0, 0])
        e[1] += 1
        if flt(po.per_received) >= 99.99:
            e[0] += 1
    pendientes = {}
    for dt in DOCUMENTOS_CON_APROBACION:
        if dt == "Costeo" or not frappe.get_meta(dt).has_field("costeo"):
            continue
        for r in frappe.get_all(dt, filters={"costeo": ["in", nombres], "docstatus": 0,
                                             "estado_aprobacion_yelke": ["in", list(EN_APROBACION)]}, pluck="costeo"):
            pendientes[r] = pendientes.get(r, 0) + 1

    hoy = getdate(nowdate())
    salida = []
    for c in costeos:
        ov, cot = ovs.get(c.name), cots.get(c.name)
        etapa = _ETAPA.get(c.costeo_status, 1)
        doc_venta = ov or cot
        alertas = []
        atrasado = bool(ov and ov.delivery_date and getdate(ov.delivery_date) < hoy and flt(ov.per_delivered) < 100)
        if atrasado:
            alertas.append({"tono": "bad", "texto": _("Entrega vencida hace {0} días · {1} % entregado").format(
                date_diff(hoy, ov.delivery_date), round(flt(ov.per_delivered)))})
        if pendientes.get(c.name):
            alertas.append({"tono": "wait", "texto": _("{0} documento(s) esperando aprobación").format(pendientes[c.name])})
        recibidos, total = encargos.get(c.name, [0, 0])
        salida.append({
            "name": c.name, "titulo": c.titulo or c.name, "cliente": c.cliente, "estado": c.costeo_status,
            "compania": c.get("compañia"),
            "etapa": etapa, "documento": doc_venta.name if doc_venta else None,
            "monto": flt(doc_venta.grand_total) if doc_venta else None,
            "moneda": doc_venta.currency if doc_venta else "MXN",
            "entrega": ov.delivery_date if ov else None,
            "entregado_pct": round(flt(ov.per_delivered)) if ov else 0,
            "facturado_pct": round(flt(ov.per_billed)) if ov else 0,
            "prendas": flt(ov.total_qty) if ov else None,
            "encargos": [recibidos, total],
            "alertas": alertas,
            "grupo": "completados" if c.costeo_status == "Completado" else ("atrasados" if atrasado else "activos"),
        })
    return {"proyectos": salida}


@frappe.whitelist()
def get_resumen(company: str = None) -> dict:
    """Indicadores del tablero de Inicio (MISMO cálculo, api/tablero.py; aquí del año
    en curso) + lo que requiere atención."""
    _exigir_director()
    from costeo_yelke.api.tablero import get_tablero

    proyectos = get_proyectos()["proyectos"]
    return {
        "tablero": get_tablero(company=company, periodo="anio"),
        "atrasados": sum(1 for p in proyectos if p["grupo"] == "atrasados"),
    }
