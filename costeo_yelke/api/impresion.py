"""Datos para los formatos de impresión de Yelke (métodos jinja, ver hooks.py).

`firmas_documento(doc)` arma el bloque de firmas de cualquier documento con las
personas que de verdad intervinieron, con su firma de User.firma (patch v0_2_52):

  · Orden de compra (material o maquila): Elaboró · Revisó · Aprobó
    (revisó = revisado_por_yelke de la doble validación).
  · Todos los demás: Elaboró · Validó.

"Validó/Aprobó" es quien lo validó (submit): se toma del Version que registra el
cambio docstatus 0 -> 1, así sirve también para documentos ya validados.
"""
import base64
from functools import lru_cache

import frappe
from frappe.utils import formatdate


def _persona(usuario):
    if not usuario or usuario == "Guest":
        return {"nombre": "", "firma": None}
    campos = ["full_name", "firma"] if frappe.db.has_column("User", "firma") else ["full_name"]
    u = frappe.db.get_value("User", usuario, campos, as_dict=True) or {}
    nombre = u.get("full_name") or usuario
    if usuario == "Administrator":
        nombre = "Administrador"
    return {"nombre": nombre, "firma": firma_limpia(u.get("firma"))}


def firma_limpia(uri):
    """La firma tal como se imprime: sin la línea guía y recortada al trazo.

    El recuadro de firma de ERPNext (jSignature, decorColor) pinta su línea guía
    DENTRO de la imagen que guarda, y guarda el lienzo completo (casi todo en
    blanco), así que impresa salía chica y con una raya debajo. La línea guía de
    jSignature va siempre en el mismo lugar: y = alto - round(alto/5), de
    x = 1.5·d a ancho - 1.5·d (d = round(alto/5)). Se borra esa franja y se
    recorta a lo que quede dibujado; el formato la escala al alto de la firma."""
    if not uri or not uri.startswith("data:image"):
        return uri or None
    return _firma_limpia(uri)


@lru_cache(maxsize=64)
def _firma_limpia(uri):
    import io

    from PIL import Image

    try:
        im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")
    except Exception:
        return uri
    ancho, alto = im.size
    d = round(alto / 5)
    y = alto - d
    pix = im.load()
    for yy in range(max(0, y - 2), min(alto, y + 3)):
        for xx in range(max(0, int(d * 1.5) - 2), min(ancho, int(ancho - d * 1.5) + 3)):
            pix[xx, yy] = (0, 0, 0, 0)
    caja = im.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
    if not caja:
        return None
    margen = 3
    im = im.crop((max(0, caja[0] - margen), max(0, caja[1] - margen),
                  min(ancho, caja[2] + margen), min(alto, caja[3] + margen)))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _quien_valido(doc):
    if doc.docstatus != 1:
        return None, None
    v = frappe.get_all(
        "Version",
        filters={"ref_doctype": doc.doctype, "docname": doc.name, "data": ["like", '%"docstatus",0,1%']},
        fields=["owner", "creation"], order_by="creation asc", limit=1,
    )
    if v:
        return v[0].owner, v[0].creation
    return doc.modified_by, doc.modified


def _firma(titulo, usuario, fecha):
    p = _persona(usuario) if usuario else {"nombre": "", "firma": None}
    return {"titulo": titulo, "nombre": p["nombre"], "firma": p["firma"],
            "fecha": formatdate(fecha) if (usuario and fecha) else "",
            "fecha_hora": fecha_hora(fecha) if (usuario and fecha) else ""}


def firmas_documento(doc):
    valido, valido_en = _quien_valido(doc)
    if doc.doctype == "Purchase Order":
        return [
            _firma("Elaboró", doc.owner, doc.creation),
            _firma("Revisó", doc.get("revisado_por_yelke"), doc.get("revisado_en_yelke")),
            _firma("Aprobó", valido, valido_en),
        ]
    return [
        _firma("Elaboró", doc.owner, doc.creation),
        _firma("Validó", valido, valido_en),
    ]


# ── Apoyo del diseño de impresión (templates/print/oc_yelke.html y membrete.html) ──
# wkhtmltopdf no puede depender de internet: fuentes y logo van incrustados en
# base64. Se leen una vez por proceso (lru_cache).
import base64
import os
import re
from functools import lru_cache

from frappe.utils import flt

_PUBLIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
_PESOS_POPPINS = {300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}

TITULOS = {
    "Quotation": "Cotización", "Sales Order": "Orden de venta", "Delivery Note": "Nota de entrega",
    "Sales Invoice": "Factura", "Purchase Order": "Orden de compra", "Purchase Receipt": "Recibo de compra",
    "Purchase Invoice": "Factura de compra", "Material Request": "Solicitud de material",
    "Supplier Quotation": "Presupuesto de proveedor", "Request for Quotation": "Solicitud de cotización",
    "Subcontracting Order": "Encargo a taller", "Subcontracting Receipt": "Recibo de taller",
    "Stock Entry": "Movimiento de almacén", "Costeo": "Costeo",
}

# "H87 - Pieza" -> "pzas"; lo demás, el nombre de la unidad sin la clave SAT.
_UDM_CORTA = {"pieza": "pzas", "metro": "m", "kilogramo": "kg", "litro": "l", "par": "pares",
              "juego": "juegos", "rollo": "rollos", "caja": "cajas", "mazo": "mazos", "prendas": "prendas"}


def fuentes_css():
    # Función normal: Frappe solo registra FunctionType como método jinja,
    # y un lru_cache no lo es.
    return _fuentes_css()


@lru_cache(maxsize=1)
def _fuentes_css():
    css = []
    for peso, nombre in _PESOS_POPPINS.items():
        ruta = os.path.join(_PUBLIC, "fonts", "poppins", f"Poppins-{nombre}.ttf")
        with open(ruta, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        css.append("@font-face{font-family:'Poppins';font-style:normal;font-weight:%d;"
                   "src:url(data:font/truetype;base64,%s);}" % (peso, b64))
    return "\n".join(css)


def logo_yelke():
    return _logo_yelke()


@lru_cache(maxsize=1)
def _logo_yelke():
    with open(os.path.join(_PUBLIC, "images", "logo-yelke-print.png"), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def titulo_documento(doc):
    if doc.get("doctype") == "Purchase Order" and doc.get("is_subcontracted"):
        return "Orden de maquila"
    return TITULOS.get(doc.get("doctype"), doc.get("doctype"))


def estado_documento(doc):
    return {0: ("Borrador", "borrador"), 1: ("Validada", "validada"), 2: ("Cancelada", "cancelada")}.get(
        int(doc.get("docstatus") or 0), ("", ""))


def cantidad_uom(qty, uom=None):
    q = flt(qty)
    num = f"{q:,.0f}" if q == int(q) else f"{q:,.2f}".rstrip("0").rstrip(".")
    if not uom:
        return num
    nombre = uom.split(" - ", 1)[-1].strip()
    return f"{num} {_UDM_CORTA.get(nombre.lower(), nombre.lower())}"


def importe_letra(monto, moneda="MXN"):
    """56909.60 -> "Cincuenta y seis mil novecientos nueve pesos 60/100 M.N." """
    from num2words import num2words

    monto = round(flt(monto), 2)
    enteros, centavos = int(monto), int(round((monto - int(monto)) * 100))
    texto = num2words(enteros, lang="es")
    # num2words dice "cincuenta y uno mil"; en español es "cincuenta y un mil".
    texto = re.sub(r"\bveintiuno (mil|millones)", r"veintiún \1", texto)
    texto = re.sub(r"\buno (mil|millones)", r"un \1", texto)
    # ...y antes de "pesos" también se apocopa: "mil un pesos", "veintiún pesos".
    texto = re.sub(r"veintiuno$", "veintiún", texto)
    texto = re.sub(r"\buno$", "un", texto)
    texto = texto[:1].upper() + texto[1:]
    if texto.endswith(("millón", "millones")):
        texto += " de"  # "un millón de pesos"
    if (moneda or "MXN") == "MXN":
        return f"{texto} {'peso' if enteros == 1 else 'pesos'} {centavos:02d}/100 M.N."
    nombre = {"USD": "dólares", "EUR": "euros"}.get(moneda, moneda)
    return f"{texto} {nombre} {centavos:02d}/100 {moneda}"


def contacto_documento(doc):
    """Contacto del cliente/proveedor del documento: nombre, puesto, teléfono, correo."""
    nombre = doc.get("contact_person")
    c = frappe.db.get_value("Contact", nombre, ["full_name", "designation", "mobile_no", "phone", "email_id"],
                            as_dict=True) if nombre else None
    datos = {
        "nombre": (c and c.full_name) or doc.get("contact_display") or "",
        "puesto": (c and c.designation) or "",
        "telefono": doc.get("contact_mobile") or doc.get("contact_phone") or (c and (c.mobile_no or c.phone)) or "",
        "correo": doc.get("contact_email") or (c and c.email_id) or "",
    }
    return datos if any(datos.values()) else None


def datos_empresa(company):
    if not company or not frappe.db.exists("Company", company):
        return {"nombre": company or "", "rfc": "", "web": "", "correo": "", "telefono": ""}
    c = frappe.get_cached_doc("Company", company)
    web = re.sub(r"^https?://|/$", "", c.get("website") or "") or "www.yelke.com.mx"
    return {"nombre": c.company_name, "rfc": c.get("tax_id") or "", "web": web,
            "correo": c.get("email") or "", "telefono": telefono(c.get("phone_no")),
            "direccion": direccion_lineas(_direccion_empresa(company))}


def _direccion_empresa(company):
    try:
        from erpnext.setup.doctype.company.company import get_default_company_address

        return get_default_company_address(company)
    except Exception:
        return None


def telefono(numero):
    """4423481220 -> 442 348 1220 (lada de 3 dígitos, como se escribe en Querétaro)."""
    d = re.sub(r"\D", "", numero or "")
    if len(d) == 12 and d.startswith("52"):
        d = d[2:]
    return f"{d[:3]} {d[3:6]} {d[6:]}" if len(d) == 10 else (numero or "")


def imagen_articulo(row):
    """Imagen del renglón (si no la trae, la del artículo) como miniatura incrustada.

    Las imágenes de artículo suelen ser archivos privados: wkhtmltopdf no tiene sesión
    para pedirlos y en el PDF salían como un cuadrito vacío. Incrustada en base64 sale
    igual en el PDF, la impresión y la vista web, y la miniatura no infla el PDF."""
    url = row.get("image") or (frappe.db.get_value("Item", row.item_code, "image") if row.get("item_code") else None)
    return _miniatura(url) if url else None


@lru_cache(maxsize=256)
def _miniatura(url):
    import io

    from PIL import Image

    try:
        if url.startswith("http"):
            return url
        ruta = frappe.get_site_path(*url.lstrip("/").split("/")) if url.startswith("/private/") \
            else frappe.get_site_path("public", *url.lstrip("/").split("/"))
        im = Image.open(ruta)
        im.thumbnail((240, 240))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_corta(valor):
    """08 oct 2026 -- en español sin depender del idioma del usuario."""
    if not valor:
        return ""
    d = frappe.utils.getdate(valor)
    return f"{d.day:02d} {_MESES[d.month - 1]} {d.year}"


def fecha_hora(valor):
    if not valor:
        return ""
    dt = frappe.utils.get_datetime(valor)
    return f"{fecha_corta(dt)} · {dt:%H:%M}"


def rfc_tercero(doctype, nombre):
    return (frappe.db.get_value(doctype, nombre, "tax_id") or "") if nombre else ""


def direccion_lineas(nombre):
    """Dirección en 2-3 líneas cortas: calle · colonia / ciudad, estado / C.P."""
    if not nombre or not frappe.db.exists("Address", nombre):
        return []
    a = frappe.get_cached_doc("Address", nombre)
    lineas = [x for x in (a.address_line1, a.address_line2) if x]
    ciudad = ", ".join(x for x in (a.city, a.state) if x)
    cp = f"C.P. {a.pincode}" if a.pincode else ""
    if ciudad or cp:
        lineas.append(" · ".join(x for x in (ciudad, cp) if x))
    return lineas


def descripcion_html(desc, item_name=None):
    """Descripción de un artículo para los PDF: los renglones "- <talla> × <n>
    pza(s)" (desglose de tallas normales y extra, ver api/tallas_ov.py) salen como
    lista; los encabezados ("Desglose por talla:", "Talla: Caballero") como
    etiqueta, y el resto como párrafo."""
    from frappe.utils import escape_html

    from costeo_yelke.api.tallas_ov import texto_plano

    partes, lista = [], []

    def cerrar_lista():
        if lista:
            partes.append('<ul class="yk-lista">' + "".join(f"<li>{x}</li>" for x in lista) + "</ul>")
            lista.clear()

    for linea in texto_plano(desc).splitlines():
        linea = linea.strip()
        if not linea or (item_name and linea.upper() == item_name.strip().upper()):
            continue  # el nombre ya sale como título del renglón
        if linea.startswith(("- ", "• ")):
            lista.append(escape_html(linea[2:].strip()).replace(" × ", " <b>×</b> ").replace(" pza(s)", " pzas"))
            continue
        cerrar_lista()
        if linea.endswith(":") or linea.lower().startswith(("talla:", "tallas extra")):
            partes.append(f'<div class="yk-lista-titulo">{escape_html(linea.rstrip(":"))}</div>')
        else:
            partes.append(f"<div>{escape_html(linea)}</div>")
    cerrar_lista()
    return "".join(partes)
