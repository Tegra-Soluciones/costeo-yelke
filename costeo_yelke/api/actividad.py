"""Actividad (línea de tiempo) y comentarios de los documentos del flujo
(docs/plan-panel-direccion.md §5).

No se inventa nada: es lo mismo que pinta el timeline del escritorio de ERPNext
(creación, Version, Comment, Communication) traducido a frases en español, para
que el SPA lo muestre igual en todos sus documentos. Un comentario que se escribe
aquí es un Comment normal: también se ve en /app.
"""
import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, strip_html

from costeo_yelke.api.aprobaciones import (
    APROBADO, DEVUELTO, EN_APROBACION, PENDIENTE, PREFIJO_DEVOLUCION, REVISADO,
    _aprobadores, _autor, _avisar, _describir, _revisores, _ruta_doc, _ruta_panel,
)
from costeo_yelke.roles import nivel_aprobacion

# Campos que no le dicen nada a una persona (o que ya cuenta el estado de aprobación).
_IGNORAR = {
    "modified", "modified_by", "owner", "creation", "idx", "docstatus", "amended_from",
    "estado_aprobacion_yelke", "enviado_aprobacion_por", "enviado_aprobacion_en", "aprobado_por_yelke",
    "aprobado_en_yelke", "ultimo_motivo_devolucion", "cambio_tras_envio", "revisado_yelke",
    "revisado_por_yelke", "revisado_en_yelke", "_comments", "_assign", "_liked_by", "_user_tags",
    "per_billed", "per_received", "per_delivered", "status", "billing_status", "delivery_status",
}
# De los campos calculados (solo lectura) solo interesa el total: el resto cambia solo
# cuando alguien edita una cantidad o un precio, y ese cambio ya se cuenta.
_CALCULADOS_VISIBLES = {"grand_total", "rounded_total"}
_MAX_TEXTO = 80
_MAX_CAMBIOS = 6


def _exigir_documento(doctype, name):
    from costeo_yelke.api.costeo_api import DOCTYPES_FLUJO_COSTEO

    if doctype not in DOCTYPES_FLUJO_COSTEO:
        frappe.throw(_("{0} no es un documento del flujo del costeo.").format(_(doctype)), frappe.PermissionError)
    if not frappe.db.exists(doctype, name):
        frappe.throw(_("No existe {0} {1}.").format(_(doctype), name), frappe.DoesNotExistError)


def _valor(v):
    if v in (None, ""):
        return "—"
    texto = strip_html(cstr(v)).strip()
    return texto if len(texto) <= _MAX_TEXTO else texto[:_MAX_TEXTO - 1] + "…"


def _etiqueta_campo(meta, campo):
    df = meta.get_field(campo)
    return _(df.label) if df and df.label else campo


def _se_cuenta(df, campo, antes, despues):
    if campo in _IGNORAR or campo.startswith("base_") or _valor(antes) == _valor(despues):
        return False
    if df and (df.hidden or df.fieldtype in ("Section Break", "Column Break", "Tab Break")):
        return False
    return not (df and df.read_only and campo not in _CALCULADOS_VISIBLES)


def _frases_version(meta, data):
    """Version.data -> ['Cantidad: 900 → 930', 'Agregó 1 renglón en Artículos', ...]."""
    frases, docstatus = [], None
    for campo, antes, despues in data.get("changed") or []:
        if campo == "docstatus":
            docstatus = despues
            continue
        if not _se_cuenta(meta.get_field(campo), campo, antes, despues):
            continue
        frases.append(f"{_etiqueta_campo(meta, campo)}: {_valor(antes)} → {_valor(despues)}")
    for tipo, verbo in (("added", _("Agregó")), ("removed", _("Quitó"))):
        cuenta = {}
        for tabla, _fila in data.get(tipo) or []:
            cuenta[tabla] = cuenta.get(tabla, 0) + 1
        for tabla, n in cuenta.items():
            frases.append(_("{0} {1} renglón(es) en {2}").format(verbo, n, _etiqueta_campo(meta, tabla)))
    for tabla, idx, _nombre, cambios in data.get("row_changed") or []:
        hijo = frappe.get_meta(meta.get_field(tabla).options) if meta.get_field(tabla) else None
        for campo, antes, despues in cambios or []:
            if not _se_cuenta(hijo.get_field(campo) if hijo else None, campo, antes, despues):
                continue
            etiqueta = _etiqueta_campo(hijo, campo) if hijo else campo
            frases.append(_("Renglón {0} · {1}: {2} → {3}").format(cint(idx) + 1, etiqueta, _valor(antes), _valor(despues)))
    return frases, docstatus


def _tipo_info(texto):
    t = texto.lower()
    if "reenvió" in t or "envió a aprobación" in t:
        return "envio"
    if t.startswith("lo revisó"):
        return "revision"
    if t.startswith("lo aprobó") or t.startswith("aprobó"):  # también "… en nombre de …"
        return "aprobado"
    if t.startswith("cambió después"):
        return "aviso"
    return "info"


@frappe.whitelist()
def get_actividad(doctype: str, name: str) -> dict:
    """Eventos del documento, del más viejo al más nuevo."""
    _exigir_documento(doctype, name)
    meta = frappe.get_meta(doctype)
    base = frappe.db.get_value(doctype, name, ["owner", "creation"], as_dict=True)
    eventos = [{"tipo": "crea", "usuario": base.owner, "texto": _("lo creó"), "en": base.creation}]

    for v in frappe.get_all("Version", filters={"ref_doctype": doctype, "docname": name},
                            fields=["owner", "creation", "data"], order_by="creation asc"):
        try:
            data = json.loads(v.data or "{}")
        except ValueError:
            continue
        frases, docstatus = _frases_version(meta, data)
        if docstatus == 1:
            eventos.append({"tipo": "validado", "usuario": v.owner, "texto": _("lo validó"), "en": v.creation})
        elif docstatus == 2:
            eventos.append({"tipo": "cancelado", "usuario": v.owner, "texto": _("lo canceló"), "en": v.creation})
        if frases:
            extra = len(frases) - _MAX_CAMBIOS
            eventos.append({
                "tipo": "cambio", "usuario": v.owner, "en": v.creation,
                "texto": _("hizo cambios") if len(frases) > 1 else _("cambió"),
                "detalle": frases[:_MAX_CAMBIOS] + ([_("y {0} cambio(s) más").format(extra)] if extra > 0 else []),
            })

    comentarios = frappe.get_all(
        "Comment",
        filters={"reference_doctype": doctype, "reference_name": name,
                 "comment_type": ["in", ["Comment", "Info", "Attachment", "Attachment Removed"]]},
        fields=["name", "comment_type", "comment_email", "owner", "content", "creation"],
        order_by="creation asc",
    )
    for c in comentarios:
        usuario = c.comment_email or c.owner
        texto = strip_html(c.content or "").strip()
        if c.comment_type == "Comment":
            if texto.startswith(PREFIJO_DEVOLUCION):
                eventos.append({"tipo": "devuelto", "usuario": usuario, "texto": _("lo regresó para corregir"),
                                "cita": texto[len(PREFIJO_DEVOLUCION):], "en": c.creation, "id": c.name})
            else:
                eventos.append({"tipo": "comentario", "usuario": usuario, "texto": _("comentó"),
                                "cita": texto, "en": c.creation, "id": c.name})
        elif c.comment_type == "Info":
            eventos.append({"tipo": _tipo_info(texto), "usuario": usuario, "texto": texto[:1].lower() + texto[1:],
                            "en": c.creation})
        else:
            verbo = _("adjuntó") if c.comment_type == "Attachment" else _("quitó el adjunto")
            eventos.append({"tipo": "adjunto", "usuario": usuario, "texto": f"{verbo} {texto}", "en": c.creation})

    for m in frappe.get_all("Communication",
                            filters={"reference_doctype": doctype, "reference_name": name,
                                     "communication_type": "Communication"},
                            fields=["owner", "subject", "recipients", "sent_or_received", "creation"],
                            order_by="creation asc"):
        recibido = m.sent_or_received == "Received"
        eventos.append({"tipo": "correo", "usuario": m.owner,
                        "texto": _("recibió un correo") if recibido else _("mandó por correo a {0}").format(m.recipients or ""),
                        "cita": m.subject, "en": m.creation})

    if doctype == "Costeo":
        from costeo_yelke.api.encargos import eventos_actividad
        eventos += eventos_actividad(name)

    eventos.sort(key=lambda e: e["en"])
    usuarios = {e["usuario"] for e in eventos if e.get("usuario")}
    perfiles = {u.name: u for u in frappe.get_all("User", filters={"name": ["in", list(usuarios)]},
                                                  fields=["name", "full_name", "user_image"])}
    for e in eventos:
        u = perfiles.get(e["usuario"])
        e["nombre"] = (u.full_name if u else None) or e["usuario"]
        e["imagen"] = u.user_image if u else None
    return {"eventos": eventos, "comentarios": sum(1 for e in eventos if e["tipo"] in ("comentario", "devuelto"))}


@frappe.whitelist()
def agregar_comentario(doctype: str, name: str, texto: str) -> dict:
    """Un Comment normal de Frappe (se ve también en /app). Si el documento está en
    aprobación, le avisa a la contraparte por la campana: al autor si comenta
    Dirección o el revisor, y a quien le toque decidir si comenta el autor."""
    _exigir_documento(doctype, name)
    texto = (texto or "").strip()
    if not texto:
        frappe.throw(_("Escribe el comentario."))
    doc = frappe.get_doc(doctype, name)
    doc.add_comment("Comment", frappe.utils.escape_html(texto).replace("\n", "<br>"))

    nivel = nivel_aprobacion(doctype)
    estado = doc.get("estado_aprobacion_yelke")
    if nivel and doc.docstatus == 0 and estado in (*EN_APROBACION, DEVUELTO):
        autor = _autor(doc)
        quien = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        if frappe.session.user == autor:
            destino = _revisores() if nivel == "doble" and estado == PENDIENTE else _aprobadores()
            ruta = _ruta_panel(doctype, name)
        else:
            destino, ruta = [autor], _ruta_doc(doctype, name)
        _avisar(destino, _("{0} comentó en {1}").format(quien, _describir(doc)), doctype, name,
                mensaje=texto, ruta=ruta, correo=False)
    # Encargos abiertos del proyecto: el comentario le llega a la contraparte.
    from costeo_yelke.api.encargos import avisar_comentario
    avisar_comentario(name if doctype == "Costeo" else doc.get("costeo"), texto)
    return get_actividad(doctype, name)


@frappe.whitelist()
def get_cuenta_comentarios(doctype: str, name: str) -> dict:
    """Para el botón "Actividad · n" del encabezado, sin traer toda la línea de tiempo."""
    _exigir_documento(doctype, name)
    return {"comentarios": frappe.db.count("Comment", {"reference_doctype": doctype, "reference_name": name,
                                                      "comment_type": "Comment"})}
