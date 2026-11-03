"""«Enviar a» en la orden de compra de materia prima.

El proveedor puede mandar el material directo al taller que lo va a usar (un envío
menos). Es solo una indicación impresa en la OC: en el sistema la compra entra al
almacén de Yelke y de ahí se manda al taller como siempre (recibo + envío al taller).

La sugerencia sale del flujo del costeo: el taller de cada encargo de maquila
(OC subcontratada) y la materia prima que pide el BOM de lo que hace. Si todavía no
hay órdenes de maquila, de las etapas del costeo.
"""
import frappe
from frappe import _

from costeo_yelke.api.entregas_taller import direcciones_destino


def _talleres_por_material(costeo):
    """``{item_code: [proveedor, ...]}`` -- qué taller(es) consumen cada material, en
    el orden de sus órdenes de maquila."""
    out = {}

    def _poner(code, supplier):
        if code and supplier and supplier not in out.setdefault(code, []):
            out[code].append(supplier)

    pos = frappe.get_all("Purchase Order",
                         filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": ["<", 2]},
                         fields=["name", "supplier"], order_by="creation asc")
    boms = {}
    for po in pos:
        for it in frappe.get_all("Purchase Order Item", filters={"parent": po.name}, fields=["fg_item", "bom"]):
            bom = it.bom or (frappe.db.get_value("BOM", {"item": it.fg_item, "is_active": 1, "is_default": 1})
                             if it.fg_item else None)
            if not bom:
                continue
            if bom not in boms:
                boms[bom] = frappe.get_all("BOM Item", filters={"parent": bom}, pluck="item_code")
            for code in boms[bom]:
                _poner(code, po.supplier)
    if pos:
        return out

    # Sin órdenes de maquila todavía: de las etapas del costeo.
    from costeo_yelke.api.costeo_api import _match_material_stage

    doc = frappe.get_doc("Costeo", costeo)
    por_material = {}
    for r in doc.get("tabla_materiales_etapa") or []:
        if r.material_id and r.stage_id:
            por_material.setdefault(r.material_id, []).append(r.stage_id)
    for mat in doc.get("costeo_producto_detalle") or []:
        if mat.concept_type != "Materia Prima" or not mat.item:
            continue
        etapas = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == mat.finished_item]
        elegidas = [e for e in etapas if e.stage_id in por_material.get(mat.material_id, [])]
        if not elegidas:
            e = _match_material_stage(mat.etapa, etapas)
            # Sin etapa asignada: la(s) que arrancan de materia prima directa.
            elegidas = [e] if e else [x for x in etapas if not (x.recibe_de or "").strip()]
        for e in elegidas:
            _poner(mat.item, e.proveedor)
    return out


def sugerencia_envio(doc):
    """Talleres a los que puede ir el material de esta OC, con sus direcciones.
    ``sugerido`` = el único taller que recibe todo el material de la OC (si hay uno)."""
    costeo = doc.get("costeo")
    if doc.get("is_subcontracted") or not costeo:
        return None
    por_material = _talleres_por_material(costeo)
    talleres = {}
    for it in doc.get("items") or []:
        for s in por_material.get(it.item_code, []):
            talleres.setdefault(s, []).append(it.item_name or it.item_code)
    actual = doc.get("enviar_a_taller")
    if actual and actual not in talleres:
        talleres[actual] = []
    codigos = {it.item_code for it in doc.get("items") or []}
    cubren_todo = [s for s, mats in talleres.items()
                   if all(s in por_material.get(c, []) for c in codigos)]
    return {
        "sugerido": cubren_todo[0] if len(cubren_todo) == 1 else None,
        "talleres": [{
            "supplier": s,
            "supplier_name": frappe.db.get_value("Supplier", s, "supplier_name") or s,
            "materiales": list(dict.fromkeys(mats)),
            "direcciones": direcciones_destino(doc.name, s),
        } for s, mats in talleres.items()],
    }


def prellenar_envio(doc, method=None):
    """before_insert de Purchase Order: la OC de materia prima nace con el taller
    sugerido (si todo su material va a uno solo) y su dirección de envío. Se puede
    cambiar o dejar vacío (se manda a Yelke)."""
    if doc.get("enviar_a_taller") or not doc.meta.has_field("enviar_a_taller"):
        return
    try:
        sug = sugerencia_envio(doc)
    except Exception:
        # Es solo una sugerencia: nunca impide crear la orden.
        return
    if not sug or not sug["sugerido"]:
        return
    doc.enviar_a_taller = sug["sugerido"]
    taller = next(t for t in sug["talleres"] if t["supplier"] == sug["sugerido"])
    doc.enviar_a_direccion = taller["direcciones"][0]["name"] if taller["direcciones"] else None


def aplicar_envio(doc, taller, direccion):
    """Fija «Enviar a» en la OC (sin guardar). ``taller`` vacío = se manda a Yelke."""
    taller = (taller or "").strip() or None
    direccion = (direccion or "").strip() or None
    if taller and not frappe.db.exists("Supplier", taller):
        frappe.throw(_("El taller {0} no existe.").format(taller))
    if not taller:
        direccion = None
    elif direccion and direccion not in [d["name"] for d in direcciones_destino(doc.name, taller)]:
        frappe.throw(_("La dirección {0} no es del taller {1}.").format(direccion, taller))
    doc.enviar_a_taller = taller
    doc.enviar_a_direccion = direccion


def envio_impresion(doc):
    """Taller y dirección de «Enviar a» para el formato impreso, o None."""
    taller = doc.get("enviar_a_taller")
    if not taller:
        return None
    from costeo_yelke.api.impresion import direccion_lineas

    return {"nombre": frappe.db.get_value("Supplier", taller, "supplier_name") or taller,
            "direccion": direccion_lineas(doc.get("enviar_a_direccion"))}
