"""Mi panel: lo que cada persona tiene pendiente, entre TODOS los proyectos activos
(docs/plan-accesos-ejecucion.md, fase 6).

Una sección por vista que el usuario tiene en "editar" (roles.accesos); cada renglón
trae la ruta exacta dentro del proyecto (paso, vista de Producción, lote) para llegar
con un clic. Solo proyectos vivos (ni Completado ni Cancelado) y consultas directas por
estado de documento -- sin recalcular lotes -- para que cargue rápido.
"""
import frappe
from frappe import _
from frappe.utils import fmt_money

from costeo_yelke.roles import VISTAS, accesos

LIMITE = 12  # renglones por sección; el total se cuenta aparte


def _activos(company=None):
    f = {"docstatus": ["<", 2], "costeo_status": ["not in", ["Completado", "Cancelado"]]}
    if company and frappe.db.has_column("Costeo", "compañia"):
        f["compañia"] = company
    return {c.name: c for c in frappe.get_all("Costeo", filters=f, fields=["name", "titulo", "cliente", "costeo_status", "docstatus", "modified"])}


def _ruta(costeo, step=None, **query):
    q = {"step": step, **query} if step is not None else dict(query)
    return {"name": "CosteoDetail", "params": {"name": costeo}, "query": {k: v for k, v in q.items() if v not in (None, "")}}


def _fila(costeos, costeo, titulo, detalle, ruta, fecha=None):
    c = costeos.get(costeo) or {}
    return {"titulo": titulo, "detalle": detalle, "costeo": costeo, "proyecto": c.get("titulo") or costeo,
            "cliente": c.get("cliente") or "", "ruta": ruta, "fecha": str(fecha or c.get("modified") or "")}


def _pos(costeos, filtros, campos=("name", "costeo", "supplier_name", "lote_ref", "per_received", "per_billed", "grand_total", "currency", "transaction_date")):
    return frappe.get_all("Purchase Order", filters={"costeo": ["in", list(costeos) or [""]], **filtros}, fields=list(campos),
                          order_by="modified desc")


def _docs_de_costeos(doctype, cs, filtros, campos):
    """Documentos de los costeos `cs`. Si el doctype no tiene el campo `costeo` (sitios
    viejos), se liga por su orden de venta."""
    campos = list(dict.fromkeys(["name", *campos]))
    if frappe.db.has_column(doctype, "costeo"):
        return frappe.get_all(doctype, filters={"costeo": ["in", list(cs) or [""]], **filtros},
                              fields=[*campos, "costeo"], order_by="modified desc")
    hijo, campo_ov = {"Delivery Note": ("Delivery Note Item", "against_sales_order"),
                      "Sales Invoice": ("Sales Invoice Item", "sales_order")}[doctype]
    ovs = {o.name: o.costeo for o in frappe.get_all("Sales Order", filters={"costeo": ["in", list(cs) or [""]]}, fields=["name", "costeo"])}
    padres = {}
    for r in frappe.get_all(hijo, filters={campo_ov: ["in", list(ovs) or [""]]}, fields=["parent", campo_ov]):
        padres.setdefault(r.parent, ovs[r[campo_ov]])
    campos = [c for c in campos if frappe.db.has_column(doctype, c) or c == "name"]
    out = frappe.get_all(doctype, filters={"name": ["in", list(padres) or [""]], **filtros}, fields=campos, order_by="modified desc")
    for d in out:
        d["costeo"] = padres[d.name]
    return out


def _seccion_costear(cs):
    return [_fila(cs, c.name, c.titulo or c.name, _("Costeo en borrador"), _ruta(c.name, 0), c.modified)
            for c in cs.values() if c.docstatus == 0]


def _seccion_cotizar(cs):
    out = [_fila(cs, c.name, c.titulo or c.name, _("Validado, falta la cotización"), _ruta(c.name, 1), c.modified)
           for c in cs.values() if c.docstatus == 1 and c.costeo_status == "Borrador"]
    for q in frappe.get_all("Quotation", filters={"costeo": ["in", list(cs) or [""]], "docstatus": 0},
                            fields=["name", "costeo", "modified"]):
        out.append(_fila(cs, q.costeo, q.name, _("Cotización en borrador"), _ruta(q.costeo, 1), q.modified))
    return out


def _seccion_vender(cs):
    out = []
    for q in frappe.get_all("Quotation", filters={"costeo": ["in", list(cs) or [""]], "docstatus": 1, "status": ["in", ["Open", "Replied"]]},
                            fields=["name", "costeo", "modified"]):
        out.append(_fila(cs, q.costeo, q.name, _("Cotización enviada, sin orden de venta"), _ruta(q.costeo, 2), q.modified))
    for so in frappe.get_all("Sales Order", filters={"costeo": ["in", list(cs) or [""]], "docstatus": 0}, fields=["name", "costeo", "modified"]):
        out.append(_fila(cs, so.costeo, so.name, _("Orden de venta en borrador"), _ruta(so.costeo, 2), so.modified))
    return out


def _seccion_alta(cs, paso, texto):
    return [_fila(cs, c.name, c.titulo or c.name, texto, _ruta(c.name, paso), c.modified)
            for c in cs.values() if c.costeo_status == "Orden de Venta"]


def _seccion_preparacion(cs):
    out = []
    for mr in frappe.get_all("Material Request", filters={"costeo": ["in", list(cs) or [""]], "docstatus": 0}, fields=["name", "costeo", "modified"]):
        out.append(_fila(cs, mr.costeo, mr.name, _("Solicitud de material en borrador"), _ruta(mr.costeo, 5, vista="preparacion"), mr.modified))
    for po in _pos(cs, {"is_subcontracted": 1, "docstatus": 0}):
        out.append(_fila(cs, po.costeo, po.name, _("Orden a taller por validar · {0}").format(po.supplier_name),
                         _ruta(po.costeo, 5, vista="ordenes"), po.transaction_date))
    return out


def _seccion_materia(cs):
    out = []
    for mr in frappe.get_all("Material Request", filters={"costeo": ["in", list(cs) or [""]], "docstatus": 1, "per_ordered": ["<", 100]},
                             fields=["name", "costeo", "per_ordered", "modified"]):
        out.append(_fila(cs, mr.costeo, mr.name, _("Solicitud sin OC completa ({0}% pedido)").format(round(mr.per_ordered)),
                         _ruta(mr.costeo, 5, vista="preparacion"), mr.modified))
    for po in _pos(cs, {"is_subcontracted": 0, "docstatus": 0}):
        out.append(_fila(cs, po.costeo, po.name, _("OC en borrador · {0}").format(po.supplier_name),
                         _ruta(po.costeo, 5, vista="lote", lote=po.lote_ref, paso="materia"), po.transaction_date))
    for po in _pos(cs, {"is_subcontracted": 0, "docstatus": 1, "per_received": ["<", 100]}):
        out.append(_fila(cs, po.costeo, po.name, _("Por recibir ({0}%) · {1}").format(round(po.per_received), po.supplier_name),
                         _ruta(po.costeo, 5, vista="lote", lote=po.lote_ref, paso="materia"), po.transaction_date))
    return out


def _scos(cs):
    pos = {p.name: p for p in _pos(cs, {"is_subcontracted": 1, "docstatus": 1})}
    scos = frappe.get_all("Subcontracting Order", filters={"purchase_order": ["in", list(pos) or [""]], "docstatus": 1, "per_received": ["<", 100]},
                          fields=["name", "purchase_order", "supplier_name", "lote_ref", "per_received", "modified"])
    enviados = set(frappe.get_all("Stock Entry", filters={"subcontracting_order": ["in", [s.name for s in scos] or [""]], "docstatus": 1,
                                                          "purpose": "Send to Subcontractor"}, pluck="subcontracting_order"))
    return pos, scos, enviados


def _seccion_talleres(cs):
    out = []
    pos, scos, enviados = _scos(cs)
    for s in scos:
        costeo = pos[s.purchase_order].costeo
        ruta = _ruta(costeo, 5, vista="lote", lote=s.lote_ref, paso="talleres")
        if s.name not in enviados:
            out.append(_fila(cs, costeo, s.name, _("Encargo sin enviar material · {0}").format(s.supplier_name), ruta, s.modified))
        else:
            out.append(_fila(cs, costeo, s.name, _("En el taller ({0}% recibido) · {1}").format(round(s.per_received), s.supplier_name), ruta, s.modified))
    return out


def _seccion_envios(cs):
    out = []
    pos_mat = {p.name: p for p in _pos(cs, {"is_subcontracted": 0, "docstatus": 1})}
    prs = frappe.get_all("Purchase Receipt Item", filters={"purchase_order": ["in", list(pos_mat) or [""]], "docstatus": 0},
                         fields=["parent", "purchase_order"])
    for pr in {r.parent: r for r in prs}.values():
        po = pos_mat[pr.purchase_order]
        out.append(_fila(cs, po.costeo, pr.parent, _("Recibo de material en borrador · {0}").format(po.supplier_name),
                         _ruta(po.costeo, 5, vista="lote", lote=po.lote_ref, paso="materia")))
    pos, scos, _env = _scos(cs)
    todos_scos = frappe.get_all("Subcontracting Order", filters={"purchase_order": ["in", list(pos) or [""]], "docstatus": 1},
                                fields=["name", "purchase_order", "lote_ref", "supplier_name"])
    por_sco = {s.name: s for s in todos_scos}
    for se in frappe.get_all("Stock Entry", filters={"subcontracting_order": ["in", list(por_sco) or [""]], "docstatus": 0},
                             fields=["name", "subcontracting_order", "modified"]):
        s = por_sco[se.subcontracting_order]
        out.append(_fila(cs, pos[s.purchase_order].costeo, se.name, _("Envío a taller en borrador · {0}").format(s.supplier_name),
                         _ruta(pos[s.purchase_order].costeo, 5, vista="lote", lote=s.lote_ref, paso="talleres"), se.modified))
    scr = frappe.get_all("Subcontracting Receipt Item", filters={"subcontracting_order": ["in", list(por_sco) or [""]], "docstatus": 0},
                         fields=["parent", "subcontracting_order"])
    for r in {x.parent: x for x in scr}.values():
        s = por_sco[r.subcontracting_order]
        out.append(_fila(cs, pos[s.purchase_order].costeo, r.parent, _("Recibo del taller en borrador · {0}").format(s.supplier_name),
                         _ruta(pos[s.purchase_order].costeo, 5, vista="lote", lote=s.lote_ref, paso="talleres")))
    return out


def _seccion_facturas(cs):
    out = []
    for po in _pos(cs, {"docstatus": 1, "per_received": [">=", 99.99], "per_billed": ["<", 99.99]}):
        out.append(_fila(cs, po.costeo, po.name, _("Recibido sin facturar · {0}").format(po.supplier_name),
                         _ruta(po.costeo, 5, vista="facturas"), po.transaction_date))
    pis = set(frappe.get_all("Purchase Invoice Item", filters={"purchase_order": ["in", [p.name for p in _pos(cs, {"docstatus": 1})] or [""]],
                                                              "docstatus": 0}, pluck="parent"))
    if frappe.db.has_column("Purchase Invoice", "flete_costeo"):
        pis |= set(frappe.get_all("Purchase Invoice", filters={"flete_costeo": ["in", list(cs) or [""]], "docstatus": 0}, pluck="name"))
    for pi in frappe.get_all("Purchase Invoice", filters={"name": ["in", list(pis) or [""]]},
                             fields=["name", "supplier_name", "base_net_total", "modified", "flete_costeo"] if frappe.db.has_column("Purchase Invoice", "flete_costeo")
                             else ["name", "supplier_name", "base_net_total", "modified"]):
        costeo = pi.get("flete_costeo") or frappe.db.get_value("Purchase Order", frappe.db.get_value("Purchase Invoice Item", {"parent": pi.name}, "purchase_order"), "costeo")
        out.append(_fila(cs, costeo, pi.name, _("Factura en borrador · {0} · {1}").format(pi.supplier_name, fmt_money(pi.base_net_total)),
                         _ruta(costeo, 5, vista="facturas"), pi.modified))
    return out


def _seccion_entrega(cs):
    out = []
    for dn in _docs_de_costeos("Delivery Note", cs, {"docstatus": 0}, ["lote_ref", "modified"]):
        out.append(_fila(cs, dn.costeo, dn.name, _("Remisión en borrador"),
                         _ruta(dn.costeo, 5, vista="lote", lote=dn.get("lote_ref"), paso="entrega") if dn.get("lote_ref") else _ruta(dn.costeo, 5, vista="envios"), dn.modified))
    for so in frappe.get_all("Sales Order", filters={"costeo": ["in", [c for c, v in cs.items() if v.costeo_status == "En Producción"] or [""]],
                                                     "docstatus": 1, "per_delivered": ["<", 99.99]}, fields=["name", "costeo", "per_delivered", "modified"]):
        out.append(_fila(cs, so.costeo, so.name, _("Entregado {0}% de la orden de venta").format(round(so.per_delivered)),
                         _ruta(so.costeo, 5, vista="tablero"), so.modified))
    return out


def _seccion_facturar(cs):
    out = []
    for dn in _docs_de_costeos("Delivery Note", cs, {"docstatus": 1, "per_billed": ["<", 99.99]}, ["modified"]):
        out.append(_fila(cs, dn.costeo, dn.name, _("Remisión entregada sin facturar"), _ruta(dn.costeo, 7), dn.modified))
    for si in _docs_de_costeos("Sales Invoice", cs, {"docstatus": 0}, ["modified"]):
        out.append(_fila(cs, si.costeo, si.name, _("Factura de venta en borrador"), _ruta(si.costeo, 7), si.modified))
    return out


SECCIONES = {
    "costear": _seccion_costear, "cotizar": _seccion_cotizar, "vender": _seccion_vender,
    "alta": lambda cs: _seccion_alta(cs, 3, _("Orden de venta lista: dar de alta los productos")),
    "flujo_produccion": lambda cs: _seccion_alta(cs, 4, _("Confirmar el flujo de producción")),
    "preparacion": _seccion_preparacion, "materia": _seccion_materia, "talleres": _seccion_talleres,
    "envios": _seccion_envios, "facturas": _seccion_facturas, "entrega": _seccion_entrega, "facturar": _seccion_facturar,
}


@frappe.whitelist()
def get_mi_panel(company: str = None) -> dict:
    """{"secciones": [{clave, etiqueta, total, filas}]} -- solo vistas en "editar"."""
    mis = accesos()
    costeos = _activos(company)
    secciones = []
    for clave, fn in SECCIONES.items():
        if mis.get(clave) != "editar":
            continue
        try:
            filas = fn(costeos)
        except Exception:
            frappe.log_error(title=f"Mi panel: sección {clave}")
            continue
        # Un documento sin proyecto activo ligado no tiene a dónde llevar.
        filas = [f for f in filas if f["costeo"] in costeos]
        if not filas:
            continue
        filas.sort(key=lambda f: f["fecha"], reverse=True)
        secciones.append({"clave": clave, "etiqueta": VISTAS[clave]["etiqueta"], "total": len(filas), "filas": filas[:LIMITE]})
    return {"secciones": secciones, "proyectos_activos": len(costeos)}
