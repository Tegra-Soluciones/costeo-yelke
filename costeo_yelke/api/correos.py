"""Correos de Yelke: un solo diseño para los avisos internos (aprobaciones, asignaciones,
permisos) y para los documentos que se mandan a clientes y proveedores.

HTML de correo, no de página: tablas y estilos en línea (Outlook ignora casi todo lo
demás) y el logo por URL pública -- Gmail y Outlook bloquean las imágenes en base64.
El diseño sigue al de los PDF (templates/print/membrete.html): logo, cinta reflejante
naranja con franjas plateadas y la compañía del documento al pie.

Los correos a clientes y proveedores llevan copia a quien aprueba (Juan, rol Aprobador
de Documentos) y se contestan a quien los mandó, no al buzón de notificaciones.
"""
import frappe
from frappe import _
from frappe.utils import escape_html, flt, formatdate, get_url

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

def copia_direccion(excluir=()):
    """Correos de quien aprueba (Juan): reciben copia de lo que se manda a clientes y
    proveedores."""
    from costeo_yelke.roles import ROL_APROBADOR, usuarios_con_rol

    fuera = {(x or "").strip().lower() for x in excluir}
    correos = frappe.get_all("User", filters={"name": ["in", usuarios_con_rol(ROL_APROBADOR) or [""]]}, pluck="email")
    return [c for c in correos if c and c.lower() not in fuera]


def lista(texto):
    if isinstance(texto, (list, tuple)):
        return [t.strip() for t in texto if t and t.strip()]
    return [t.strip() for t in (texto or "").replace(";", ",").split(",") if t.strip()]


def correo_documento(doctype, name, mensaje, titulo=None):
    """Cuerpo del correo con el que se manda un documento a un cliente o proveedor."""
    from costeo_yelke.api.impresion import titulo_documento

    doc = frappe.get_doc(doctype, name)
    return html(
        titulo or f"{titulo_documento(doc)} {name}",
        mensaje=mensaje,
        filas=resumen_documento(doctype, name, para_cliente=True),
        nota=_("Encontrará el documento en PDF adjunto a este correo."),
        firma_de=frappe.session.user,
        compania=doc.get("company"),
    )


def enviar_documento(doctype, name, recipients, subject, mensaje, attachments=None, cc=None, now=False):
    """Manda un documento a un cliente o proveedor con el diseño de Yelke, copia a quien
    aprueba y respuesta a quien lo envía."""
    destinatarios = lista(recipients)
    copia = list(dict.fromkeys(lista(cc) + copia_direccion(excluir=destinatarios)))
    yo = frappe.db.get_value("User", frappe.session.user, "email") if frappe.session.user not in ("Administrator", "Guest") else None
    copia = [c for c in copia if c.lower() not in {d.lower() for d in destinatarios}]
    frappe.sendmail(
        recipients=destinatarios,
        cc=copia or None,
        reply_to=yo or None,
        subject=subject,
        message=correo_documento(doctype, name, mensaje),
        attachments=attachments,
        reference_doctype=doctype,
        reference_name=name,
        now=now,
    )
    return destinatarios, copia
