"""Correos de Yelke: un solo diseño para los avisos internos (aprobaciones, asignaciones,
permisos) y para los documentos que se mandan a clientes y proveedores.

HTML de correo, no de página: tablas y estilos en línea (Outlook ignora casi todo lo
demás) y el logo por URL pública -- Gmail y Outlook bloquean las imágenes en base64.
El diseño sigue al de los PDF (templates/print/membrete.html): logo, cinta reflejante
naranja con franjas plateadas y la compañía del documento al pie.

Los correos a clientes y proveedores (correo_documento) tienen su propio diseño, más
cuidado: el documento como protagonista (folio, total, fechas, renglones), el mensaje
de quien lo manda y su firma. Se contestan a esa persona, no al buzón de
notificaciones, y llevan copia a quien aprueba (Juan). Los avisos internos le llegan
solo a cada usuario, sin copias.
"""
import re

import frappe
from frappe import _
from frappe.utils import escape_html, flt, formatdate, get_url, strip_html

NARANJA = "#ff6b15"
TINTA = "#18181b"
GRIS = "#71717a"
BORDE = "#e4e4e7"
FUENTE = "'Poppins','Segoe UI',Helvetica,Arial,sans-serif"


def logo_url():
    return get_url("/assets/costeo_yelke/images/logo-yelke-print.png")


def dinero(monto, moneda="MXN"):
    texto = f"${flt(monto):,.2f}"
    return texto if (moneda or "MXN") == "MXN" else f"{texto} {moneda}"


# ─────────────────────────────────────────────────────────────────────────────
# Resumen del documento (la tarjeta con los datos clave)
# ─────────────────────────────────────────────────────────────────────────────

def resumen_documento(doctype, name, para_cliente=False):
    """[(etiqueta, valor)] con lo que importa para decidir sin abrir nada: qué es,
    con quién, cuánto y de qué proyecto (el proyecto no va al cliente: es el nombre
    interno)."""
    if not doctype or not name or not frappe.db.exists(doctype, name):
        return []
    from costeo_yelke.api.impresion import titulo_documento

    doc = frappe.get_doc(doctype, name)
    filas = []
    if doctype == "Costeo":
        filas.append((_("Proyecto"), doc.get("titulo") or doc.name))
        if doc.get("cliente"):
            filas.append((_("Cliente"), frappe.db.get_value("Customer", doc.cliente, "customer_name") or doc.cliente))
        # Sin la venta: estos avisos también les llegan a Taller y Almacén.
        return filas

    filas.append((titulo_documento(doc), doc.name))
    if doc.get("customer_name") or doc.get("customer") or doc.get("party_name"):
        filas.append((_("Cliente"), doc.get("customer_name") or doc.get("party_name") or doc.get("customer")))
    elif doc.get("supplier_name") or doc.get("supplier"):
        filas.append((_("Proveedor"), doc.get("supplier_name") or doc.get("supplier")))
    if doc.get("grand_total"):
        filas.append((_("Total"), dinero(doc.grand_total, doc.get("currency"))))
    fecha = doc.get("transaction_date") or doc.get("posting_date")
    if fecha:
        filas.append((_("Fecha"), formatdate(fecha)))
    if doctype == "Quotation" and doc.get("valid_till"):
        filas.append((_("Vigencia"), formatdate(doc.valid_till)))
    if doctype in ("Sales Order", "Purchase Order") and (doc.get("delivery_date") or doc.get("schedule_date")):
        filas.append((_("Entrega"), formatdate(doc.get("delivery_date") or doc.get("schedule_date"))))
    if doctype == "Sales Invoice" and doc.get("due_date"):
        filas.append((_("Vence"), formatdate(doc.due_date)))
    if doc.get("costeo") and not para_cliente:
        titulo = frappe.db.get_value("Costeo", doc.costeo, "titulo")
        if titulo:
            filas.append((_("Proyecto"), titulo))
    return filas


def compania_de(doctype, name):
    if not doctype or not name or not frappe.db.exists(doctype, name):
        return None
    campo = "compañia" if doctype == "Costeo" else "company"
    return frappe.db.get_value(doctype, name, campo) if frappe.get_meta(doctype).has_field(campo) else None


# ─────────────────────────────────────────────────────────────────────────────
# Piezas del diseño
# ─────────────────────────────────────────────────────────────────────────────

def _cinta():
    celdas = "".join(f'<td style="height:4px;background:{c};font-size:0;line-height:0">&nbsp;</td>'
                     for c in (NARANJA, "#c9cdd2", NARANJA, "#c9cdd2", NARANJA))
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{celdas}</tr></table>'


def _tarjeta(filas):
    if not filas:
        return ""
    renglones = "".join(
        f'<tr><td style="padding:7px 14px;font-size:12px;color:{GRIS};white-space:nowrap;vertical-align:top">{escape_html(str(k))}</td>'
        f'<td style="padding:7px 14px;font-size:13.5px;color:{TINTA};font-weight:600;text-align:right">{escape_html(str(v))}</td></tr>'
        for k, v in filas)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:#fafafa;border:1px solid {BORDE};border-radius:10px;margin:4px 0 22px">{renglones}</table>')


def _parrafos(texto):
    """Texto del usuario (o del sistema) a párrafos: escapado, respetando renglones.
    Si ya viene en HTML (el editor de la app manda <br>), se respeta tal cual."""
    if not texto:
        return ""
    if "<" in texto and ">" in texto:
        cuerpo = texto
    else:
        cuerpo = "<br>".join(escape_html(t) for t in texto.strip().split("\n"))
    return f'<div style="font-size:14.5px;line-height:1.6;color:{TINTA};margin:0 0 18px">{cuerpo}</div>'


def _boton(texto, url):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:2px 0 8px"><tr>'
            f'<td style="background:{NARANJA};border-radius:8px">'
            f'<a href="{escape_html(url)}" style="display:inline-block;padding:11px 22px;font-family:{FUENTE};'
            f'font-size:14px;font-weight:600;color:#ffffff;text-decoration:none">{escape_html(texto)}</a>'
            f'</td></tr></table>')


def _firma(usuario, compania=None):
    """Firma de quien manda el documento: nombre, compañía, correo y teléfono."""
    if not usuario or usuario in ("Administrator", "Guest"):
        return ""
    u = frappe.db.get_value("User", usuario, ["full_name", "email", "mobile_no", "phone"], as_dict=True)
    if not u:
        return ""
    from costeo_yelke.api.impresion import telefono

    datos = " · ".join(x for x in [u.email, telefono(u.mobile_no or u.phone)] if x)
    return (f'<div style="margin:22px 0 0;padding-top:16px;border-top:1px solid {BORDE}">'
            f'<div style="font-size:14px;font-weight:600;color:{TINTA}">{escape_html(u.full_name or usuario)}</div>'
            + (f'<div style="font-size:12.5px;color:{NARANJA};font-weight:600;margin-top:1px">{escape_html(compania)}</div>' if compania else "") +
            f'<div style="font-size:12.5px;color:{GRIS};margin-top:2px">{escape_html(datos)}</div></div>')


def _pie(compania):
    from costeo_yelke.api.impresion import datos_empresa

    e = datos_empresa(compania) if compania else {"nombre": "Yelke", "web": "www.yelke.com.mx"}
    linea1 = " · ".join(x for x in [e.get("nombre"), ("RFC " + e["rfc"]) if e.get("rfc") else ""] if x)
    linea2 = " · ".join(x for x in [e.get("telefono"), e.get("correo"), e.get("web")] if x)
    direccion = ", ".join(e.get("direccion") or [])
    return (f'<div style="font-size:11.5px;line-height:1.55;color:{GRIS};text-align:center;padding:18px 24px 6px">'
            f'<b style="color:{TINTA}">{escape_html(linea1)}</b><br>{escape_html(linea2)}'
            + (f"<br>{escape_html(direccion)}" if direccion else "") + "</div>")


def html(titulo, mensaje=None, filas=None, boton=None, nota=None, firma_de=None, compania=None, etiqueta=None):
    """El correo completo. `boton` = (texto, url); `etiqueta` = la píldora sobre el
    título ("Por aprobar", "Asignación"...)."""
    pildora = (f'<span style="display:inline-block;background:#fff1e8;color:#c2410c;font-size:11.5px;font-weight:600;'
               f'letter-spacing:.3px;border-radius:999px;padding:3px 10px;margin-bottom:10px">{escape_html(etiqueta)}</span><br>'
               if etiqueta else "")
    return f"""<div style="background:#f4f4f5;padding:24px 12px;font-family:{FUENTE}">
<table role="presentation" align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto">
  <tr><td style="background:#ffffff;border:1px solid {BORDE};border-radius:14px;overflow:hidden">
    {_cinta()}
    <div style="padding:22px 28px 6px"><img src="{logo_url()}" alt="Yelke" width="120" style="display:block;width:120px;height:auto;border:0"></div>
    <div style="padding:12px 28px 26px">
      {pildora}<div style="font-size:19px;line-height:1.35;font-weight:600;color:{TINTA};margin:0 0 16px">{escape_html(titulo)}</div>
      {_parrafos(mensaje)}
      {_tarjeta(filas or [])}
      {_boton(*boton) if boton else ""}
      {f'<div style="font-size:12px;color:{GRIS};margin-top:12px">{escape_html(nota)}</div>' if nota else ""}
      {_firma(firma_de, compania)}
    </div>
  </td></tr>
  <tr><td>{_pie(compania)}</td></tr>
</table></div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Copias y envío
# ─────────────────────────────────────────────────────────────────────────────

def lista(texto):
    if isinstance(texto, (list, tuple)):
        return [t.strip() for t in texto if t and t.strip()]
    return [t.strip() for t in (texto or "").replace(";", ",").split(",") if t.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Documentos a clientes y proveedores
# ─────────────────────────────────────────────────────────────────────────────

MAX_RENGLONES = 6


def copia_direccion(excluir=()):
    """Correos de quien aprueba (Juan): copia de lo que se manda a clientes y proveedores."""
    from costeo_yelke.roles import ROL_APROBADOR, usuarios_con_rol

    fuera = {(x or "").strip().lower() for x in excluir}
    correos = frappe.get_all("User", filters={"name": ["in", usuarios_con_rol(ROL_APROBADOR) or [""]]}, pluck="email")
    return [c for c in correos if c and c.lower() not in fuera]


def datos_documento(doctype, name):
    """Lo que el correo enseña del documento, ya formateado."""
    from costeo_yelke.api.impresion import cantidad_uom, titulo_documento

    doc = frappe.get_doc(doctype, name)
    moneda = doc.get("currency") or "MXN"
    es_cliente = bool(doc.get("customer") or doc.get("party_name") or doc.get("customer_name"))
    fechas = []
    fecha = doc.get("transaction_date") or doc.get("posting_date")
    if fecha:
        fechas.append((_("Fecha"), formatdate(fecha)))
    if doctype == "Quotation" and doc.get("valid_till"):
        fechas.append((_("Vigente hasta"), formatdate(doc.valid_till)))
    if doctype in ("Sales Order", "Purchase Order") and (doc.get("delivery_date") or doc.get("schedule_date")):
        fechas.append((_("Entrega"), formatdate(doc.get("delivery_date") or doc.get("schedule_date"))))
    if doctype in ("Sales Invoice", "Purchase Invoice") and doc.get("due_date"):
        fechas.append((_("Vence"), formatdate(doc.due_date)))
    if doc.get("payment_terms_template"):
        fechas.append((_("Condiciones"), doc.payment_terms_template))
    if doctype == "Sales Order" and doc.get("po_no"):
        fechas.append((_("Su orden de compra"), doc.po_no))

    items = list(doc.get("items") or [])
    def _limpio(texto):
        return re.sub(r"[\s\-·]+$", "", strip_html(texto or "").strip())

    def _detalle(r, nombre):
        # La descripción, si dice algo más que el nombre; nunca el código interno.
        desc = _limpio(r.get("description"))
        if not desc or desc.upper().replace("-", " ") in (nombre.upper().replace("-", " "), (r.get("item_code") or "").upper().replace("-", " ")):
            return ""
        return desc if len(desc) <= 90 else desc[:88].rstrip() + "…"

    renglones = []
    for r in items[:MAX_RENGLONES]:
        nombre = _limpio(r.get("item_name") or r.get("item_code"))
        renglones.append({
            "producto": nombre, "codigo": _detalle(r, nombre),
            "cantidad": cantidad_uom(r.get("qty"), r.get("uom")),
            "importe": dinero(r.get("amount"), moneda) if flt(r.get("amount")) else "",
        })
    impuestos = flt(doc.get("total_taxes_and_charges"))
    return {
        "tipo": titulo_documento(doc), "folio": doc.name, "compania": doc.get("company"),
        "contraparte_etiqueta": _("Cliente") if es_cliente else _("Proveedor"),
        "contraparte": doc.get("customer_name") or doc.get("party_name") or doc.get("customer")
        or doc.get("supplier_name") or doc.get("supplier") or "",
        "fechas": fechas, "renglones": renglones, "mas": max(len(items) - MAX_RENGLONES, 0),
        "subtotal": dinero(doc.get("net_total"), moneda) if impuestos else "",
        "impuestos": dinero(impuestos, moneda) if impuestos else "",
        "total": dinero(doc.get("grand_total"), moneda) if flt(doc.get("grand_total")) else "",
        "moneda": moneda,
    }


def _iniciales(nombre):
    partes = [p for p in (nombre or "").split() if p[:1].isalpha()]
    return ((partes[0][0] + (partes[1][0] if len(partes) > 1 else "")) if partes else "Y").upper()


def html_documento(d, mensaje=None, firma_de=None, adjuntos=()):
    """Correo de un documento a un cliente o proveedor. `d` = datos_documento(...)."""
    from costeo_yelke.api.impresion import datos_empresa, telefono

    e = datos_empresa(d.get("compania")) if d.get("compania") else {"nombre": "Yelke", "web": "www.yelke.com.mx"}
    td = f"font-family:{FUENTE};"
    # Encabezado: logo a la izquierda, tipo y folio a la derecha.
    encabezado = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="padding:26px 32px 22px;vertical-align:middle"><img src="{logo_url()}" alt="Yelke" width="132" '
        f'style="display:block;width:132px;height:auto;border:0"></td>'
        f'<td style="{td}padding:26px 32px 22px;text-align:right;vertical-align:middle">'
        f'<div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:{GRIS};font-weight:600">{escape_html(d["tipo"])}</div>'
        f'<div style="font-size:18px;font-weight:700;color:{TINTA};margin-top:3px;white-space:nowrap">{escape_html(d["folio"])}</div>'
        f'</td></tr></table>')
    # Bloque oscuro con el total: lo primero que se busca.
    total = ""
    if d.get("total"):
        total = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{TINTA}"><tr>'
            f'<td style="{td}padding:22px 32px;vertical-align:middle">'
            f'<div style="font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:#a1a1aa;font-weight:600">{escape_html(d["contraparte_etiqueta"])}</div>'
            f'<div style="font-size:15px;color:#ffffff;font-weight:600;margin-top:4px">{escape_html(d["contraparte"])}</div></td>'
            f'<td style="{td}padding:22px 32px;text-align:right;vertical-align:middle">'
            f'<div style="font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:#a1a1aa;font-weight:600">{_("Total")}</div>'
            f'<div style="font-size:26px;color:{NARANJA};font-weight:700;margin-top:2px;white-space:nowrap">{escape_html(d["total"])}</div>'
            f'</td></tr></table>')
    # Fechas y condiciones en dos columnas.
    celdas = [f'<td width="50%" style="{td}padding:10px 0;vertical-align:top">'
              f'<div style="font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:{GRIS}">{escape_html(k)}</div>'
              f'<div style="font-size:14px;color:{TINTA};font-weight:600;margin-top:3px">{escape_html(str(v))}</div></td>'
              for k, v in d.get("fechas") or []]
    filas_fechas = "".join("<tr>" + "".join(celdas[i:i + 2]) + ("<td></td>" if len(celdas[i:i + 2]) == 1 else "") + "</tr>"
                           for i in range(0, len(celdas), 2))
    fechas = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 6px">{filas_fechas}</table>'
              if filas_fechas else "")
    # Renglones del documento.
    renglones = ""
    if d.get("renglones"):
        filas = "".join(
            f'<tr><td style="{td}padding:11px 0;border-bottom:1px solid #f0f0f1;font-size:13.5px;color:{TINTA}">'
            f'{escape_html(r["producto"])}'
            + (f'<div style="font-size:11.5px;color:{GRIS};margin-top:2px">{escape_html(r["codigo"])}</div>' if r["codigo"] else "")
            + f'</td><td style="{td}padding:11px 12px;border-bottom:1px solid #f0f0f1;font-size:13px;color:{GRIS};white-space:nowrap;text-align:right">{escape_html(r["cantidad"])}</td>'
            f'<td style="{td}padding:11px 0;border-bottom:1px solid #f0f0f1;font-size:13.5px;color:{TINTA};font-weight:600;white-space:nowrap;text-align:right">{escape_html(r["importe"])}</td></tr>'
            for r in d["renglones"])
        if d.get("mas"):
            filas += (f'<tr><td colspan="3" style="{td}padding:10px 0;font-size:12.5px;color:{GRIS}">'
                      f'{_("y {0} renglón(es) más en el PDF").format(d["mas"])}</td></tr>')
        totales = ""
        if d.get("impuestos"):
            totales = "".join(
                f'<tr><td colspan="2" style="{td}padding:6px 12px 0 0;font-size:12.5px;color:{GRIS};text-align:right">{k}</td>'
                f'<td style="{td}padding:6px 0 0;font-size:13px;color:{TINTA};text-align:right;white-space:nowrap">{escape_html(v)}</td></tr>'
                for k, v in ((_("Subtotal"), d["subtotal"]), (_("IVA"), d["impuestos"])))
            totales += (f'<tr><td colspan="2" style="{td}padding:8px 12px 0 0;font-size:13px;color:{TINTA};font-weight:600;text-align:right">{_("Total")}</td>'
                        f'<td style="{td}padding:8px 0 0;font-size:15px;color:{TINTA};font-weight:700;text-align:right;white-space:nowrap">{escape_html(d["total"])}</td></tr>')
        renglones = (
            f'<div style="{td}font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:{GRIS};font-weight:600;margin:22px 0 4px">{_("Detalle")}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas}{totales}</table>')
    # Adjuntos como "fichas".
    fichas = "".join(
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 8px 8px 0;display:inline-table"><tr>'
        f'<td style="{td}background:#fff1e8;border-radius:8px;padding:9px 12px;font-size:12.5px;color:#9a3412;font-weight:600">'
        f'<span style="display:inline-block;background:{NARANJA};color:#fff;border-radius:4px;font-size:9.5px;font-weight:700;padding:2px 5px;margin-right:7px">PDF</span>'
        f'{escape_html(a)}</td></tr></table>' for a in adjuntos or [])
    adjuntos_html = (f'<div style="{td}font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:{GRIS};font-weight:600;margin:24px 0 8px">'
                     f'{_("Adjunto")}</div>{fichas}' if fichas else "")
    # Firma de quien lo manda.
    firma = ""
    u = frappe.db.get_value("User", firma_de, ["full_name", "email", "mobile_no", "phone"], as_dict=True) \
        if firma_de and firma_de not in ("Administrator", "Guest") else None
    if u:
        contacto = " · ".join(x for x in [telefono(u.mobile_no or u.phone), u.email] if x)
        firma = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:26px;border-top:1px solid {BORDE};width:100%"><tr>'
            f'<td width="52" style="padding:20px 14px 0 0;vertical-align:top">'
            f'<div style="{td}width:44px;height:44px;line-height:44px;border-radius:22px;background:{NARANJA};color:#fff;'
            f'font-size:15px;font-weight:700;text-align:center">{escape_html(_iniciales(u.full_name))}</div></td>'
            f'<td style="{td}padding:20px 0 0;vertical-align:top">'
            f'<div style="font-size:14.5px;font-weight:700;color:{TINTA}">{escape_html(u.full_name or "")}</div>'
            f'<div style="font-size:12.5px;color:{NARANJA};font-weight:600;margin-top:1px">{escape_html(e.get("nombre") or "")}</div>'
            f'<div style="font-size:12.5px;color:{GRIS};margin-top:3px">{escape_html(contacto)}</div></td></tr></table>')
    pie_lineas = [
        " · ".join(x for x in [e.get("nombre"), ("RFC " + e["rfc"]) if e.get("rfc") else ""] if x),
        " · ".join(x for x in [e.get("telefono"), e.get("correo"), e.get("web")] if x),
        ", ".join(e.get("direccion") or []),
    ]
    pie = "<br>".join(escape_html(x) for x in pie_lineas if x)
    resumen_oculto = f'{d["tipo"]} {d["folio"]}' + (f' · {d["total"]}' if d.get("total") else "")
    return f"""<div style="background:#f4f4f5;padding:28px 12px;font-family:{FUENTE}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{escape_html(resumen_oculto)}</div>
<table role="presentation" align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;margin:0 auto">
  <tr><td style="background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid {BORDE}">
    {_cinta()}
    {encabezado}
    {total}
    <div style="padding:28px 32px 30px">
      {_parrafos(mensaje)}
      {fechas}
      {renglones}
      {adjuntos_html}
      {firma}
    </div>
  </td></tr>
  <tr><td style="{td}padding:20px 28px 4px;text-align:center;font-size:11.5px;line-height:1.6;color:{GRIS}">
    <b style="color:{TINTA}">{pie.split("<br>")[0] if pie else ""}</b>{"<br>" + "<br>".join(pie.split("<br>")[1:]) if "<br>" in pie else ""}
    <div style="margin-top:10px;font-size:10.5px;color:#a1a1aa">{_("Este correo y sus adjuntos son para uso exclusivo del destinatario. Si lo recibió por error, avísenos respondiendo a este mensaje.")}</div>
  </td></tr>
</table></div>"""


def correo_documento(doctype, name, mensaje, adjuntos=()):
    """Cuerpo del correo con el que se manda un documento a un cliente o proveedor."""
    return html_documento(datos_documento(doctype, name), mensaje, firma_de=frappe.session.user, adjuntos=adjuntos)


def enviar_documento(doctype, name, recipients, subject, mensaje, attachments=None, cc=None, now=False):
    """Manda un documento a un cliente o proveedor con el diseño de Yelke: respuesta a
    quien lo envía, `cc` capturado en la pantalla y copia a quien aprueba (Juan)."""
    destinatarios = lista(recipients)
    yo = frappe.db.get_value("User", frappe.session.user, "email") if frappe.session.user not in ("Administrator", "Guest") else None
    ya = {d.lower() for d in destinatarios}
    copia = [c for c in dict.fromkeys(lista(cc) + copia_direccion(excluir=destinatarios + [yo or ""])) if c.lower() not in ya]
    adjuntos = [a.get("fname") for a in (attachments or []) if isinstance(a, dict) and a.get("fname")]
    frappe.sendmail(
        recipients=destinatarios,
        cc=copia or None,
        reply_to=yo or None,
        subject=subject,
        message=correo_documento(doctype, name, mensaje, adjuntos),
        attachments=attachments,
        reference_doctype=doctype,
        reference_name=name,
        now=now,
    )
    return destinatarios, copia
