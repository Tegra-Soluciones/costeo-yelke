"""Reparto por TALLA de los lotes de entrega.

La Orden de Venta ya dice cuántas prendas de cada talla lleva cada producto
(api/tallas_ov.py). Al partir la producción en lotes, en cambio, la cantidad se
capturaba solo como "prendas del producto": qué tallas iban en qué tanda vivía en la
cabeza de la persona y no llegaba nunca al taller. Este módulo baja esa decisión al
sistema.

Las reglas, tal como se acordaron:

  · se captura cuántas prendas de CADA talla lleva cada lote;
  · la suma de todos los lotes tiene que dar EXACTO lo que dice la OV para esa
    talla -- nadie puede mover piezas de una talla a otra sin darse cuenta;
  · el TOTAL de prendas del producto sí se puede mover hasta un 5% contra lo que
    pide el plan (TOLERANCIA_TOTAL_PCT) -- es el mismo margen de "producir de más"
    que ya usan el plan y la solicitud de material (_QTY_TOLERANCIA_PCT), y es lo
    que permite que un plan inflado al 105% conviva con un desglose exacto;
  · las prendas del producto en el lote dejan de capturarse aparte: se DERIVAN de
    la suma de sus tallas, para que no puedan contradecirse.

Nada de esto es obligatorio. Un producto cuyo renglón de la OV no trae desglose por
talla se sigue capturando solo por prendas, exactamente como antes, y un lote que se
dividió antes de que esto existiera no se revalida nunca (su JSON queda vacío y todo
se comporta como siempre).

De aquí el dato viaja a dos lados:
  · la Orden de Manufactura, agrupada por lote (om_general.tallas_por_lote_de_producto);
  · el Encargo a Taller, que lleva SOLO las tallas de su lote (tallas_de_encargo).
    Es el encargo y no la orden de compra porque la OC de subcontratación cubre
    TODOS los lotes de ese taller -- no tiene lote_ref; la Subcontracting Order sí.

Se guarda en Costeo Lote.desglose_tallas: JSON, una fila por lote y producto.
"""
import json

import frappe
from frappe import _
from frappe.utils import flt

from costeo_yelke.api.tallas_ov import desglose_canonico_de_ov

# Mismo margen que _QTY_TOLERANCIA_PCT en costeo_api (producir/comprar de más).
TOLERANCIA_TOTAL_PCT = 0.05
_EPS = 0.001


# ── Lectura del desglose de la OV ────────────────────────────────────────────
def _generos(doc):
    return {t.finished_item: t.genero for t in (doc.get("tabla_tallas_costeo") or []) if t.genero}


def ov_del_plan(plan):
    """La orden de venta de un Production Plan (tabla hija nativa), o None."""
    if not plan:
        return None
    return frappe.db.get_value("Production Plan Sales Order", {"parent": plan}, "sales_order")


def desglose_ov(costeo, sales_order, doc=None):
    """{producto: [{clave, etiqueta, genero, talla, cantidad}]} de esa OV.
    Vacío si no hay OV o si ningún renglón trae desglose -- y entonces todo lo que
    sigue se desactiva solo."""
    if not sales_order:
        return {}
    if doc is None and costeo and frappe.db.exists("Costeo", costeo):
        doc = frappe.get_doc("Costeo", costeo)
    return desglose_canonico_de_ov(sales_order, _generos(doc) if doc else None)


# ── Validación del reparto ───────────────────────────────────────────────────
def _entero(valor, etiqueta):
    qty = flt(valor)
    if abs(qty - round(qty)) > _EPS:
        frappe.throw(_("Las cantidades por talla deben ser piezas enteras ({0}).").format(etiqueta))
    return int(round(qty))


def validar_reparto(desglose, lotes, planned_por_producto=None):
    """Valida el reparto por talla y devuelve ``{lote_ref: {producto: [filas]}}``.

    ``desglose`` es lo que dice la OV (desglose_ov); ``lotes`` la lista que ya se
    manda a dividir, cada uno ``{lote_ref, piezas: {prod: qty}, tallas: {prod:
    {clave: qty}}}``. Los productos que la OV no trae desglosados se ignoran aquí
    por completo: siguen validándose solo por prendas, como siempre.

    Lanza con un mensaje que dice QUÉ talla y de cuánto es la diferencia -- cuadrar
    un reparto a ciegas es justo lo que hace que la gente se rinda y lo capture mal.
    """
    planned_por_producto = planned_por_producto or {}
    etiquetas = {prod: {f["clave"]: f["etiqueta"] or f["talla"] for f in filas}
                 for prod, filas in desglose.items()}
    # Productos que de verdad entran en este reparto (los que la OV desglosa y que
    # además se están repartiendo en lotes).
    en_juego = set()
    for lote in lotes:
        for prod, qty in (lote.get("piezas") or {}).items():
            if prod in desglose and flt(qty) > 0:
                en_juego.add(prod)
        for prod in (lote.get("tallas") or {}):
            if prod in desglose:
                en_juego.add(prod)

    out, errores = {}, []
    for lote in lotes:
        ref = lote.get("lote_ref") or ""
        tallas_lote = lote.get("tallas") or {}
        for prod in en_juego:
            capturado = tallas_lote.get(prod) or {}
            filas = []
            for clave, qty in capturado.items():
                if clave not in etiquetas.get(prod, {}):
                    frappe.throw(_("La talla {0} de {1} no está en la orden de venta.").format(clave, prod))
                n = _entero(qty, f"{prod} · {etiquetas[prod][clave]}")
                if n < 0:
                    frappe.throw(_("Las cantidades por talla no pueden ser negativas ({0}).").format(prod))
                if n == 0:
                    continue
                base = next(f for f in desglose[prod] if f["clave"] == clave)
                filas.append({"clave": clave, "etiqueta": base["etiqueta"], "genero": base["genero"],
                              "talla": base["talla"], "cantidad": n})
            if filas:
                out.setdefault(ref, {})[prod] = filas

    for prod in sorted(en_juego):
        sumas = {}
        for repartos in out.values():
            for f in repartos.get(prod) or []:
                sumas[f["clave"]] = sumas.get(f["clave"], 0) + f["cantidad"]
        if not sumas:
            errores.append(_("{0}: falta repartir sus tallas entre los lotes.").format(prod))
            continue
        for f in desglose[prod]:
            diferencia = sumas.get(f["clave"], 0) - flt(f["cantidad"])
            if abs(diferencia) > _EPS:
                errores.append(_("{0} · {1}: repartiste {2} y la orden de venta pide {3} ({4} {5}).").format(
                    prod, f["etiqueta"] or f["talla"], int(sumas.get(f["clave"], 0)), int(flt(f["cantidad"])),
                    _("sobran") if diferencia > 0 else _("faltan"), int(abs(diferencia))))
        # El total sí tiene margen contra el plan: el plan puede venir inflado hasta
        # un 5% ("producir de más") y aun así el desglose exacto de la OV es correcto.
        planned = flt(planned_por_producto.get(prod))
        if planned:
            total = sum(sumas.values())
            tope, piso = planned * (1 + TOLERANCIA_TOTAL_PCT), planned * (1 - TOLERANCIA_TOTAL_PCT)
            if total > tope + _EPS or total < piso - _EPS:
                errores.append(_("{0}: entre todos los lotes salen {1} prendas y el plan pide {2} "
                                 "(se permite de {3} a {4}, el 5% de siempre).").format(
                    prod, int(total), int(planned), int(round(piso)), int(round(tope))))

    if errores:
        frappe.throw(_("El reparto por talla no cuadra:<br>· {0}").format("<br>· ".join(errores)),
                     title=_("Revisa las tallas de los lotes"))
    return out


def piezas_derivadas(reparto):
    """{lote_ref: {producto: prendas}} -- las prendas de cada producto en cada lote
    salen de la suma de sus tallas, nunca de un número capturado aparte."""
    return {ref: {prod: sum(f["cantidad"] for f in filas) for prod, filas in productos.items()}
            for ref, productos in reparto.items()}


# ── Lectura de lo guardado ───────────────────────────────────────────────────
def reparto_guardado(costeo, doc=None):
    """{lote_ref: {producto: [filas]}} con lo que ya quedó guardado en el costeo.
    Vacío mientras nadie haya repartido por talla."""
    if doc is None:
        if not (costeo and frappe.db.exists("Costeo", costeo)):
            return {}
        doc = frappe.get_doc("Costeo", costeo)
    out = {}
    for row in (doc.get("tabla_lotes_costeo") or []):
        crudo = row.get("desglose_tallas")
        if not crudo:
            continue
        try:
            filas = json.loads(crudo)
        except ValueError:
            continue
        if filas:
            out.setdefault(row.lote_ref, {})[row.producto_terminado] = filas
    return out


def fechas_de_lote(costeo, doc=None):
    """{lote_ref: fecha de entrega} -- para ordenar e identificar los lotes."""
    if doc is None:
        if not (costeo and frappe.db.exists("Costeo", costeo)):
            return {}
        doc = frappe.get_doc("Costeo", costeo)
    out = {}
    for row in (doc.get("tabla_lotes_costeo") or []):
        if row.schedule_date and not out.get(row.lote_ref):
            out[row.lote_ref] = row.schedule_date
    return out


def orden_lotes(refs, fechas):
    """Lotes ordenados por fecha de entrega y, a igualdad, por su etiqueta -- el
    mismo criterio que usan las pestañas de lotes del SPA."""
    return sorted(refs, key=lambda r: (str(fechas.get(r) or "9999-12-31"), str(r)))


def lotes_de_producto(costeo, producto, doc=None):
    """[{lote_ref, schedule_date, tallas: [...], total}] de un producto, en orden.
    Lista vacía cuando ese producto no se repartió por talla -- quien la consume
    debe entonces comportarse exactamente como antes."""
    if doc is None:
        if not (costeo and frappe.db.exists("Costeo", costeo)):
            return []
        doc = frappe.get_doc("Costeo", costeo)
    reparto = reparto_guardado(costeo, doc)
    fechas = fechas_de_lote(costeo, doc)
    out = []
    for ref in orden_lotes([r for r, p in reparto.items() if p.get(producto)], fechas):
        filas = reparto[ref][producto]
        out.append({"lote_ref": ref, "schedule_date": str(fechas.get(ref)) if fechas.get(ref) else None,
                    "tallas": filas, "total": sum(flt(f.get("cantidad")) for f in filas)})
    return out


# ── Lo que necesita la pantalla de lotes ─────────────────────────────────────
@frappe.whitelist()
def get_tallas_de_lotes(plan: str) -> dict:
    """Para el paso de lotes: por producto, las tallas que pide la OV con su
    cantidad, y lo que ya está repartido (si el lote ya se dividió).

    ``{"sales_order", "productos": {producto: [{clave, etiqueta, genero, talla,
    cantidad}]}, "repartido": {lote_ref: {producto: {clave: cantidad}}}}``.
    ``productos`` vacío = esta OV no tiene desglose por talla y la pantalla se
    comporta como siempre (solo prendas)."""
    costeo = frappe.db.get_value("Production Plan", plan, "costeo") if plan else None
    sales_order = ov_del_plan(plan)
    if not costeo:
        return {"sales_order": sales_order, "productos": {}, "repartido": {}}
    doc = frappe.get_doc("Costeo", costeo)
    productos = desglose_ov(costeo, sales_order, doc)
    repartido = {ref: {prod: {f["clave"]: flt(f.get("cantidad")) for f in filas}
                       for prod, filas in por_prod.items()}
                 for ref, por_prod in reparto_guardado(costeo, doc).items()}
    return {"sales_order": sales_order, "productos": productos, "repartido": repartido}


# ── Impresión del Encargo a Taller (un solo lote) ────────────────────────────
def _producto_de_item(sco_item, cache):
    """El producto terminado de un renglón del encargo. El renglón trae la PIEZA
    ("CAMISOLA · CORTE"), no la prenda: se resuelve por el renglón de la orden de
    compra, que sí guarda producto_terminado (patch v0_2_41), y si no se puede, por
    el prefijo del código de la pieza."""
    po_item = sco_item.get("purchase_order_item")
    if po_item:
        if po_item not in cache:
            cache[po_item] = frappe.db.get_value("Purchase Order Item", po_item, "producto_terminado")
        if cache[po_item]:
            return cache[po_item]
    return (sco_item.get("item_code") or "").split(" · ")[0]


@frappe.whitelist()
def tallas_de_encargo(sco: str) -> list:
    """Las tallas del LOTE de un Encargo a Taller (Subcontracting Order), por
    producto: ``[{producto, item_name, tallas: [...], total}]``.

    Lista vacía cuando el encargo no trae lote o cuando ese lote no se repartió por
    talla -- el formato de impresión entonces no dibuja la sección, igual que antes.
    Es aquí y no en la orden de compra porque la OC de subcontratación cubre todos
    los lotes del taller; el encargo es el único documento que es de UN lote."""
    doc = frappe.get_doc("Subcontracting Order", sco)
    lote_ref = doc.get("lote_ref")
    if not lote_ref:
        return []
    costeo = frappe.db.get_value("Purchase Order", doc.purchase_order, "costeo") if doc.purchase_order else None
    reparto = (reparto_guardado(costeo) or {}).get(lote_ref) or {}
    if not reparto:
        return []
    cache, vistos, out = {}, [], []
    for it in doc.items:
        prod = _producto_de_item(it.as_dict(), cache)
        if not prod or prod in vistos or not reparto.get(prod):
            continue
        vistos.append(prod)
        filas = reparto[prod]
        out.append({"producto": prod,
                    "item_name": frappe.db.get_value("Item", prod, "item_name") or prod,
                    "tallas": filas, "total": sum(flt(f.get("cantidad")) for f in filas)})
    return out
