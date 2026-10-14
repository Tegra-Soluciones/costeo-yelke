"""Genera los SVG del diagrama de documentos del manual (sección 17).

Se dibujan a mano en vez de usar una librería porque el manual es un HTML
autocontenido: no puede cargar nada de internet, y un SVG inline pesa unos pocos
kilobytes contra los cientos de una captura.

Convención de color, la misma en los cuatro diagramas:
  · naranja  = documento propio de Yelke (Costeo, Orden Manufactura)
  · blanco   = documento nativo de ERPNext que alguien captura o valida
  · gris     = lo que el sistema genera solo (pólizas, asientos)
"""

W = 716          # ancho útil dentro de .page (760 - 2*24 de padding)
BW, BH = 188, 46  # caja
GAP_Y = 34        # alto de la flecha entre cajas

PROPIO = ("#fff4ec", "#fbd3b3", "#9a3412")   # relleno, borde, texto
NATIVO = ("#ffffff", "#d4d4d8", "#18181b")
AUTO = ("#fafafa", "#e4e4e7", "#52525b")


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def caja(x, y, titulo, doctype, estilo=NATIVO, w=BW, h=BH):
    f, b, t = estilo
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{f}" stroke="{b}" stroke-width="1"/>'
        f'<text x="{x + w/2}" y="{y + 19}" text-anchor="middle" font-size="12" font-weight="700" fill="{t}">{esc(titulo)}</text>'
        f'<text x="{x + w/2}" y="{y + 34}" text-anchor="middle" font-size="9.5" fill="#8b8b93">{esc(doctype)}</text>'
    )


def flecha_v(x, y1, y2, etiqueta="", lado="der"):
    """Flecha vertical con su etiqueta al lado."""
    s = (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 7}" stroke="#c4c4c8" stroke-width="1.4"/>'
         f'<path d="M{x - 4},{y2 - 8} L{x},{y2 - 1} L{x + 4},{y2 - 8} Z" fill="#c4c4c8"/>')
    if etiqueta:
        tx = x + 9 if lado == "der" else x - 9
        anchor = "start" if lado == "der" else "end"
        s += (f'<text x="{tx}" y="{(y1 + y2) / 2 + 3}" text-anchor="{anchor}" font-size="9.5" '
              f'fill="#8b8b93" font-family="SF Mono,Menlo,monospace">{esc(etiqueta)}</text>')
    return s


def flecha_h(x1, x2, y, etiqueta=""):
    s = (f'<line x1="{x1}" y1="{y}" x2="{x2 - 7}" y2="{y}" stroke="#c4c4c8" stroke-width="1.4"/>'
         f'<path d="M{x2 - 8},{y - 4} L{x2 - 1},{y} L{x2 - 8},{y + 4} Z" fill="#c4c4c8"/>')
    if etiqueta:
        s += (f'<text x="{(x1 + x2) / 2}" y="{y - 7}" text-anchor="middle" font-size="9.5" '
              f'fill="#8b8b93" font-family="SF Mono,Menlo,monospace">{esc(etiqueta)}</text>')
    return s


def svg(alto, cuerpo):
    # Sin atributo height: con viewBox + width:100% el navegador calcula el alto por
    # proporcion. Poner height="auto" (que no es valido en SVG) le hacia reservar un
    # alto fijo enorme y el dibujo quedaba flotando en medio de un hueco.
    return (f'<svg viewBox="0 0 {W} {alto}" style="display:block;width:100%;height:auto" '
            f'xmlns="http://www.w3.org/2000/svg" font-family="Inter,-apple-system,Segoe UI,sans-serif" '
            f'role="img">{cuerpo}</svg>')


# ── 1. Panorama: las cuatro ramas que salen del Costeo ─────────────────────
def panorama():
    c, y = [], 0
    cx = (W - 240) / 2
    c.append(caja(cx, y, "Costeo", "Costeo · propio", PROPIO, w=240))
    y += BH
    # tronco hasta el reparto
    c.append(f'<line x1="{W/2}" y1="{y}" x2="{W/2}" y2="{y + 26}" stroke="#c4c4c8" stroke-width="1.4"/>')
    y += 26
    cols = [W * 0.14, W * 0.38, W * 0.62, W * 0.86]
    c.append(f'<line x1="{cols[0]}" y1="{y}" x2="{cols[3]}" y2="{y}" stroke="#c4c4c8" stroke-width="1.4"/>')
    for x in cols:
        c.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 20}" stroke="#c4c4c8" stroke-width="1.4"/>'
                 f'<path d="M{x-4},{y+13} L{x},{y+20} L{x+4},{y+13} Z" fill="#c4c4c8"/>')
    y += 24
    ramas = [("Vender", "cotización, OV,\nremisión, factura"),
             ("Comprar material", "solicitud, OC,\nrecibo, factura"),
             ("Mandar a maquilar", "OC de maquila, encargo,\nenvío, recibo"),
             ("Ficha técnica", "Orden Manufactura")]
    for x, (tit, det) in zip(cols, ramas):
        bw = 150
        c.append(f'<rect x="{x - bw/2}" y="{y}" width="{bw}" height="58" rx="8" fill="#fafafa" stroke="#e4e4e7"/>')
        c.append(f'<text x="{x}" y="{y + 19}" text-anchor="middle" font-size="11.5" font-weight="700" fill="#18181b">{esc(tit)}</text>')
        for i, linea in enumerate(det.split("\n")):
            c.append(f'<text x="{x}" y="{y + 34 + i*12}" text-anchor="middle" font-size="9.5" fill="#8b8b93">{esc(linea)}</text>')
    return svg(y + 64, "".join(c))


# ── 2, 3 y 4: cadenas verticales ───────────────────────────────────────────
def cadena(pasos, titulo_x=None):
    """pasos = [(titulo, doctype, estilo, etiqueta_de_la_flecha_que_llega)]"""
    c, y = [], 0
    x = (W - BW) / 2
    for i, (tit, dt, est, et) in enumerate(pasos):
        if i:
            c.append(flecha_v(W / 2, y, y + GAP_Y, et))
            y += GAP_Y
        c.append(caja(x, y, tit, dt, est))
        y += BH
    return svg(y + 4, "".join(c))


VENTA = [
    ("Costeo", "Costeo · propio", PROPIO, ""),
    ("Cotización", "Quotation", NATIVO, "costeo"),
    ("Orden de Venta", "Sales Order", NATIVO, "prevdoc_docname"),
    ("Remisión", "Delivery Note", NATIVO, "against_sales_order"),
    ("Factura de Venta", "Sales Invoice", NATIVO, "delivery_note"),
    ("Póliza de overhead", "Journal Entry · automática", AUTO, "overhead_journal_entry"),
]

MATERIAL = [
    ("Orden de Venta", "Sales Order", NATIVO, ""),
    ("Plan de Producción", "Production Plan", NATIVO, "sales_order"),
    ("Solicitud de Material", "Material Request", NATIVO, "production_plan"),
    ("Orden de Compra", "Purchase Order", NATIVO, "material_request_item"),
    ("Recibo de Compra", "Purchase Receipt", NATIVO, "purchase_order"),
    ("Factura de Compra", "Purchase Invoice", NATIVO, "pr_detail"),
]

MAQUILA = [
    ("Plan de Producción", "Production Plan", NATIVO, ""),
    ("OC de subcontratación", "Purchase Order · is_subcontracted", NATIVO, "production_plan"),
    ("Encargo a Taller", "Subcontracting Order", NATIVO, "purchase_order"),
    ("Envío de material", "Stock Entry", NATIVO, "subcontracting_order"),
    ("Recibo de Taller", "Subcontracting Receipt", NATIVO, "subcontracting_order"),
    ("Recibo de compra interno", "Purchase Receipt · automático", AUTO, "subcontracting_receipt"),
]

if __name__ == "__main__":
    import io, json
    out = {
        "panorama": panorama(),
        "venta": cadena(VENTA),
        "material": cadena(MATERIAL),
        "maquila": cadena(MAQUILA),
    }
    io.open("/tmp/diagramas.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    for k, v in out.items():
        print("%-10s %6d bytes" % (k, len(v)))
