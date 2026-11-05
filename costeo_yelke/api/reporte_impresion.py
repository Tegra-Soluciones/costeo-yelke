"""Reporte final en PDF: el mismo análisis de la pantalla (costeo_api.get_reporte_final)
con el formato de impresión de Yelke (membrete, cinta, Poppins), para circular
internamente.

La plantilla es el Print Format "Reporte Final Yelke" del Costeo; aquí se dejan los
números ya calculados (indicadores, puente, gráficas) para que el Jinja solo pinte.
Un costeo puede tener varias OV: la del reporte llega por frappe.flags desde
`descargar_reporte_final`; impreso desde el escritorio sin OV, toma el costeo completo.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate

FORMATO = "Reporte Final Yelke"


def _pct(v, total):
    return (flt(v) / flt(total) * 100) if flt(total) else 0.0


def reporte_final_impresion(doc):
    """Método jinja: el reporte de `doc` (Costeo) listo para imprimir."""
    from costeo_yelke.api.costeo_api import get_reporte_final

    r = get_reporte_final(doc.name, frappe.flags.get("reporte_sales_order"))
    e, real, op = r["estimado"], r["real"], r.get("operacion") or {}
    materia = flt(real.get("material_consumido", real.get("material_directo")))
    fletes = sum(flt(real.get(k)) for k in ("flete_materiales", "flete_taller_ida", "flete_taller_regreso", "flete_cliente"))
    prendas = flt(real.get("qty_total")) or flt(e.get("qty_total"))
    facturado = bool(real.get("sales_invoice"))

    costos = [
        {"label": "Materia prima", "plan": flt(e["materiales_total"]), "real": materia,
         "nota": (_("comprado {0} menos sobrante {1}").format(frappe.format_value(real["material_directo"], "Currency"),
                                                             frappe.format_value(real["material_sobrante"], "Currency"))
                  if flt(real.get("material_sobrante")) else "")},
        {"label": "Maquila", "plan": flt(e["servicios_total"]), "real": flt(real["servicio_directo"]), "nota": ""},
        {"label": "Fletes", "plan": flt(e["shipping_total"]), "real": fletes, "nota": ""},
        {"label": "Gastos", "plan": flt(e["overhead_total"]), "real": flt(real["overhead"]),
         "nota": _("{0}% del costo directo").format(round(flt(e.get("overhead_pct_promedio")), 1))},
    ]
    for c in costos:
        c["dif"] = c["real"] - c["plan"]
        c["por_prenda"] = c["real"] / prendas if prendas else 0
        c["pct"] = _pct(c["real"], real["costo_total"])
    max_concepto = max([1.0] + [max(c["plan"], c["real"]) for c in costos])
    for c in costos:
        c["ancho_plan"], c["ancho_real"] = c["plan"] / max_concepto * 100, c["real"] / max_concepto * 100

    puente = [
        {"label": "Venta", "v": flt(real["ingreso"]) - flt(e["venta_total"]) if facturado else 0.0},
        {"label": "Materia prima", "v": flt(e["materiales_total"]) - materia},
        {"label": "Maquila", "v": flt(e["servicios_total"]) - flt(real["servicio_directo"])},
        {"label": "Fletes", "v": flt(e["shipping_total"]) - fletes},
        {"label": "Gastos", "v": flt(e["overhead_total"]) - flt(real["overhead"])},
    ]
    max_puente = max([1.0] + [abs(p["v"]) for p in puente])
    for p in puente:
        p["ancho"] = abs(p["v"]) / max_puente * 100

    tonos = ["#e65a0b", "#ff8a47", "#ffc29e", "#d4d4d8"]
    composicion = [{"label": c["label"], "v": c["real"], "color": tonos[i], "pct": c["pct"]}
                   for i, c in enumerate(costos) if c["real"] > 0]
    venta = flt(real["ingreso"]) if facturado else flt(e["venta_total"])
    peso = [{"label": c["label"], "v": c["real"], "color": tonos[i], "pct": _pct(c["real"], venta)}
            for i, c in enumerate(costos) if c["real"] > 0]
    utilidad = venta - sum(c["real"] for c in costos)
    if utilidad > 0:
        peso.append({"label": "Utilidad", "v": utilidad, "color": "#0f8a5f", "pct": _pct(utilidad, venta)})

    mats = (r.get("resumen") or {}).get("materiales") or []
    comprado = sum(flt(m["comprado_importe"]) for m in mats)
    usado = sum(flt(m["consumido_qty"]) * flt(m["precio_real"]) for m in mats)

    costo_u_plan = flt(e["costo_total"]) / flt(e["qty_total"]) if flt(e["qty_total"]) else 0
    max_costo = max(flt(e["costo_total"]), flt(real["costo_total"]), 1.0)
    so_name = frappe.flags.get("reporte_sales_order") or frappe.db.get_value(
        "Sales Order", {"costeo": doc.name, "docstatus": 1}, "name", order_by="creation desc")
    return frappe._dict({
        **r, "costos": costos, "puente": puente, "composicion": composicion, "peso_venta": peso,
        "prendas": prendas, "fletes_total": fletes, "materia_real": materia, "facturado": facturado,
        "costo_unit": flt(real["costo_total"]) / prendas if prendas else 0, "costo_unit_plan": costo_u_plan,
        "util_unit": flt(real["rentabilidad_monto"]) / prendas if prendas and facturado else 0,
        "util_unit_plan": flt(e["rentabilidad_monto"]) / flt(e["qty_total"]) if flt(e["qty_total"]) else 0,
        "aprovechamiento": _pct(usado, comprado) if comprado else None,
        "ancho_costo_plan": flt(e["costo_total"]) / max_costo * 100,
        "ancho_costo_real": flt(real["costo_total"]) / max_costo * 100,
        "sales_order": so_name, "op": op,
    })


@frappe.whitelist()
def descargar_reporte_final(costeo: str, sales_order: str = None):
    """El reporte final como PDF, con el formato "Reporte Final Yelke"."""
    if not frappe.has_permission("Costeo", "read", costeo):
        frappe.throw(_("No tienes permiso para ver este costeo."), frappe.PermissionError)
    frappe.flags.reporte_sales_order = sales_order or None
    try:
        pdf = frappe.get_print("Costeo", costeo, FORMATO, as_pdf=True)
    finally:
        frappe.flags.reporte_sales_order = None
    fecha = getdate().strftime("%Y-%m-%d")
    frappe.local.response.filename = f"Reporte final {costeo}{(' ' + sales_order) if sales_order else ''} {fecha}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
