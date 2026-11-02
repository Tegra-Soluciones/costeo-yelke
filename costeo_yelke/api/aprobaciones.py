"""Aprobaciones de Dirección (docs/plan-panel-direccion.md §3 y §6).

Cada documento de roles.DOCUMENTOS_CON_APROBACION lleva su estado en
`estado_aprobacion_yelke` (campos del patch v0_2_60):

    Borrador --enviar--> Pendiente --(doble) revisar--> Revisado --aprobar--> Aprobado
       ^                    |                              |
       +---- reenviar --- Devuelto <------- regresar ------+

- Aprobar = validar (submit) por la MISMA puerta que ya usan las pantallas, así que
  todos los candados que ya existen se conservan (revisión previa de la OC, OC del
  cliente adjunta, PDF de la factura...).
- El candado único está en `candado_aprobacion` (before_submit): ninguna puerta, ni
  el escritorio de ERPNext, valida uno de estos documentos sin permiso de aprobar.
- No se usa el Workflow nativo: valida cada save/submit contra transiciones y la app
  guarda y valida documentos por código en muchos puntos.
- Cada paso deja su rastro como Comment (lo pinta el timeline de ERPNext y el del
  SPA) y avisa por Notification Log (campana, en tiempo real) y por correo.

Los precios acordados no son un documento con docstatus: se aprueban por costeo con
item_api.validar_precios_acordados_costeo y su devolución vive en Item Price.
"""
import frappe
from frappe import _
from frappe.utils import cint, flt, get_url, now_datetime, nowdate, time_diff_in_hours

from costeo_yelke.roles import (
    DOCUMENTOS_CON_APROBACION,
    ROL_APROBADOR,
    ROL_DIRECTOR,
    ROL_REVISOR,
    nivel_aprobacion,
    puede_aprobar_documentos,
    puede_aprobar_precios,
    puede_revisar_documentos,
    puede_ver_finanzas,
    puede_ver_panel_direccion,
    usuarios_con_rol,
)

BORRADOR, PENDIENTE, REVISADO, DEVUELTO, APROBADO = (
    "Borrador", "Pendiente", "Revisado", "Devuelto", "Aprobado")
EN_APROBACION = (PENDIENTE, REVISADO)
PREFIJO_DEVOLUCION = "Regresado para corregir: "
HORAS_RECORDATORIO = 48

# Pantalla del SPA de cada documento, para el enlace del aviso al autor. La factura
# de compra no tiene pantalla propia: se abre en el paso de su costeo (ver _ruta_doc).
_RUTA_DOC = {
    "Costeo": "/costeo-yelke/costeo/{name}",
    "Quotation": "/costeo-yelke/cotizaciones/{name}",
    "Sales Order": "/costeo-yelke/ordenes-venta/{name}",
    "Purchase Order": "/costeo-yelke/ordenes-compra/{name}",
    "Purchase Invoice": "/costeo-yelke/facturas-compra",
}


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def _etiqueta(doctype, sub=False):
    if doctype == "Purchase Order":
        return _("Orden a taller") if sub else _("Orden de compra")
    return {
        "Costeo": _("Costeo"), "Quotation": _("Cotización"), "Sales Order": _("Orden de venta"),
        "Purchase Invoice": _("Factura de compra"),
    }.get(doctype, _(doctype))


def _exigir_aprobable(doctype):
    nivel = nivel_aprobacion(doctype)
    if not nivel:
        frappe.throw(_("{0} no pasa por aprobación.").format(_(doctype)))
    return nivel


def _estado(doc):
    return doc.get("estado_aprobacion_yelke") or BORRADOR


def _autor(doc):
    """A quién se le regresa o se le avisa: quien lo envió, o su creador."""
    return doc.get("enviado_aprobacion_por") or doc.owner


def _nombre(user):
    return frappe.db.get_value("User", user, "full_name") or user


def _aprobadores():
    """Quien tiene el rol de aprobador, más quien esté aprobando HOY por delegación
    (durante la delegación los avisos les llegan a los dos)."""
    delegados = []
    if frappe.db.table_exists("Delegacion Aprobacion"):
        hoy = nowdate()
        delegados = frappe.get_all("Delegacion Aprobacion",
                                   filters={"cancelada": 0, "desde": ["<=", hoy], "hasta": [">=", hoy]},
                                   pluck="a_usuario")
    # Sin nadie con el rol de aprobador, los avisos van a Dirección: si no, un envío a
    # aprobación no le llegaba a nadie.
    return list(dict.fromkeys([*(usuarios_con_rol(ROL_APROBADOR) or usuarios_con_rol(ROL_DIRECTOR)), *delegados]))


def _revisores():
    # Sin nadie con el rol de revisor, la revisión la da el aprobador (que también
    # puede revisar, ver roles.puede_revisar_documentos).
    return usuarios_con_rol(ROL_REVISOR) or _aprobadores()


def _ruta_panel(doctype, name):
    return f"/costeo-yelke/direccion?doc={doctype}/{name}"


def _costeo_de_factura(name):
    """Costeo de una factura de compra: por la OC o el recibo de sus renglones (mismo
    camino que documentos_api.get_purchase_invoices), o por el documento del flete."""
    filas = frappe.get_all("Purchase Invoice Item", filters={"parent": name},
                           fields=["purchase_order", "purchase_receipt"])
    po = next((f.purchase_order for f in filas if f.purchase_order), None)
    if not po:
        pr = next((f.purchase_receipt for f in filas if f.purchase_receipt), None)
        if not pr and frappe.db.has_column("Purchase Invoice", "flete_origen"):
            origen = frappe.db.get_value("Purchase Invoice", name, ["flete_origen_doctype", "flete_origen"], as_dict=True) or {}
            if origen.get("flete_origen_doctype") == "Purchase Receipt":
                pr = origen.flete_origen
            elif origen.get("flete_origen_doctype") == "Delivery Note":
                so = frappe.db.get_value("Delivery Note Item", {"parent": origen.flete_origen,
                                                                "against_sales_order": ["is", "set"]}, "against_sales_order")
                return frappe.db.get_value("Sales Order", so, "costeo") if so else None
        if pr:
            po = frappe.db.get_value("Purchase Receipt Item", {"parent": pr, "purchase_order": ["is", "set"]}, "purchase_order")
    return frappe.db.get_value("Purchase Order", po, "costeo") if po and frappe.db.has_column("Purchase Order", "costeo") else None


def _ruta_doc(doctype, name):
    """Enlace al documento en el SPA. Lleva `compania` para que el SPA ponga el filtro
    de compañía en la del documento antes de abrir la pantalla (router/index.js): sin
    eso, un aviso de otra compañía abría la pantalla con el filtro equivocado."""
    from urllib.parse import quote

    ruta = (_RUTA_DOC.get(doctype) or "/costeo-yelke").format(name=quote(name))
    params = {}
    if doctype == "Purchase Invoice":
        costeo = _costeo_de_factura(name)
        if costeo:
            ruta = f"/costeo-yelke/costeo/{quote(costeo)}"
            params.update(step="7", highlight=name, doctype="Purchase Invoice")
    compania = compania_de(doctype, name)
    if compania:
        params["compania"] = compania
    return ruta + ("?" + "&".join(f"{k}={quote(str(v))}" for k, v in params.items()) if params else "")


def _monto(doc):
    if doc.doctype == "Costeo":
        return flt(sum(flt(r.total_sales_price) for r in doc.get("costeo_producto") or []))
    return flt(doc.get("grand_total"))


def _contraparte(doc):
    return (doc.get("supplier_name") or doc.get("supplier") or doc.get("customer_name")
            or doc.get("party_name") or doc.get("customer") or doc.get("cliente") or "")


def _describir(doc):
    """'Orden de compra PUR-ORD-… de GRUPO FILAFIL · $70,122.00' para avisos."""
    sub = doc.doctype == "Purchase Order" and doc.get("is_subcontracted")
    partes = [f"{_etiqueta(doc.doctype, sub)} {doc.name}"]
    if _contraparte(doc):
        partes.append(_("de {0}").format(_contraparte(doc)))
    texto = " ".join(partes)
    monto = _monto(doc)
    if monto:
        from costeo_yelke.api.correos import dinero

        texto += " · " + dinero(monto, doc.get("currency") or "MXN")
    return texto


# ─────────────────────────────────────────────────────────────────────────────
# Avisos: campana (Notification Log) + correo
# ─────────────────────────────────────────────────────────────────────────────

def _avisar(usuarios, asunto, doctype, name, mensaje="", ruta=None, boton=None, correo=True):
    """Un Notification Log por destinatario y un correo con el membrete de Yelke.

    type="Alert" para que Frappe NO mande su propio correo genérico (ver
    notification_log.get_skip_email_types): el correo lo manda esta función. Un
    correo que falla no debe tumbar la aprobación, así que solo se registra."""
    destino = {u for u in (usuarios or []) if u and u not in ("Guest", frappe.session.user)}
    destino = set(frappe.get_all(
        "User", filters={"name": ["in", list(destino)], "enabled": 1}, pluck="name")) if destino else set()
    if not destino:
        return
    for user in destino:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": asunto,
            "for_user": user,
            "type": "Alert",
            "document_type": doctype,
            "document_name": name,
            "from_user": frappe.session.user,
            "email_content": mensaje,
            "link": ruta,
        }).insert(ignore_permissions=True)

    if not correo:
        return
    correos = frappe.get_all("User", filters={"name": ["in", list(destino)]}, pluck="email")
    correos = [c for c in correos if c]
    if not correos or not _hay_correo_saliente():
        return
    try:
        frappe.sendmail(
            recipients=correos,
            subject=asunto,
            message=_correo_html(asunto, mensaje, ruta, boton or _("Abrir en Costeo Yelke"), doctype, name),
            reference_doctype=doctype,
            reference_name=name,
        )
    except Exception:
        frappe.log_error(title="Aviso de aprobación: no se pudo encolar el correo")


def _hay_correo_saliente():
    """Sin cuenta de salida (p. ej. el sandbox) frappe.sendmail truena: se omite el
    correo en silencio -- la campana basta -- en vez de llenar el Error Log."""
    return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}))


# Píldora sobre el título del correo, según de qué trata el aviso.
_ETIQUETAS = (("envió a aprobación", "Por aprobar"), ("reenvió a aprobación", "Por aprobar"),
              ("a revisión", "Por revisar"), ("revisó", "Revisado"), ("aprobó", "Aprobado"),
              ("regresó", "Por corregir"), ("asignó", "Asignación"), ("Vence hoy", "Fecha límite"),
              ("Venció", "Vencida"), ("Recordatorio", "Recordatorio"), ("canceló", "Cancelación"),
              ("documento(s)", "Pendientes"), ("terminó", "Terminado"))


def _correo_html(titulo, mensaje, ruta, boton, doctype=None, name=None):
    """Correo de aviso con el diseño de Yelke (api/correos.py): qué pasó, el mensaje de
    quien lo hizo, los datos clave del documento y el botón a la app."""
    from costeo_yelke.api.correos import compania_de, html, resumen_documento

    etiqueta = next((e for clave, e in _ETIQUETAS if clave.lower() in (titulo or "").lower()), None)
    # El título termina en el folio: proveedor, cliente y monto ya van en la tarjeta (el
    # asunto del correo sí los lleva, para leerlos desde la bandeja).
    corto = titulo.split(name)[0] + name if name and name in (titulo or "") and doctype != "Costeo" else titulo
    return html(
        corto, mensaje=mensaje, etiqueta=etiqueta,
        filas=resumen_documento(doctype, name),
        boton=(boton, get_url(ruta) if ruta else get_url("/costeo-yelke")),
        nota=_("El botón abre el documento en Costeo Yelke; desde el correo no se aprueba nada."),
        compania=compania_de(doctype, name),
    )


def _marcar_leidos(doctype, name, excepto=None):
    """El documento ya se resolvió: sus avisos pendientes dejan de ser pendientes para
    todos, salvo para su autor (a él le acaba de llegar el resultado)."""
    filtros = {"document_type": doctype, "document_name": name, "read": 0}
    if excepto:
        filtros["for_user"] = ["!=", excepto]
    for log in frappe.get_all("Notification Log", filters=filtros, pluck="name"):
        frappe.db.set_value("Notification Log", log, "read", 1, update_modified=False)


# ─────────────────────────────────────────────────────────────────────────────
# Hooks de documento (hooks.py -> doc_events, para cada DOCUMENTOS_CON_APROBACION)
# ─────────────────────────────────────────────────────────────────────────────

_CAMPOS_APROBACION = ("estado_aprobacion_yelke", "enviado_aprobacion_por", "enviado_aprobacion_en",
                      "aprobado_por_yelke", "aprobado_en_yelke", "ultimo_motivo_devolucion", "cambio_tras_envio",
                      "revisado_yelke", "revisado_por_yelke", "revisado_en_yelke")


def nace_en_borrador(doc, method=None):
    """before_insert: todo documento nuevo empieza en Borrador, venga de donde venga.
    `no_copy` no alcanza: frappe.copy_doc lo ignora por omisión, y así se crean, por
    ejemplo, las revisiones del costeo (costeo_api.crear_revision_costeo)."""
    if not nivel_aprobacion(doc.doctype):
        return
    for campo in _CAMPOS_APROBACION:
        if doc.meta.has_field(campo):
            doc.set(campo, None)
    doc.estado_aprobacion_yelke = BORRADOR


def candado_aprobacion(doc, method=None):
    """before_submit: solo quien puede aprobar valida estos documentos, entre por
    donde entre (SPA, API o escritorio de ERPNext). Los demás los envían a aprobación.

    `flags.aprobacion_yelke_sistema` es la salida para un flujo automático que deba
    validar por código a propósito; hoy ninguno la usa."""
    if not nivel_aprobacion(doc.doctype) or doc.flags.get("aprobacion_yelke_sistema"):
        return
    if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_migrate:
        return
    if puede_aprobar_documentos():
        return
    frappe.throw(
        _("{0} necesita la aprobación de Dirección: envíala a aprobación en lugar de validarla.")
        .format(_etiqueta(doc.doctype, doc.get("is_subcontracted"))),
        frappe.PermissionError,
        title=_("Requiere aprobación"),
    )


def al_validar(doc, method=None):
    """on_submit: queda Aprobado. Si venía de la bandeja, se registra y se le avisa a
    quien lo envió; si se validó directo (lo hizo quien ya puede aprobar), solo se
    marca, para que la bandeja nunca muestre algo ya validado."""
    if not nivel_aprobacion(doc.doctype):
        return
    previo = _estado(doc)
    doc.db_set({
        "estado_aprobacion_yelke": APROBADO,
        "aprobado_por_yelke": frappe.session.user,
        "aprobado_en_yelke": now_datetime(),
        "cambio_tras_envio": 0,
    }, update_modified=False)
    if previo not in EN_APROBACION:
        return
    doc.add_comment("Info", _texto_aprobo())
    autor = _autor(doc)
    _avisar(
        [autor],
        _("{0} aprobó {1}").format(_nombre(frappe.session.user), _describir(doc)),
        doc.doctype, doc.name,
        mensaje=_("Ya está validado; puedes seguir con el flujo."),
        ruta=_ruta_doc(doc.doctype, doc.name),
    )
    _marcar_leidos(doc.doctype, doc.name, excepto=autor)


def _texto_aprobo():
    """'Lo aprobó', o 'Lo aprobó en nombre de X (delegación del … al …)' si quien
    aprueba no tiene el rol y lo hace por una delegación."""
    from costeo_yelke.roles import delegacion_vigente

    roles = frappe.get_roles()
    d = None if (ROL_APROBADOR in roles or "System Manager" in roles) else delegacion_vigente()
    if not d:
        return _("Lo aprobó")
    return _("Lo aprobó en nombre de {0} (delegación del {1} al {2})").format(
        _nombre(d.de_usuario), frappe.utils.formatdate(d.desde), frappe.utils.formatdate(d.hasta))


def al_guardar(doc, method=None):
    """on_update (decisión D5 del plan): editar un documento que ya está en aprobación
    NO se bloquea -- bloquearlo rompería los guardados automáticos --, pero se marca
    'cambió después de enviarse' y, en la OC (esquema doble), se borra la revisión
    para que el revisor la vuelva a ver."""
    nivel = nivel_aprobacion(doc.doctype)
    if not nivel or doc.docstatus != 0 or _estado(doc) not in EN_APROBACION:
        return
    antes = doc.get_doc_before_save()
    if not antes:
        return
    from frappe.core.doctype.version.version import get_diff

    diff = get_diff(antes, doc)
    if not diff or not _cambio_comercial(diff):
        return
    cambios = {"cambio_tras_envio": 1}
    texto = _("Cambió después de enviarse a aprobación")
    if nivel == "doble" and _estado(doc) == REVISADO:
        cambios.update(estado_aprobacion_yelke=PENDIENTE, revisado_yelke=0,
                       revisado_por_yelke=None, revisado_en_yelke=None)
        texto += _("; la revisión se borró y hay que revisarla otra vez")
    ya_marcado = cint(doc.get("cambio_tras_envio")) and "estado_aprobacion_yelke" not in cambios
    doc.db_set(cambios, update_modified=False)
    if not ya_marcado:
        doc.add_comment("Info", texto)


def _cambio_comercial(diff):
    """¿El cambio toca la orden en sí? La ficha de manufactura del taller (campos y
    tablas om_*) se guarda junto con la OC y se vuelve a escribir en cada guardado: si
    contara, "Validar" (que guarda primero) borraría la revisión recién hecha y la
    orden nunca se podría validar."""
    def comercial(nombre):
        return not str(nombre or "").startswith("om_")
    for clave in ("changed",):
        if any(comercial(c[0]) for c in (diff.get(clave) or [])):
            return True
    for clave in ("added", "removed", "row_changed"):
        if any(comercial(c[0]) for c in (diff.get(clave) or [])):
            return True
    return False


def al_revisar(doctype, name):
    """Lo llaman las dos puertas que marcan la revisión de la OC
    (costeo_api.marcar_revisado_documento y purchase_order_api.marcar_revisada_purchase_order)
    después de guardarla."""
    if nivel_aprobacion(doctype) != "doble":
        return
    doc = frappe.get_doc(doctype, name)
    if _estado(doc) == APROBADO:
        return
    doc.db_set({"estado_aprobacion_yelke": REVISADO, "cambio_tras_envio": 0}, update_modified=False)
    doc.add_comment("Info", _("Lo revisó"))
    if puede_aprobar_documentos():
        # Quien revisa también puede aprobar (p. ej. Producción revisa y valida de un
        # jalón las OC a taller): avisarle al CEO de algo que ya se va a validar es ruido.
        return
    _avisar(
        _aprobadores(),
        _("{0} revisó {1}. Ya puedes aprobarla.").format(_nombre(frappe.session.user), _describir(doc)),
        doctype, name,
        mensaje=_("Enviada por {0}.").format(_nombre(_autor(doc))),
        ruta=_ruta_panel(doctype, name),
        boton=_("Abrir en el panel"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Acciones (SPA)
# ─────────────────────────────────────────────────────────────────────────────

def _validaciones_previas(doc):
    """Lo que de todos modos va a impedir validarlo, se avisa al enviarlo: así no le
    llega a Dirección algo que no puede aprobar."""
    if doc.doctype == "Sales Order":
        from costeo_yelke.api.costeo_api import validar_oc_cliente_adjunta
        from costeo_yelke.api.tallas_ov import validar_desglose_ov

        validar_oc_cliente_adjunta(doc)
        validar_desglose_ov(doc)
    if doc.doctype == "Purchase Invoice":
        from costeo_yelke.api.contabilidad import validar_archivos_factura

        validar_archivos_factura(doc)


@frappe.whitelist()
def enviar_a_aprobacion(doctype: str, name: str, comentario: str = None) -> dict:
    """Borrador o Devuelto -> Pendiente. Avisa al revisor (doble) o a Dirección (simple)."""
    from costeo_yelke.api.costeo_api import _vistas_de_documento
    from costeo_yelke.roles import requiere_vista

    nivel = _exigir_aprobable(doctype)
    requiere_vista(*_vistas_de_documento(doctype, name))
    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 0:
        frappe.throw(_("El documento ya está validado o cancelado."))
    estado = _estado(doc)
    if estado in EN_APROBACION:
        frappe.throw(_("Ya está en aprobación."))
    _validaciones_previas(doc)

    cambios = {
        "estado_aprobacion_yelke": PENDIENTE,
        "enviado_aprobacion_por": frappe.session.user,
        "enviado_aprobacion_en": now_datetime(),
        "cambio_tras_envio": 0,
    }
    if nivel == "doble":
        cambios.update(revisado_yelke=0, revisado_por_yelke=None, revisado_en_yelke=None)
    doc.db_set(cambios, update_modified=False)

    reenvio = estado == DEVUELTO
    doc.add_comment("Info", _("Lo corrigió y lo reenvió a aprobación") if reenvio else _("Lo envió a aprobación"))
    if (comentario or "").strip():
        doc.add_comment("Comment", frappe.utils.escape_html(comentario.strip()))

    quien = _nombre(frappe.session.user)
    verbo = _("reenvió") if reenvio else _("envió")
    if nivel == "doble":
        destino, accion = _revisores(), _("a revisión")
    else:
        destino, accion = _aprobadores(), _("a aprobación")
    _avisar(
        destino,
        f"{quien} {verbo} {accion} {_describir(doc)}",
        doctype, name,
        mensaje=(comentario or "").strip(),
        ruta=_ruta_panel(doctype, name),
        boton=_("Abrir en el panel"),
    )
    return estado_aprobacion(doctype, name)


@frappe.whitelist()
def marcar_revisado(doctype: str, name: str, comentario: str = None) -> dict:
    """Pendiente -> Revisado (solo esquema doble). Los permisos y el registro de la
    revisión son los de siempre (costeo_api._marcar_revisado), sin la vista de Producción."""
    from costeo_yelke.api.costeo_api import _marcar_revisado

    if _exigir_aprobable(doctype) != "doble":
        frappe.throw(_("Este documento no lleva revisión previa."))
    if (comentario or "").strip():
        frappe.get_doc(doctype, name).add_comment("Comment", frappe.utils.escape_html(comentario.strip()))
    _marcar_revisado(doctype, name)
    return estado_aprobacion(doctype, name)


def _validar_como_aprobador(doctype, name):
    """Valida por la puerta que ya usa la pantalla de cada documento, sin pedir la
    vista de Producción: aprobar es facultad de Dirección (o de su delegado), no de
    quien opera esa vista."""
    if doctype == "Purchase Order":
        from costeo_yelke.api.purchase_order_api import submit_purchase_order

        return submit_purchase_order(name)
    if doctype == "Quotation":
        from costeo_yelke.api.quotation_api import submit_quotation

        return submit_quotation(name)
    if doctype == "Sales Order":
        from costeo_yelke.api.sales_order_api import submit_sales_order

        return submit_sales_order(name)
    doc = frappe.get_doc(doctype, name)
    doc.flags.ignore_permissions = True
    doc.submit()
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def aprobar(doctype: str, name: str, comentario: str = None) -> dict:
    """Valida el documento. El estado, el rastro y el aviso al autor los pone al_validar."""
    _exigir_aprobable(doctype)
    if not puede_aprobar_documentos():
        frappe.throw(_("No tienes permiso para aprobar."), frappe.PermissionError)
    if frappe.db.get_value(doctype, name, "docstatus") != 0:
        frappe.throw(_("El documento ya está validado o cancelado."))
    if (comentario or "").strip():
        frappe.get_doc(doctype, name).add_comment("Comment", frappe.utils.escape_html(comentario.strip()))
    _validar_como_aprobador(doctype, name)
    return estado_aprobacion(doctype, name)


@frappe.whitelist()
def regresar(doctype: str, name: str, motivo: str) -> dict:
    """Pendiente/Revisado -> Devuelto, con el motivo OBLIGATORIO. El documento sigue en
    borrador para que su autor lo corrija; a él le llega el aviso con el motivo."""
    nivel = _exigir_aprobable(doctype)
    motivo = (motivo or "").strip()
    if len(motivo) < 5:
        frappe.throw(_("Escribe qué hay que corregir."))
    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 0:
        frappe.throw(_("El documento ya está validado o cancelado."))
    estado = _estado(doc)
    if estado not in EN_APROBACION:
        frappe.throw(_("Este documento no está en aprobación."))
    revisor_puede = nivel == "doble" and estado == PENDIENTE and puede_revisar_documentos()
    if not (puede_aprobar_documentos() or revisor_puede):
        frappe.throw(_("No tienes permiso para regresar este documento."), frappe.PermissionError)

    cambios = {"estado_aprobacion_yelke": DEVUELTO, "ultimo_motivo_devolucion": motivo,
               "cambio_tras_envio": 0}
    if nivel == "doble":
        cambios.update(revisado_yelke=0, revisado_por_yelke=None, revisado_en_yelke=None)
    doc.db_set(cambios, update_modified=False)
    doc.add_comment("Comment", frappe.utils.escape_html(PREFIJO_DEVOLUCION + motivo))

    autor = _autor(doc)
    _avisar(
        [autor],
        _("{0} te regresó {1} para corregir").format(_nombre(frappe.session.user), _describir(doc)),
        doctype, name,
        mensaje=motivo,
        ruta=_ruta_doc(doctype, name),
        boton=_("Abrir y corregir"),
    )
    _marcar_leidos(doctype, name, excepto=autor)
    return estado_aprobacion(doctype, name)


@frappe.whitelist()
def estado_aprobacion(doctype: str, name: str) -> dict:
    """Estado y botones posibles de un documento, para la franja y la barra del SPA."""
    nivel = nivel_aprobacion(doctype)
    if not nivel:
        return {"aplica": False}
    campos = ["docstatus", "owner", "estado_aprobacion_yelke", "enviado_aprobacion_por",
              "enviado_aprobacion_en", "aprobado_por_yelke", "aprobado_en_yelke",
              "ultimo_motivo_devolucion", "cambio_tras_envio"]
    if nivel == "doble":
        campos += ["revisado_por_yelke", "revisado_en_yelke"]
    d = frappe.db.get_value(doctype, name, campos, as_dict=True)
    if not d:
        frappe.throw(_("No existe {0} {1}.").format(_(doctype), name), frappe.DoesNotExistError)
    estado = d.estado_aprobacion_yelke or (APROBADO if d.docstatus == 1 else BORRADOR)
    aprueba, revisa = puede_aprobar_documentos(), puede_revisar_documentos()
    devuelto_por = None
    if estado == DEVUELTO:
        devuelto_por = frappe.db.get_value(
            "Comment",
            {"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment",
             "content": ["like", f"{frappe.utils.escape_html(PREFIJO_DEVOLUCION)}%"]},
            "comment_email", order_by="creation desc")
    borrador = d.docstatus == 0
    return {
        "aplica": True,
        "nivel": nivel,
        "estado": estado,
        "docstatus": d.docstatus,
        "enviado_por": d.enviado_aprobacion_por,
        "enviado_por_nombre": _nombre(d.enviado_aprobacion_por) if d.enviado_aprobacion_por else None,
        "enviado_en": d.enviado_aprobacion_en,
        "aprobado_por": d.aprobado_por_yelke,
        "aprobado_por_nombre": _nombre(d.aprobado_por_yelke) if d.aprobado_por_yelke else None,
        "aprobado_en": d.aprobado_en_yelke,
        "revisado_por": d.get("revisado_por_yelke"),
        "motivo_devolucion": d.ultimo_motivo_devolucion if estado == DEVUELTO else None,
        "devuelto_por": devuelto_por,
        "devuelto_por_nombre": _nombre(devuelto_por) if devuelto_por else None,
        "cambio_tras_envio": bool(d.cambio_tras_envio),
        "puede_enviar": borrador and estado in (BORRADOR, DEVUELTO),
        "puede_validar_directo": borrador and aprueba,
        "puede_revisar": borrador and nivel == "doble" and estado == PENDIENTE and revisa,
        "puede_aprobar": borrador and aprueba and (estado == REVISADO if nivel == "doble" else estado == PENDIENTE),
        "puede_regresar": borrador and estado in EN_APROBACION and (
            aprueba or (nivel == "doble" and estado == PENDIENTE and revisa)),
    }


@frappe.whitelist()
def get_permisos_aprobacion() -> dict:
    """Qué partes del panel ve el usuario: panel completo (Director), bandeja con
    aprobar, o solo 'Por revisar'."""
    from costeo_yelke.roles import ROL_DIRECTOR

    return {
        "ve_panel": puede_ver_panel_direccion(),
        # Solo el Director aterriza en el panel al abrir la app (System Manager, que es
        # el pase de desarrollador, también lo ve pero sigue entrando por Inicio).
        "es_director": ROL_DIRECTOR in frappe.get_roles(),
        "ve_finanzas": puede_ver_finanzas(),
        "puede_aprobar": puede_aprobar_documentos(),
        "puede_revisar": puede_revisar_documentos(),
        "puede_aprobar_precios": puede_aprobar_precios(),
        "delegacion": _delegacion_recibida(),
    }


def _delegacion_recibida():
    """Si el usuario aprueba HOY por una delegación: de quién y hasta cuándo."""
    from costeo_yelke.roles import delegacion_vigente

    d = delegacion_vigente()
    if not d:
        return None
    return {"de_nombre": _nombre(d.de_usuario), "hasta": str(d.hasta)}


# ─────────────────────────────────────────────────────────────────────────────
# Bandeja
# ─────────────────────────────────────────────────────────────────────────────

_CAMPOS_TARJETA = ["name", "owner", "creation", "estado_aprobacion_yelke", "enviado_aprobacion_por",
                   "enviado_aprobacion_en", "cambio_tras_envio"]
_CAMPOS_POR_DOCTYPE = {
    "Costeo": ["titulo", "cliente", "compañia"],
    "Quotation": ["company", "party_name", "customer_name", "grand_total", "currency", "costeo", "total_qty", "valid_till"],
    "Sales Order": ["company", "customer", "customer_name", "grand_total", "currency", "costeo", "total_qty",
                    "delivery_date", "oc_cliente_archivo"],
    "Purchase Order": ["company", "supplier", "supplier_name", "grand_total", "currency", "is_subcontracted", "costeo",
                       "schedule_date", "revisado_por_yelke", "revisado_en_yelke"],
    "Purchase Invoice": ["company", "supplier", "supplier_name", "grand_total", "currency", "bill_no", "posting_date",
                         "factura_pdf"],
}


def compania_de(doctype, name):
    """Compañía de un documento del flujo (el Costeo la guarda en `compañia`)."""
    campo = "compañia" if doctype == "Costeo" else "company"
    return frappe.db.get_value(doctype, name, campo) if frappe.get_meta(doctype).has_field(campo) else None


def _campos(doctype):
    meta = frappe.get_meta(doctype)
    return _CAMPOS_TARJETA + [c for c in _CAMPOS_POR_DOCTYPE.get(doctype, []) if meta.has_field(c)]


def _primeros_renglones(doctype_hijo, padres):
    """'GABARDINA NARANJA 930 Metro · y 2 más' por documento, en una sola consulta."""
    if not padres:
        return {}
    filas = frappe.get_all(doctype_hijo, filters={"parent": ["in", padres]},
                           fields=["parent", "item_name", "qty", "uom"], order_by="idx asc")
    por_padre = {}
    for f in filas:
        por_padre.setdefault(f.parent, []).append(f)
    salida = {}
    for padre, rs in por_padre.items():
        uom = (rs[0].uom or "").split(" - ")[-1]
        texto = f"{rs[0].item_name} {frappe.utils.fmt_money(rs[0].qty, precision=0)} {uom}".strip()
        if len(rs) > 1:
            texto += _(" · y {0} más").format(len(rs) - 1)
        salida[padre] = texto
    return salida


def _tarjetas(doctype, filas):
    if not filas:
        return []
    nombres = [f.name for f in filas]
    usuarios = {f.enviado_aprobacion_por or f.owner for f in filas} | {
        f.get("revisado_por_yelke") for f in filas if f.get("revisado_por_yelke")}
    nombres_usuario = dict(frappe.get_all("User", filters={"name": ["in", list(usuarios)]},
                                          fields=["name", "full_name"], as_list=True))
    extra = {}
    if doctype == "Costeo":
        for r in frappe.get_all("Costeo Producto", filters={"parent": ["in", nombres]},
                                fields=["parent", "qty", "total_sales_price", "margin_pct"]):
            e = extra.setdefault(r.parent, {"monto": 0.0, "prendas": 0, "margenes": []})
            e["monto"] += flt(r.total_sales_price)
            e["prendas"] += cint(r.qty)
            if flt(r.margin_pct):
                e["margenes"].append(flt(r.margin_pct))
    elif doctype in ("Purchase Order", "Purchase Invoice"):
        extra = _primeros_renglones(f"{doctype} Item", nombres)

    ahora = now_datetime()
    salida = []
    for f in filas:
        por = f.enviado_aprobacion_por or f.owner
        desde = f.enviado_aprobacion_en or f.creation
        t = {
            "doctype": doctype, "name": f.name, "estado": f.estado_aprobacion_yelke,
            "por": por, "por_nombre": nombres_usuario.get(por, por),
            "enviado_en": desde, "horas": round(time_diff_in_hours(ahora, desde), 1),
            "cambio_tras_envio": bool(f.cambio_tras_envio),
            "moneda": f.get("currency") or "MXN", "bloqueo": None,
            # El panel junta documentos de todas las compañías: cada tarjeta dice de cuál
            # es, y al abrir el documento original el SPA cambia el filtro a esa.
            "compania": f.get("company") or f.get("compañia"),
        }
        if doctype == "Costeo":
            e = extra.get(f.name) or {"monto": 0.0, "prendas": 0, "margenes": []}
            margen = sum(e["margenes"]) / len(e["margenes"]) if e["margenes"] else None
            t.update(tipo="costeo", titulo=f.titulo or f.name, monto=e["monto"] or None,
                     sub=" · ".join(x for x in [f.cliente, _("{0} prendas").format(e["prendas"]) if e["prendas"] else "",
                                                _("margen {0} %").format(round(margen, 1)) if margen is not None else ""] if x),
                     margen=margen, contexto=f.name)
        elif doctype == "Quotation":
            t.update(tipo="cot", titulo=f.customer_name or f.party_name, monto=f.grand_total,
                     sub=_("{0} piezas").format(frappe.utils.fmt_money(f.total_qty, precision=0))
                     + (_(" · vigente al {0}").format(frappe.utils.formatdate(f.valid_till)) if f.valid_till else ""),
                     contexto=f.costeo)
        elif doctype == "Sales Order":
            t.update(tipo="ov", titulo=f.customer_name or f.customer, monto=f.grand_total,
                     sub=_("{0} piezas · entrega {1}").format(
                         frappe.utils.fmt_money(f.total_qty, precision=0), frappe.utils.formatdate(f.delivery_date)),
                     contexto=f.costeo)
            if "oc_cliente_archivo" in f and not (f.oc_cliente_archivo or "").strip():
                t["bloqueo"] = _("Falta la OC del cliente")
        elif doctype == "Purchase Order":
            t.update(tipo="oc-maq" if f.is_subcontracted else "oc-mp", titulo=f.supplier_name or f.supplier,
                     monto=f.grand_total, sub=extra.get(f.name, ""), contexto=f.costeo,
                     revisado_por=f.revisado_por_yelke,
                     revisado_por_nombre=nombres_usuario.get(f.revisado_por_yelke, f.revisado_por_yelke)
                     if f.revisado_por_yelke else None,
                     revisado_en=f.revisado_en_yelke)
        elif doctype == "Purchase Invoice":
            t.update(tipo="fc", titulo=f.supplier_name or f.supplier, monto=f.grand_total,
                     sub=extra.get(f.name, "") + (f" · {f.bill_no}" if f.bill_no else ""), contexto=None)
            # Proveedor sin alta en el SAT: no emite factura, el PDF es opcional
            # (contabilidad.validar_archivos_factura tampoco lo exige al validar).
            sin_sat = frappe.db.get_value("Supplier", f.supplier, "sin_alta_sat") if f.get("supplier") else 0
            if "factura_pdf" in f and not (f.factura_pdf or "").strip() and not sin_sat:
                t["bloqueo"] = _("Falta el PDF de la factura")
        t["etiqueta"] = _etiqueta(doctype, f.get("is_subcontracted"))
        salida.append(t)
    return salida


def _tarjetas_precios():
    """Precios acordados capturados y sin validar, uno por costeo (se validan juntos)."""
    if not frappe.db.has_column("Item Price", "costeo"):
        return []
    filtros = {"costeo": ["is", "set"], "precio_acordado_validado": 0}
    if frappe.db.has_column("Item Price", "precio_devuelto_yelke"):
        filtros["precio_devuelto_yelke"] = 0
    filas = frappe.get_all("Item Price", filters=filtros,
                           fields=["name", "costeo", "item_code", "item_name", "customer", "price_list_rate",
                                   "valid_from", "valid_upto", "owner", "modified", "currency"],
                           order_by="item_code asc")
    por_costeo = {}
    for f in filas:
        por_costeo.setdefault(f.costeo, []).append(f)
    ahora = now_datetime()
    salida = []
    for costeo, rs in por_costeo.items():
        mas_reciente = max(r.modified for r in rs)
        precios = " · ".join(f"{r.item_name or r.item_code} {frappe.utils.fmt_money(r.price_list_rate, currency=r.currency)}"
                             for r in rs[:2]) + (_(" · y {0} más").format(len(rs) - 2) if len(rs) > 2 else "")
        salida.append({
            "doctype": "Costeo", "name": costeo, "tipo": "precio", "etiqueta": _("Precio acordado"),
            "estado": PENDIENTE, "titulo": rs[0].customer, "monto": None, "moneda": rs[0].currency,
            "sub": precios, "contexto": costeo, "precios": len(rs), "compania": compania_de("Costeo", costeo),
            "por": rs[0].owner, "por_nombre": _nombre(rs[0].owner),
            "enviado_en": mas_reciente, "horas": round(time_diff_in_hours(ahora, mas_reciente), 1),
            "cambio_tras_envio": False, "bloqueo": None,
        })
    return salida


@frappe.whitelist()
def get_bandeja() -> dict:
    """Lo que le toca al usuario, de lo que más espera a lo más nuevo.

    Aprobador: simple en Pendiente + doble ya Revisado (+ precios si los aprueba), y
    aparte, solo informativo, lo doble que todavía espera revisión.
    Revisor (sin aprobar): solo lo doble en Pendiente."""
    aprueba, revisa, precios = puede_aprobar_documentos(), puede_revisar_documentos(), puede_aprobar_precios()
    if not (aprueba or revisa or precios):
        frappe.throw(_("No tienes documentos por aprobar ni por revisar."), frappe.PermissionError)
    items, esperando = [], []
    # Sin nadie con el rol de revisor, la revisión la da quien aprueba (_revisores):
    # lo doble en Pendiente le llega en su bandeja para revisarlo y luego aprobarlo.
    # Antes solo lo veía "esperando revisión" -- apagado y sin poder abrirse -- y las
    # órdenes a talleres se quedaban atoradas.
    sin_revisores = not usuarios_con_rol(ROL_REVISOR)
    for doctype, nivel in DOCUMENTOS_CON_APROBACION.items():
        if aprueba:
            estados = ([PENDIENTE, REVISADO] if sin_revisores else [REVISADO]) if nivel == "doble" else [PENDIENTE]
        elif revisa and nivel == "doble":
            estados = [PENDIENTE]
        else:
            continue
        filas = frappe.get_all(doctype, filters={"docstatus": 0, "estado_aprobacion_yelke": ["in", estados]},
                               fields=_campos(doctype))
        items += _tarjetas(doctype, filas)
        if aprueba and nivel == "doble" and not sin_revisores:
            filas = frappe.get_all(doctype, filters={"docstatus": 0, "estado_aprobacion_yelke": PENDIENTE},
                                   fields=_campos(doctype))
            esperando += _tarjetas(doctype, filas)
    if precios:
        items += _tarjetas_precios()
    items.sort(key=lambda t: -t["horas"])
    return {
        "items": items,
        "esperando_revision": esperando,
        "resueltos_hoy": _resueltos_hoy(),
        "permisos": get_permisos_aprobacion(),
    }


@frappe.whitelist()
def get_cuenta_bandeja() -> dict:
    """Solo la cuenta, para el contador del menú (sin armar las tarjetas)."""
    aprueba, revisa, precios = puede_aprobar_documentos(), puede_revisar_documentos(), puede_aprobar_precios()
    total = 0
    sin_revisores = not usuarios_con_rol(ROL_REVISOR)  # ver get_bandeja
    for doctype, nivel in DOCUMENTOS_CON_APROBACION.items():
        if aprueba:
            estados = ([PENDIENTE, REVISADO] if sin_revisores else [REVISADO]) if nivel == "doble" else [PENDIENTE]
        elif revisa and nivel == "doble":
            estados = [PENDIENTE]
        else:
            continue
        total += frappe.db.count(doctype, {"docstatus": 0, "estado_aprobacion_yelke": ["in", estados]})
    if precios and frappe.db.has_column("Item Price", "costeo"):
        filtros = {"costeo": ["is", "set"], "precio_acordado_validado": 0}
        if frappe.db.has_column("Item Price", "precio_devuelto_yelke"):
            filtros["precio_devuelto_yelke"] = 0
        total += len(set(frappe.get_all("Item Price", filters=filtros, pluck="costeo")))
    return {"total": total, "devueltos": len(get_mis_devueltos()["items"])}


def _resueltos_hoy():
    """Lo que el usuario aprobó, revisó o regresó hoy (lista corta, colapsada en el panel)."""
    user, hoy = frappe.session.user, nowdate()
    salida = []
    for doctype in DOCUMENTOS_CON_APROBACION:
        for f in frappe.get_all(doctype, filters={"aprobado_por_yelke": user, "aprobado_en_yelke": [">=", hoy]},
                                fields=["name", "aprobado_en_yelke"]):
            salida.append({"doctype": doctype, "name": f.name, "resultado": APROBADO, "en": f.aprobado_en_yelke})
    comentarios = frappe.get_all(
        "Comment",
        filters={"comment_email": user, "creation": [">=", hoy],
                 "reference_doctype": ["in", list(DOCUMENTOS_CON_APROBACION)],
                 "comment_type": ["in", ["Comment", "Info"]]},
        fields=["reference_doctype", "reference_name", "content", "comment_type", "creation"],
        order_by="creation desc",
    )
    for c in comentarios:
        contenido = frappe.utils.strip_html(c.content or "")
        if c.comment_type == "Comment" and contenido.startswith(PREFIJO_DEVOLUCION):
            salida.append({"doctype": c.reference_doctype, "name": c.reference_name, "resultado": DEVUELTO,
                           "motivo": contenido[len(PREFIJO_DEVOLUCION):], "en": c.creation})
        elif c.comment_type == "Info" and contenido == _("Lo revisó") and not puede_aprobar_documentos():
            salida.append({"doctype": c.reference_doctype, "name": c.reference_name, "resultado": REVISADO,
                           "en": c.creation})
    salida.sort(key=lambda r: str(r["en"]), reverse=True)
    return salida


def ruta_ov_cancelada(name):
    """Enlace al costeo de una OV cancelada, en Vender y resaltando esa OV."""
    from urllib.parse import quote

    costeo = frappe.db.get_value("Sales Order", name, "costeo")
    if not costeo:
        return _ruta_doc("Sales Order", name)
    params = {"step": "2", "highlight": name, "doctype": "Sales Order"}
    compania = compania_de("Sales Order", name)
    if compania:
        params["compania"] = compania
    return f"/costeo-yelke/costeo/{quote(costeo)}?" + "&".join(f"{k}={quote(str(v))}" for k, v in params.items())


def _ov_canceladas_por_rehacer(user):
    """OV que se cancelaron y le toca rehacer a `user` (costeo_api.cancelar_orden_venta):
    salen mientras su costeo no tenga una OV nueva viva creada después de cancelarse."""
    if not frappe.db.has_column("Sales Order", "rehacer_por"):
        return []
    salida = []
    for f in frappe.get_all("Sales Order", filters={"docstatus": 2, "rehacer_por": user},
                            fields=["name", "costeo", "motivo_cancelacion", "modified"]):
        if f.costeo and frappe.db.exists("Sales Order", {
                "costeo": f.costeo, "docstatus": ["<", 2], "creation": [">", f.modified]}):
            continue
        salida.append({"doctype": "Sales Order", "name": f.name, "etiqueta": _("Orden de venta cancelada"),
                       "motivo": f.motivo_cancelacion, "ruta": ruta_ov_cancelada(f.name),
                       "compania": compania_de("Sales Order", f.name), "accion": _("Rehacer")})
    return salida


@frappe.whitelist()
def get_mis_devueltos() -> dict:
    """Lo que le regresaron al usuario y no ha reenviado (campana + Inicio del empleado):
    documentos devueltos en aprobación y órdenes de venta canceladas que le toca rehacer."""
    user = frappe.session.user
    salida = _ov_canceladas_por_rehacer(user)
    for doctype in DOCUMENTOS_CON_APROBACION:
        for f in frappe.get_all(
                doctype,
                filters={"docstatus": 0, "estado_aprobacion_yelke": DEVUELTO},
                or_filters={"enviado_aprobacion_por": user, "owner": user},
                fields=["name", "enviado_aprobacion_por", "owner", "ultimo_motivo_devolucion", "modified"]):
            if (f.enviado_aprobacion_por or f.owner) != user:
                continue
            salida.append({"doctype": doctype, "name": f.name, "etiqueta": _etiqueta(doctype),
                           "motivo": f.ultimo_motivo_devolucion, "ruta": _ruta_doc(doctype, f.name),
                           "compania": compania_de(doctype, f.name)})
    return {"items": salida}


# ─────────────────────────────────────────────────────────────────────────────
# Precios acordados
# ─────────────────────────────────────────────────────────────────────────────

def _precios_pendientes(costeo):
    filtros = {"costeo": costeo, "precio_acordado_validado": 0}
    if frappe.db.has_column("Item Price", "precio_devuelto_yelke"):
        filtros["precio_devuelto_yelke"] = 0
    return frappe.get_all("Item Price", filters=filtros, fields=["name", "owner"])


@frappe.whitelist()
def aprobar_precios(costeo: str, comentario: str = None) -> dict:
    from costeo_yelke.api.item_api import validar_precios_acordados_costeo

    pendientes = _precios_pendientes(costeo)
    r = validar_precios_acordados_costeo(costeo)
    doc = frappe.get_doc("Costeo", costeo)
    if (comentario or "").strip():
        doc.add_comment("Comment", frappe.utils.escape_html(comentario.strip()))
    doc.add_comment("Info", _texto_aprobo().replace(_("Lo aprobó"), _("Aprobó los precios acordados"), 1))
    _avisar({p.owner for p in pendientes},
            _("{0} aprobó los precios acordados del costeo {1}").format(_nombre(frappe.session.user), costeo),
            "Costeo", costeo, ruta=_ruta_doc("Costeo", costeo))
    _marcar_leidos("Costeo", costeo)
    return r


@frappe.whitelist()
def regresar_precios(costeo: str, motivo: str) -> dict:
    if not puede_aprobar_precios():
        frappe.throw(_("Solo Dirección puede regresar precios acordados."), frappe.PermissionError)
    motivo = (motivo or "").strip()
    if len(motivo) < 5:
        frappe.throw(_("Escribe qué hay que corregir."))
    pendientes = _precios_pendientes(costeo)
    if not pendientes:
        frappe.throw(_("No hay precios acordados por aprobar en este costeo."))
    for p in pendientes:
        frappe.db.set_value("Item Price", p.name, {"precio_devuelto_yelke": 1, "precio_motivo_devolucion": motivo},
                            update_modified=False)
    frappe.get_doc("Costeo", costeo).add_comment(
        "Comment", frappe.utils.escape_html(PREFIJO_DEVOLUCION + _("precios acordados. ") + motivo))
    _avisar({p.owner for p in pendientes},
            _("{0} te regresó los precios acordados del costeo {1} para corregir").format(
                _nombre(frappe.session.user), costeo),
            "Costeo", costeo, mensaje=motivo, ruta=_ruta_doc("Costeo", costeo), boton=_("Abrir y corregir"))
    _marcar_leidos("Costeo", costeo)
    return {"ok": True, "regresados": len(pendientes)}


# ─────────────────────────────────────────────────────────────────────────────
# Recordatorio diario (scheduler)
# ─────────────────────────────────────────────────────────────────────────────

def recordatorio_pendientes():
    """Una vez al día: a quien tiene algo esperando más de 48 h, UN aviso con la cuenta
    (no uno por documento)."""
    limite = frappe.utils.add_to_date(now_datetime(), hours=-HORAS_RECORDATORIO)
    para_aprobar, para_revisar = [], []
    for doctype, nivel in DOCUMENTOS_CON_APROBACION.items():
        base = {"docstatus": 0, "enviado_aprobacion_en": ["<", limite]}
        if nivel == "doble":
            para_aprobar += frappe.get_all(doctype, filters={**base, "estado_aprobacion_yelke": REVISADO}, pluck="name")
            para_revisar += frappe.get_all(doctype, filters={**base, "estado_aprobacion_yelke": PENDIENTE}, pluck="name")
        else:
            para_aprobar += frappe.get_all(doctype, filters={**base, "estado_aprobacion_yelke": PENDIENTE}, pluck="name")

    def _uno(usuarios, n, que):
        if not n:
            return
        asunto = _("Tienes {0} documento(s) {1} desde hace más de 48 h").format(n, que)
        for user in usuarios:
            frappe.get_doc({"doctype": "Notification Log", "subject": asunto, "for_user": user,
                            "type": "Alert", "link": "/costeo-yelke/direccion"}).insert(ignore_permissions=True)
        correos = [c for c in frappe.get_all("User", filters={"name": ["in", usuarios]}, pluck="email") if c]
        if correos and _hay_correo_saliente():
            try:
                frappe.sendmail(recipients=correos, subject=asunto,
                                message=_correo_html(asunto, _("Ábrelos desde el panel de Dirección."),
                                                     "/costeo-yelke/direccion", _("Abrir el panel")))
            except Exception:
                frappe.log_error(title="Recordatorio de aprobaciones: no se pudo encolar el correo")

    _uno(_aprobadores(), len(para_aprobar), _("esperando tu aprobación"))
    revisores = [u for u in usuarios_con_rol(ROL_REVISOR) if u not in _aprobadores()]
    _uno(revisores, len(para_revisar), _("esperando tu revisión"))
