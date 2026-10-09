"""Desglose por talla en la Orden de Venta.

Dos casos, con el mismo formato de texto ("- <talla> × <n> pza(s)"):
  · Producto principal: cuántas piezas de cada talla normal. La suma debe ser
    EXACTAMENTE la cantidad del renglón (la del costeo) -- se captura aquí.
  · Tallas extra (variantes): ya existía en "Cantidades confirmadas por talla"
    (costeo_api.lineas_venta_variantes); es más libre.

El desglose se guarda en Sales Order Item.desglose_tallas (JSON, patch v0_2_53)
y además se escribe como lista DEBAJO de la descripción del artículo, así viaja
a la remisión, la factura y los PDF. La Orden de Manufactura lo lee de aquí
(desglose_de_ov) para su desglose de tallas general.
"""
import json
import re

import frappe
from frappe import _
from frappe.utils import cint, flt

TITULO_BLOQUE = "Desglose por talla:"
_LINEA_TALLA = re.compile(r"^\s*[-•]\s*(.+?)\s*×\s*([\d.,]+)\s*pza", re.IGNORECASE)


def texto_plano(desc):
    """Descripción de ERPNext (puede venir en HTML del editor) a texto con saltos."""
    desc = desc or ""
    if "<" in desc:
        desc = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", desc)
        desc = re.sub(r"(?i)<li[^>]*>", "- ", desc)
        desc = re.sub(r"<[^>]+>", "", desc)
        desc = (desc.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\n{3,}", "\n\n", desc).strip()


def quitar_bloque(desc):
    """Quita un bloque "Desglose por talla:" previo (para reescribirlo al guardar)."""
    texto = texto_plano(desc)
    i = texto.find(TITULO_BLOQUE)
    return texto[:i].rstrip() if i >= 0 else texto


def bloque(filas):
    lineas = [f"- {f['etiqueta']} × {cint(f['qty'])} pza(s)" for f in filas if flt(f.get("qty")) > 0]
    return (TITULO_BLOQUE + "\n" + "\n".join(lineas)) if lineas else ""


def _etiqueta(talla_code):
    t = frappe.db.get_value("Talla", talla_code, ["talla", "genero"], as_dict=True) or {}
    return " ".join(x for x in (t.get("genero"), t.get("talla") or talla_code) if x), t.get("genero") or ""


def _es_linea_extra(desc):
    # Las líneas de sobrecosto de talla repiten el artículo base (ver
    # costeo_api._build_talla_extra_description): no son "el producto principal".
    return "Tallas extra (+" in (desc or "")


def _productos_principales(costeo):
    if not costeo or not frappe.db.exists("Costeo", costeo):
        return set()
    return {p.finished_item for p in frappe.get_doc("Costeo", costeo).costeo_producto
            if p.finished_item and not p.get("variante_talla_de")}


@frappe.whitelist()
def get_desglose_tallas_ov(sales_order: str) -> list:
    """Renglones de producto principal de la OV con su desglose guardado."""
    so = frappe.get_doc("Sales Order", sales_order)
    principales = _productos_principales(so.get("costeo"))
    out = []
    for it in so.items:
        if it.item_code not in principales or _es_linea_extra(it.description):
            continue
        out.append({
            "row": it.name, "item_code": it.item_code, "item_name": it.item_name, "qty": flt(it.qty),
            "filas": json.loads(it.get("desglose_tallas") or "[]"),
        })
    return out


@frappe.whitelist()
def guardar_desglose_tallas_ov(sales_order: str, row: str, filas) -> dict:
    """Guarda el desglose por talla de un renglón de producto principal.
    `filas` = [{"talla": <código Talla>, "qty": n}]; la suma debe ser la cantidad del renglón."""
    filas = frappe.parse_json(filas) if isinstance(filas, str) else (filas or [])
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus != 0:
        frappe.throw(_("Solo se puede cambiar el desglose de una orden de venta en borrador."))
    it = next((x for x in so.items if x.name == row), None)
    if not it:
        frappe.throw(_("No se encontró ese renglón en la orden de venta."))

    limpias = []
    for f in filas:
        qty = flt(f.get("qty"))
        if not f.get("talla") or qty <= 0:
            continue
        if qty != int(qty):
            frappe.throw(_("Las cantidades por talla deben ser piezas enteras."))
        etiqueta, genero = _etiqueta(f["talla"])
        limpias.append({"talla": f["talla"], "etiqueta": etiqueta, "genero": genero, "qty": int(qty)})

    suma = sum(f["qty"] for f in limpias)
    if limpias and suma != flt(it.qty):
        frappe.throw(_("El desglose suma {0} piezas y el producto lleva {1}: debe coincidir exacto.").format(
            cint(suma), cint(it.qty)))

    base = quitar_bloque(it.description)
    blq = bloque(limpias)
    it.description = (base + "\n\n" + blq).strip() if blq else base
    it.desglose_tallas = json.dumps(limpias, ensure_ascii=False) if limpias else None
    so.flags.ignore_permissions = True
    so.flags.ignore_mandatory = True
    so.save()
    return {"ok": True, "description": it.description, "filas": limpias}


def desglose_de_ov(sales_order, generos=None):
    """{item_code: [{"genero", "talla", "cantidad"}]} con lo capturado en la OV.
    Usa el JSON guardado; para líneas viejas sin JSON (tallas extra de antes) lee
    las líneas "- <talla> × <n> pza(s)" de la descripción. `generos`
    ({item_code: genero}) completa el género cuando la línea no lo trae."""
    if not sales_order:
        return {}
    generos = generos or {}
    out = {}
    for r in frappe.get_all("Sales Order Item", filters={"parent": sales_order},
                            fields=["item_code", "description", "desglose_tallas"], order_by="idx"):
        filas = []
        if r.get("desglose_tallas"):
            for f in json.loads(r.desglose_tallas):
                genero = f.get("genero") or ""
                talla = f.get("etiqueta") or ""
                if genero and talla.startswith(genero + " "):
                    talla = talla[len(genero) + 1:]
                filas.append({"genero": genero, "talla": talla, "cantidad": flt(f.get("qty"))})
        else:
            for linea in texto_plano(r.description).splitlines():
                m = _LINEA_TALLA.match(linea)
                if m:
                    filas.append({"genero": generos.get(r.item_code, ""), "talla": m.group(1).strip(),
                                  "cantidad": flt(m.group(2).replace(",", ""))})
        if filas:
            out.setdefault(r.item_code, []).extend(filas)
    return out
