"""Orden de manufactura GENERAL por producto (DocType "Orden Manufactura").

Una por producto BASE del costeo (su variante de talla entra como tallas). De ella se
arma la OM de cada orden de maquila (Purchase Order subcontratada):
  - la info general y las tallas van a TODOS los talleres;
  - procesos, observaciones, tablas de medidas y archivos solo a los talleres a los
    que se asignaron ("Para"; vacío = todos).
Un taller que trabaja varios productos recibe un registro por producto.

La OM de la orden de maquila NO se copia: se arma al momento (om_de_oc) desde la
general, así nunca se desincroniza. Costeos sin OM general siguen mostrando la OM
que se capturó directo en la orden de compra (campos om_* de Purchase Order).
"""
import json

import frappe
from frappe import _
from frappe.utils import flt

from costeo_yelke.api.costeo_api import _om_decode_tables, _om_encode_tables, get_om

GENERAL = ["om_modelo", "om_tela", "om_color", "om_color_principal", "om_forro", "om_combinacion",
           "om_ubicacion", "om_aberturas", "om_fecha_requerida", "om_bordado", "om_estampado",
           "om_sublimado", "om_reflejante"]


def _lista(v):
    if isinstance(v, (list, tuple)):
        return [x for x in v if x]
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def _base_de(doc, producto):
    for p in doc.costeo_producto:
        if p.finished_item == producto:
            return p.get("variante_talla_de") or producto
    return producto


def _productos_base(doc):
    """[(base, [base + sus variantes])] en el orden del costeo."""
    out = {}
    for p in doc.costeo_producto:
        if not p.finished_item:
            continue
        base = p.get("variante_talla_de") or p.finished_item
        out.setdefault(base, [base])
        if p.finished_item not in out[base]:
            out[base].append(p.finished_item)
    return list(out.items())


def _etiqueta_talla(texto):
    # "XXL - CAB-LETRA,3XL - CAB-LETRA" -> "XXL, 3XL"
    return ", ".join(t.split(" - ")[0].strip() for t in (texto or "").split(",") if t.strip())


def tallas_de_producto(doc, base):
    """Tallas heredadas del costeo para el producto base y sus variantes: lo que el
    costeo trae desglosado por talla, y el resto de cada producto como un renglón
    (la variante con su etiqueta de talla; la base, "Sin desglose")."""
    filas = []
    productos = dict(_productos_base(doc)).get(base, [base])
    for prod in productos:
        p = next((x for x in doc.costeo_producto if x.finished_item == prod), None)
        if not p:
            continue
        asignado = 0.0
        for t in (doc.get("tabla_tallas_costeo") or []):
            if t.finished_item != prod or flt(t.qty) <= 0:
                continue
            filas.append({"producto": prod, "genero": t.genero or "", "talla": _etiqueta_talla(t.talla), "cantidad": flt(t.qty)})
            asignado += flt(t.qty)
        resto = flt(p.qty) - asignado
        if resto > 0:
            etiqueta = p.get("talla_grupo_label") or ""
            genero = etiqueta.split(" ")[0] if etiqueta else ""
            talla = etiqueta[len(genero):].strip() if etiqueta else ("Sin desglose" if prod == base else prod)
            filas.append({"producto": prod, "genero": genero, "talla": talla or "Sin desglose", "cantidad": resto})
    return filas


def talleres_de_producto(doc, base):
    productos = dict(_productos_base(doc)).get(base, [base])
    vistos = []
    for e in sorted(doc.get("tabla_etapas_costeo") or [], key=lambda e: (str(e.etapa or ""), e.idx)):
        if e.producto_terminado in productos and e.proveedor and e.proveedor not in vistos:
            vistos.append(e.proveedor)
    return vistos


def _om_doc(costeo, producto):
    name = frappe.db.get_value("Orden Manufactura", {"costeo": costeo, "producto": producto}, "name")
    return frappe.get_doc("Orden Manufactura", name) if name else None


def _serializar(om):
    if not om:
        return None
    general = {f: (str(om.get(f)) if f == "om_fecha_requerida" and om.get(f) else om.get(f)) for f in GENERAL}
    return {
        "name": om.name,
        "general": general,
        "procesos": [{"nombre_proceso": r.nombre_proceso, "ubicacion": r.ubicacion, "colores": r.colores,
                      "proveedores": _lista(r.proveedores)} for r in om.om_procesos],
        "observaciones": [{"texto": r.texto, "proveedores": _lista(r.proveedores)} for r in om.om_observaciones],
        "tablas": _om_decode_tables(om),
        "archivos": [{"archivo": r.archivo, "descripcion": r.descripcion, "proveedores": _lista(r.proveedores)}
                     for r in om.om_archivos],
    }


@frappe.whitelist()
def get_oms_generales(costeo: str) -> dict:
    """Las órdenes de manufactura generales del costeo, una por producto base, con sus
    talleres (para asignar) y sus tallas heredadas."""
    doc = frappe.get_doc("Costeo", costeo)
    out = []
    for base, productos in _productos_base(doc):
        out.append({
            "producto": base,
            "item_name": frappe.db.get_value("Item", base, "item_name") or base,
            "variantes": [p for p in productos if p != base],
            "talleres": talleres_de_producto(doc, base),
            "tallas": tallas_de_producto(doc, base),
            "om": _serializar(_om_doc(costeo, base)),
        })
    return {"productos": out}


@frappe.whitelist()
def guardar_om_general(costeo: str, producto: str, datos) -> dict:
    datos = json.loads(datos) if isinstance(datos, str) else (datos or {})
    doc = frappe.get_doc("Costeo", costeo)
    base = _base_de(doc, producto)
    om = _om_doc(costeo, base) or frappe.new_doc("Orden Manufactura")
    om.costeo, om.producto = costeo, base
    for f, v in (datos.get("general") or {}).items():
        if f in GENERAL:
            om.set(f, v or (0 if f in ("om_aberturas", "om_bordado", "om_estampado", "om_sublimado", "om_reflejante") else None))
    om.set("om_tallas", tallas_de_producto(doc, base))
    om.set("om_procesos", [
        {"proceso": f"Proceso {i}", "nombre_proceso": r.get("nombre_proceso"), "ubicacion": r.get("ubicacion"),
         "colores": r.get("colores"), "proveedores": ", ".join(_lista(r.get("proveedores")))}
        for i, r in enumerate(datos.get("procesos") or [], 1)
        if (r.get("nombre_proceso") or r.get("ubicacion") or r.get("colores"))])
    om.set("om_observaciones", [
        {"texto": r.get("texto"), "proveedores": ", ".join(_lista(r.get("proveedores")))}
        for r in (datos.get("observaciones") or []) if (r.get("texto") or "").strip()])
    _om_encode_tables(om, datos.get("tablas") or [])
    om.set("om_archivos", [
        {"archivo": r.get("archivo"), "descripcion": r.get("descripcion"),
         "proveedores": ", ".join(_lista(r.get("proveedores")))}
        for r in (datos.get("archivos") or []) if r.get("archivo")])
    om.flags.ignore_permissions = True
    om.save()
    return {"ok": True, "name": om.name, "om": _serializar(om)}


def _para(fila_proveedores, supplier):
    lista = fila_proveedores if isinstance(fila_proveedores, list) else _lista(fila_proveedores)
    return not lista or supplier in lista


@frappe.whitelist()
def om_de_oc(po: str) -> list:
    """La OM de UNA orden de maquila: un registro por producto que trabaja ese taller,
    con la info general y tallas completas y solo lo asignado a su proveedor. Sin OM
    general, la que se capturó directo en la orden de compra (como antes)."""
    po_doc = frappe.get_doc("Purchase Order", po)
    costeo = po_doc.get("costeo")
    registros = []
    if costeo and frappe.db.exists("Costeo", costeo):
        doc = frappe.get_doc("Costeo", costeo)
        bases = []
        for it in po_doc.items:
            prod = it.get("producto_terminado") or (it.get("fg_item") or "").split(" · ")[0]
            base = _base_de(doc, prod) if prod else None
            if base and base not in bases:
                bases.append(base)
        for base in bases:
            om = _serializar(_om_doc(costeo, base))
            if not om:
                continue
            sup = po_doc.supplier
            registros.append({
                "producto": base,
                "item_name": frappe.db.get_value("Item", base, "item_name") or base,
                "general": om["general"],
                "tallas": tallas_de_producto(doc, base),
                "procesos": [r for r in om["procesos"] if _para(r["proveedores"], sup)],
                "observaciones": [r for r in om["observaciones"] if _para(r["proveedores"], sup)],
                "tablas": [t for t in om["tablas"] if _para(t.get("proveedores"), sup)],
                "archivos": [r for r in om["archivos"] if _para(r["proveedores"], sup)],
                "origen": "general",
            })
    if not registros:
        legacy = get_om(po)
        g = legacy.get("general") or {}
        if any(g.get(f) for f in GENERAL) or legacy.get("procesos") or legacy.get("tablas") or legacy.get("archivos") or g.get("om_observaciones"):
            registros.append({
                "producto": "", "item_name": "", "general": g, "tallas": [],
                "procesos": legacy.get("procesos") or [],
                "observaciones": [{"texto": g.get("om_observaciones")}] if g.get("om_observaciones") else [],
                "tablas": legacy.get("tablas") or [], "archivos": legacy.get("archivos") or [],
                "tallas_caballero": legacy.get("tallas_caballero"), "tallas_dama": legacy.get("tallas_dama"),
                "origen": "orden_compra",
            })
    return registros
