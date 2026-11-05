"""Tablero de Inicio (y Resumen del panel de Dirección): los indicadores del flujo
costeo -> venta -> producción -> facturación, sin sesgos de cálculo.

Reglas, cada una corrige un sesgo que tenía la versión anterior (dashboard_metrics):

- Solo cuenta lo VALIDADO (docstatus 1). Un borrador todavía no es venta ni compra;
  sumarlo inflaba Vendido ~38 % en el sandbox. Los borradores se informan aparte.
- Todo es por PERIODO (fecha del documento) y se compara contra el periodo anterior
  de la misma duración. "Todo" no compara.
- Montos NETOS en moneda de la compañía (base_net_total): el IVA es trasladado.
- Conversión = valor de las cotizaciones GANADAS (status Ordered) / valor cotizado.
  Antes era Vendido / Cotizado, que mezcla OV que no vienen de una cotización.
- Margen PONDERADO por venta: Σ(venta - costo) / Σ venta de los costeos que se
  vendieron en el periodo, cada costeo una vez. Antes era el promedio simple de
  margin_pct por renglón (una talla de 50 piezas pesaba igual que una de 1,000) e
  incluía plantillas y borradores.
- Cobrado: proporción saldada de cada factura contra su total REDONDEADO (el saldo
  pendiente se guarda redondeado: comparar contra el total sin redondear daba -$1.03).
  Si el sistema no tiene ningún cobro registrado, se dice así en vez de mostrar $0.
- Costeos por etapa: sin plantillas (nombre_plantilla) ni versiones reemplazadas.
- Maquila: una orden a taller cuenta como recibida solo al 100 %; además se da el
  avance ponderado por importe. Antes bastaba un recibo parcial.
- Serie mensual: meses completos, con ceros donde no hubo movimiento.
"""
import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, nowdate

PERIODOS = {
    "mes": _("Este mes"),
    "trimestre": _("Este trimestre"),
    "anio": _("Este año"),
    "12m": _("Últimos 12 meses"),
    "todo": _("Todo"),
}
ETAPAS = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado"]
_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _rango(periodo):
    """(desde, hasta, desde_anterior, hasta_anterior) -- fechas inclusive."""
    hoy = getdate(nowdate())
    if periodo == "mes":
        desde = get_first_day(hoy)
    elif periodo == "trimestre":
        desde = getdate(f"{hoy.year}-{((hoy.month - 1) // 3) * 3 + 1:02d}-01")
    elif periodo == "anio":
        desde = getdate(f"{hoy.year}-01-01")
    elif periodo == "12m":
        desde = get_first_day(add_months(hoy, -11))
    else:
        return None, None, None, None
    dias = (hoy - desde).days
    hasta_ant = add_days(desde, -1)
    # El periodo anterior equivalente: mismo número de días transcurridos, para que la
    # comparación no castigue a un mes que va a la mitad contra uno completo.
    desde_ant = {"mes": get_first_day(hasta_ant), "trimestre": add_months(desde, -3),
                 "anio": getdate(f"{hoy.year - 1}-01-01"), "12m": add_months(desde, -12)}[periodo]
    hasta_ant = min(getdate(hasta_ant), getdate(add_days(desde_ant, dias)))
    return desde, hoy, getdate(desde_ant), hasta_ant


def _filtro(campo_fecha, desde, hasta, company, campo_compania="company", alias=""):
    a = f"{alias}." if alias else ""
    cond, vals = [f"{a}docstatus = 1"], []
    if desde:
        cond.append(f"{a}`{campo_fecha}` between %s and %s")
        vals += [desde, hasta]
    if company:
        cond.append(f"{a}`{campo_compania}` = %s")
        vals.append(company)
    return " and ".join(cond), vals


def _suma(doctype, campo_fecha, desde, hasta, company, campo="base_net_total", extra=""):
    cond, vals = _filtro(campo_fecha, desde, hasta, company)
    r = frappe.db.sql(f"select coalesce(sum({campo}), 0) from `tab{doctype}` where {cond} {extra}", vals)
    return flt(r[0][0])


def _ventas(desde, hasta, company):
    vendido = _suma("Sales Order", "transaction_date", desde, hasta, company)
    prendas = _suma("Sales Order", "transaction_date", desde, hasta, company, campo="total_qty")
    cond, vals = _filtro("transaction_date", desde, hasta, company)
    ordenes = frappe.db.sql(f"select count(*) from `tabSales Order` where {cond}", vals)[0][0]

    # Órdenes de venta que NO vienen de una cotización: explican por qué "Vendido"
    # puede ser mayor que "Cotizaciones ganadas" sin que haya un error.
    cond_so, vals_so = _filtro("transaction_date", desde, hasta, company, alias="so")
    vendido_directo = flt(frappe.db.sql(f"""
        select coalesce(sum(so.base_net_total), 0) from `tabSales Order` so
        where {cond_so}
          and not exists (select 1 from `tabSales Order Item` i where i.parent = so.name and ifnull(i.prevdoc_docname, '') != '')""",
        vals_so)[0][0])

    cotizado = _suma("Quotation", "transaction_date", desde, hasta, company)
    ganado = _suma("Quotation", "transaction_date", desde, hasta, company, extra="and status = 'Ordered'")
    perdido = _suma("Quotation", "transaction_date", desde, hasta, company, extra="and status = 'Lost'")

    facturado = _suma("Sales Invoice", "posting_date", desde, hasta, company)
    cond, vals = _filtro("posting_date", desde, hasta, company)
    cobrado = frappe.db.sql(f"""
        select coalesce(sum(base_net_total * least(1, greatest(0,
               1 - outstanding_amount / nullif(if(rounded_total > 0, rounded_total, grand_total), 0)))), 0)
        from `tabSales Invoice` where {cond} and is_return = 0""", vals)[0][0]

    # Margen ponderado de lo vendido, según el costeo de cada OV (cada costeo una vez).
    cond, vals = _filtro("transaction_date", desde, hasta, company)
    m = frappe.db.sql(f"""
        select coalesce(sum(cp.total_sales_price), 0) venta,
               coalesce(sum(cp.total_sales_price - cp.qty * cp.total_unit_cost), 0) utilidad
        from `tabCosteo Producto` cp
        where cp.parent in (select distinct costeo from `tabSales Order`
                            where {cond} and ifnull(costeo, '') != '')""", vals, as_dict=True)[0]
    margen = (flt(m.utilidad) / flt(m.venta) * 100) if flt(m.venta) else None
    return {
        "vendido": vendido, "prendas": prendas, "ordenes": ordenes, "vendido_directo": vendido_directo,
        "cotizado": cotizado, "ganado": ganado, "perdido": perdido,
        "conversion": (ganado / cotizado * 100) if cotizado else None,
        "facturado": facturado, "cobrado": flt(cobrado), "margen": margen,
        # Utilidad estimada de lo vendido, con la MISMA base que el margen (el costeo de
        # cada OV). Antes era "facturado − todas las compras", que mezcla compras de
        # pedidos que todavía no se facturan.
        "utilidad": flt(m.utilidad), "venta_costeada": flt(m.venta),
    }


def _compras(desde, hasta, company):
    return {
        "material": _suma("Purchase Order", "transaction_date", desde, hasta, company, extra="and is_subcontracted = 0"),
        "maquila": _suma("Purchase Order", "transaction_date", desde, hasta, company, extra="and is_subcontracted = 1"),
    }


def _delta(actual, anterior):
    if anterior in (None, 0) or actual is None:
        return None
    return (actual - anterior) / abs(anterior) * 100


def _exigir_finanzas():
    from costeo_yelke.roles import puede_ver_finanzas

    if not puede_ver_finanzas():
        frappe.throw(_("Las cifras financieras son para Dirección."), frappe.PermissionError)


def _composicion(desde, hasta, company):
    """De cada peso vendido, cuánto es materia prima, maquila, otros costos, overhead y
    utilidad: los costeos que se vendieron en el periodo, ponderados por la cantidad de
    cada producto (la misma base que el margen)."""
    cond, vals = _filtro("transaction_date", desde, hasta, company)
    r = frappe.db.sql(f"""
        select coalesce(sum(cp.total_sales_price), 0) venta,
               coalesce(sum(cp.qty * cp.material_cost), 0) material,
               coalesce(sum(cp.qty * cp.services_cost), 0) maquila,
               coalesce(sum(cp.qty * (cp.shipping_cost + cp.labeling_cost + cp.packaging_cost)), 0) otros,
               coalesce(sum(cp.qty * cp.overhead_amt), 0) overhead,
               coalesce(sum(cp.total_sales_price - cp.qty * cp.total_unit_cost), 0) utilidad
        from `tabCosteo Producto` cp
        where cp.parent in (select distinct costeo from `tabSales Order` where {cond} and ifnull(costeo, '') != '')""",
                      vals, as_dict=True)[0]
    partes = [("material", _("Materia prima")), ("maquila", _("Maquila")), ("otros", _("Envío, etiquetas y empaque")),
              ("overhead", _("Gastos")), ("utilidad", _("Utilidad"))]
    return {"venta": flt(r.venta), "partes": [{"clave": k, "etiqueta": e, "monto": flt(r[k])} for k, e in partes]}


@frappe.whitelist()
def get_tablero(company: str = None, periodo: str = "anio") -> dict:
    """Tablero FINANCIERO (Dirección, Supervisor, Analista de costos). El resto del
    equipo ve get_tablero_operativo."""
    _exigir_finanzas()
    periodo = periodo if periodo in PERIODOS else "anio"
    company = company or None
    desde, hasta, desde_ant, hasta_ant = _rango(periodo)

    v = _ventas(desde, hasta, company)
    c = _compras(desde, hasta, company)
    previo = None
    if desde:
        va, ca = _ventas(desde_ant, hasta_ant, company), _compras(desde_ant, hasta_ant, company)
        previo = {
            "desde": str(desde_ant), "hasta": str(hasta_ant),
            "vendido": _delta(v["vendido"], va["vendido"]),
            "facturado": _delta(v["facturado"], va["facturado"]),
            "prendas": _delta(v["prendas"], va["prendas"]),
            "cotizado": _delta(v["cotizado"], va["cotizado"]),
            "compras": _delta(c["material"] + c["maquila"], ca["material"] + ca["maquila"]),
            # El margen se compara en PUNTOS, no en % de cambio.
            "margen_pts": (v["margen"] - va["margen"]) if v["margen"] is not None and va["margen"] is not None else None,
        }

    # Borradores: lo que viene (no se suma a lo validado).
    borradores = {}
    for dt, campo in (("Quotation", "transaction_date"), ("Sales Order", "transaction_date"),
                      ("Purchase Order", "transaction_date"), ("Sales Invoice", "posting_date")):
        filtros = {"docstatus": 0, **({"company": company} if company else {})}
        fila = frappe.get_all(dt, filters=filtros, fields=["count(name) as n", "sum(base_net_total) as t"])[0]
        borradores[dt] = {"n": fila.n or 0, "monto": flt(fila.t)}

    return {
        "usuario": frappe.utils.get_fullname(frappe.session.user),
        "periodo": periodo, "etiqueta": PERIODOS[periodo], "desde": str(desde) if desde else None,
        "hasta": str(hasta) if hasta else None, "periodos": PERIODOS,
        "moneda": (frappe.db.get_value("Company", company, "default_currency") if company else None)
                  or frappe.db.get_default("currency") or "MXN",
        "ventas": v, "compras": c, "previo": previo, "borradores": borradores,
        "cobros_registrados": bool(frappe.db.exists("Payment Entry Reference",
                                                    {"reference_doctype": "Sales Invoice", "docstatus": 1})),
        "serie": _serie_mensual(desde, hasta, company, periodo),
        "composicion": _composicion(desde, hasta, company),
        "costeos": _costeos_por_etapa(company),
        "produccion": _produccion(company),
        "clientes": _top("Sales Order", "customer", "customer_name", "transaction_date", desde, hasta, company),
        "talleres": _top("Purchase Order", "supplier", "supplier_name", "transaction_date", desde, hasta, company,
                         extra="and is_subcontracted = 1"),
        "proveedores": _top("Purchase Order", "supplier", "supplier_name", "transaction_date", desde, hasta, company,
                            extra="and is_subcontracted = 0"),
    }


def _serie_mensual(desde, hasta, company, periodo):
    """Vendido y facturado por mes, meses completos y con ceros. 'Este mes' o
    'Trimestre' son muy cortos para una serie: se muestran los últimos 6 meses."""
    hoy = getdate(nowdate())
    meses = 12 if periodo in ("anio", "12m", "todo") else 6
    inicio = get_first_day(add_months(hoy, -(meses - 1)))
    if periodo == "anio":
        inicio = getdate(f"{hoy.year}-01-01")
        meses = hoy.month
    fin = get_last_day(hoy)
    datos = {}
    for dt, campo, clave in (("Sales Order", "transaction_date", "vendido"), ("Sales Invoice", "posting_date", "facturado"),
                             ("Purchase Order", "transaction_date", "compras")):
        cond, vals = _filtro(campo, inicio, fin, company)
        for r in frappe.db.sql(f"""select date_format(`{campo}`, '%%Y-%%m') mes, sum(base_net_total) t
                                   from `tab{dt}` where {cond} group by mes""", vals, as_dict=True):
            datos.setdefault(r.mes, {})[clave] = flt(r.t)
    salida = []
    for i in range(meses):
        d = add_months(inicio, i)
        k = f"{d.year}-{d.month:02d}"
        salida.append({"mes": k, "etiqueta": f"{_MESES[d.month - 1]} {str(d.year)[2:]}",
                       "vendido": datos.get(k, {}).get("vendido", 0.0), "facturado": datos.get(k, {}).get("facturado", 0.0),
                       "compras": datos.get(k, {}).get("compras", 0.0)})
    return salida


def _costeos_por_etapa(company):
    """Estado actual (no depende del periodo). Sin plantillas ni versiones reemplazadas
    (docstatus 2 = cancelado o sustituido por una revisión)."""
    cond, vals = ["ifnull(nombre_plantilla, '') = ''", "docstatus < 2"], []
    if company:
        cond.append("`compañia` = %s")
        vals.append(company)
    filas = frappe.db.sql(f"""select ifnull(costeo_status, 'Borrador') estado, docstatus, count(*) n
                              from tabCosteo where {' and '.join(cond)} group by estado, docstatus""", vals, as_dict=True)
    etapas = {e: 0 for e in ETAPAS}
    cancelados, en_captura = 0, 0
    for f in filas:
        if f.estado == "Cancelado":
            cancelados += f.n
            continue
        if f.estado == "Borrador" and f.docstatus == 0:
            en_captura += f.n
        etapas[f.estado if f.estado in etapas else "Borrador"] += f.n
    return {"etapas": [{"etapa": e, "n": etapas[e]} for e in ETAPAS], "cancelados": cancelados,
            "en_captura": en_captura, "total": sum(etapas.values())}


def _produccion(company):
    """Órdenes a taller validadas de los costeos que siguen vivos: completas solo al
    100 % recibido, y el avance ponderado por importe."""
    cond, vals = ["po.docstatus = 1", "po.is_subcontracted = 1",
                  "(c.name is null or c.costeo_status not in ('Completado', 'Cancelado'))"], []
    if company:
        cond.append("po.company = %s")
        vals.append(company)
    r = frappe.db.sql(f"""
        select count(*) total, sum(po.per_received >= 99.99) completas,
               sum(po.base_net_total * least(po.per_received, 100) / 100) recibido, sum(po.base_net_total) importe
        from `tabPurchase Order` po left join tabCosteo c on c.name = po.costeo
        where {' and '.join(cond)}""", vals, as_dict=True)[0]
    importe = flt(r.importe)
    return {"total": int(r.total or 0), "completas": int(flt(r.completas)),
            "avance": (flt(r.recibido) / importe * 100) if importe else None}


def _top(doctype, campo, campo_nombre, campo_fecha, desde, hasta, company, extra="", limite=5):
    """Los `limite` principales y el resto como 'Otros' (para no ocultar cuánto pesan)."""
    cond, vals = _filtro(campo_fecha, desde, hasta, company)
    filas = frappe.db.sql(f"""select `{campo}` clave, max(`{campo_nombre}`) nombre, sum(base_net_total) monto,
                                     count(*) n
                              from `tab{doctype}` where {cond} {extra} group by `{campo}` order by monto desc""",
                          vals, as_dict=True)
    total = sum(flt(f.monto) for f in filas)
    salida = [{"clave": f.clave, "nombre": f.nombre or f.clave, "monto": flt(f.monto), "n": f.n} for f in filas[:limite]]
    resto = filas[limite:]
    if resto:
        salida.append({"clave": None, "nombre": _("Otros ({0})").format(len(resto)),
                       "monto": sum(flt(f.monto) for f in resto), "n": sum(f.n for f in resto)})
    return {"filas": salida, "total": total}


# ─────────────────────────────────────────────────────────────────────────────
# Tablero OPERATIVO: para todo el equipo, sin cifras financieras de la empresa
# ─────────────────────────────────────────────────────────────────────────────

def _costeos_vivos_sql(alias="po"):
    return (f"({alias}.costeo is null or {alias}.costeo = '' or {alias}.costeo not in "
            "(select name from tabCosteo where costeo_status in ('Completado', 'Cancelado')))")


def _mi_trabajo(user):
    from costeo_yelke.api.aprobaciones import DOCUMENTOS_CON_APROBACION, get_mis_devueltos

    hace7 = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-7)
    borradores = en_aprobacion = aprobados = 0
    for dt in DOCUMENTOS_CON_APROBACION:
        extra = {"nombre_plantilla": ["in", ["", None]]} if dt == "Costeo" else {}
        borradores += frappe.db.count(dt, {"owner": user, "docstatus": 0, "estado_aprobacion_yelke": ["in", ["Borrador", "", None]], **extra})
        en_aprobacion += frappe.db.count(dt, {"enviado_aprobacion_por": user, "docstatus": 0,
                                              "estado_aprobacion_yelke": ["in", ["Pendiente", "Revisado"]]})
        aprobados += frappe.db.count(dt, {"enviado_aprobacion_por": user, "aprobado_en_yelke": [">=", hace7]})
    return {"borradores": borradores, "en_aprobacion": en_aprobacion,
            "regresados": len(get_mis_devueltos()["items"]), "aprobados_7d": aprobados}


def _entregas(company):
    """Prendas pendientes de entregar de las OV validadas, por semana de su fecha de
    entrega (lo vencido aparte), y las más próximas."""
    hoy = getdate(nowdate())
    lunes = add_days(hoy, -hoy.weekday())
    cond, vals = ["so.docstatus = 1", "so.per_delivered < 99.99", "so.status not in ('Closed', 'Completed')"], []
    if company:
        cond.append("so.company = %s")
        vals.append(company)
    filas = frappe.db.sql(f"""
        select so.name, so.customer_name, so.delivery_date, so.total_qty, so.per_delivered, so.costeo,
               c.titulo
        from `tabSales Order` so left join tabCosteo c on c.name = so.costeo
        where {' and '.join(cond)} order by so.delivery_date asc""", vals, as_dict=True)
    semanas = [{"etiqueta": _("Vencido"), "prendas": 0.0, "vencido": True}]
    for i in range(8):
        ini = add_days(lunes, 7 * i)
        semanas.append({"etiqueta": _("Esta sem.") if i == 0 else f"{getdate(ini).day} {_MESES[getdate(ini).month - 1]}",
                        "desde": str(ini), "prendas": 0.0})
    for f in filas:
        pendiente = flt(f.total_qty) * (1 - flt(f.per_delivered) / 100)
        f.pendiente = pendiente
        if f.delivery_date and getdate(f.delivery_date) < hoy:
            semanas[0]["prendas"] += pendiente
            continue
        i = ((getdate(f.delivery_date) - lunes).days // 7) if f.delivery_date else 99
        if 0 <= i < 8:
            semanas[i + 1]["prendas"] += pendiente
    proximas = [{"name": f.name, "proyecto": f.titulo or f.costeo or f.name, "cliente": f.customer_name,
                 "costeo": f.costeo, "fecha": str(f.delivery_date) if f.delivery_date else None,
                 "prendas": flt(f.total_qty), "pendiente": round(f.pendiente), "entregado_pct": round(flt(f.per_delivered)),
                 "vencida": bool(f.delivery_date and getdate(f.delivery_date) < hoy)} for f in filas[:6]]
    return {"semanas": semanas, "proximas": proximas, "abiertas": len(filas),
            "vencidas": sum(1 for f in filas if f.delivery_date and getdate(f.delivery_date) < hoy)}


def _compras_estado(company, subcontratadas):
    cond, vals = ["po.docstatus = 1", f"po.is_subcontracted = {1 if subcontratadas else 0}", _costeos_vivos_sql()], []
    if company:
        cond.append("po.company = %s")
        vals.append(company)
    r = frappe.db.sql(f"""
        select sum(po.per_received <= 0) por_recibir, sum(po.per_received > 0 and po.per_received < 99.99) parcial,
               sum(po.per_received >= 99.99) recibidas, count(*) total,
               sum(po.per_received < 99.99 and po.schedule_date < curdate()) vencidas,
               sum(po.per_received >= 99.99 and po.per_billed < 99.99) por_facturar
        from `tabPurchase Order` po where {' and '.join(cond)}""", vals, as_dict=True)[0]
    return {k: int(flt(r[k])) for k in ("por_recibir", "parcial", "recibidas", "total", "vencidas", "por_facturar")}


def _talleres_avance(company):
    """Avance por taller de las órdenes a taller abiertas (sin importes)."""
    cond, vals = ["po.docstatus = 1", "po.is_subcontracted = 1", _costeos_vivos_sql()], []
    if company:
        cond.append("po.company = %s")
        vals.append(company)
    filas = frappe.db.sql(f"""
        select po.supplier clave, max(po.supplier_name) nombre, count(*) n, avg(least(po.per_received, 100)) avance,
               sum(po.per_received < 99.99 and po.schedule_date < curdate()) vencidas
        from `tabPurchase Order` po where {' and '.join(cond)} group by po.supplier
        order by avance asc, n desc""", vals, as_dict=True)
    return [{"nombre": f.nombre or f.clave, "ordenes": f.n, "avance": round(flt(f.avance)), "vencidas": int(flt(f.vencidas))}
            for f in filas]


@frappe.whitelist()
def get_tablero_operativo(company: str = None) -> dict:
    """Inicio para el equipo: su trabajo y el estado de la operación (entregas, compras,
    talleres, facturas por capturar). Cantidades y fechas, sin cifras financieras."""
    company = company or None
    filtros_pi = {"docstatus": 0, **({"company": company} if company else {})}
    return {
        "usuario": frappe.utils.get_fullname(frappe.session.user),
        "mi_trabajo": _mi_trabajo(frappe.session.user),
        "entregas": _entregas(company),
        "compras": _compras_estado(company, subcontratadas=False),
        "maquila": _compras_estado(company, subcontratadas=True),
        "talleres": _talleres_avance(company),
        "facturas_borrador": frappe.db.count("Purchase Invoice", filtros_pi),
        "costeos": _costeos_por_etapa(company),
    }
