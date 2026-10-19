"""Delegación de las aprobaciones de Dirección (docs/plan-panel-direccion.md, Fase 7).

Para el CEO son tres datos: a quién, desde y hasta. Se termina sola el día "hasta"
y se puede terminar antes. No se reparten ni quitan roles: roles.delegacion_vigente
le da al delegado el permiso de aprobar solo mientras las fechas estén vigentes, así
que no hay un job que olvide quitar nada ni choca con el Perfil de Rol.

El delegado aprueba y regresa documentos (bandeja), pero no ve Proyectos ni Resumen.
"""
import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, now_datetime, nowdate

from costeo_yelke.api.aprobaciones import _avisar, _nombre
from costeo_yelke.roles import (
    ROL_APROBADOR, ROL_DIRECTOR, ROL_REVISOR, olvidar_delegaciones, puede_ver_panel_direccion,
)

_RUTA_PANEL = "/costeo-yelke/direccion"


def _exigir_quien_delega():
    if not (puede_ver_panel_direccion() or "Supervisor Yelke" in frappe.get_roles()):
        frappe.throw(_("Solo Dirección puede delegar sus aprobaciones."), frappe.PermissionError)


def _fila(d):
    hoy = getdate(nowdate())
    if d.cancelada:
        estado = "Terminada"
    elif getdate(d.desde) > hoy:
        estado = "Programada"
    elif getdate(d.hasta) < hoy:
        estado = "Vencida"
    else:
        estado = "Activa"
    return {
        "name": d.name, "a_usuario": d.a_usuario, "a_nombre": _nombre(d.a_usuario),
        "de_usuario": d.de_usuario, "de_nombre": _nombre(d.de_usuario),
        "desde": str(d.desde), "hasta": str(d.hasta), "motivo": d.motivo, "estado": estado,
    }


def _rol_corto(roles):
    for rol, texto in ((ROL_REVISOR, _("Revisor")), ("Comprador Yelke", _("Compras")), ("Costeador Yelke", _("Costeos")),
                       ("Vendedor Yelke", _("Ventas")), ("Facturador Yelke", _("Facturas")), (ROL_APROBADOR, _("Aprobador")),
                       ("Supervisor Yelke", _("Supervisor"))):
        if rol in roles:
            return texto
    return ""


@frappe.whitelist()
def get_delegacion() -> dict:
    """La delegación activa o programada del usuario, las últimas terminadas y a quién
    se puede delegar."""
    _exigir_quien_delega()
    user = frappe.session.user
    filas = frappe.get_all("Delegacion Aprobacion", filters={"de_usuario": user},
                           fields=["name", "de_usuario", "a_usuario", "desde", "hasta", "motivo", "cancelada"],
                           order_by="desde desc", limit=10)
    filas = [_fila(f) for f in filas]
    candidatos = []
    for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User",
                                             "name": ["not in", ["Administrator", "Guest", user]]},
                            fields=["name", "full_name"], order_by="full_name asc"):
        roles = set(frappe.get_all("Has Role", filters={"parent": u.name, "parenttype": "User"}, pluck="role"))
        if ROL_DIRECTOR in roles:
            continue
        candidatos.append({"name": u.name, "nombre": u.full_name or u.name, "rol": _rol_corto(roles),
                           "revisor": ROL_REVISOR in roles})
    candidatos.sort(key=lambda c: (not c["revisor"], c["nombre"].lower()))
    return {
        "activa": next((f for f in filas if f["estado"] == "Activa"), None),
        "programadas": [f for f in filas if f["estado"] == "Programada"],
        "anteriores": [f for f in filas if f["estado"] in ("Terminada", "Vencida")][:5],
        "candidatos": candidatos,
        "hoy": nowdate(),
    }


@frappe.whitelist()
def crear_delegacion(a_usuario: str, desde: str, hasta: str, motivo: str = None) -> dict:
    _exigir_quien_delega()
    doc = frappe.get_doc({
        "doctype": "Delegacion Aprobacion", "de_usuario": frappe.session.user, "a_usuario": a_usuario,
        "desde": desde, "hasta": hasta, "motivo": (motivo or "").strip() or None,
    })
    doc.insert(ignore_permissions=True)
    olvidar_delegaciones()
    quien = _nombre(frappe.session.user)
    if getdate(desde) <= getdate(nowdate()):
        asunto = _("{0} te dejó aprobando en su lugar hasta el {1}").format(quien, formatdate(hasta))
        mensaje = _("Desde hoy ves la bandeja de aprobaciones en Costeo Yelke. Se termina sola el {0}.").format(formatdate(hasta))
    else:
        asunto = _("{0} te dejará aprobando en su lugar del {1} al {2}").format(quien, formatdate(desde), formatdate(hasta))
        mensaje = _("El {0} te llegará otro aviso cuando empiece.").format(formatdate(desde))
    _avisar([a_usuario], asunto, "Delegacion Aprobacion", doc.name, mensaje=mensaje, ruta=_RUTA_PANEL,
            boton=_("Abrir las aprobaciones"))
    return get_delegacion()


@frappe.whitelist()
def terminar_delegacion(name: str) -> dict:
    """Termina ahora una delegación activa o cancela una programada."""
    _exigir_quien_delega()
    doc = frappe.get_doc("Delegacion Aprobacion", name)
    if doc.de_usuario != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Esa delegación no es tuya."), frappe.PermissionError)
    if doc.cancelada:
        return get_delegacion()
    empezo = getdate(doc.desde) <= getdate(nowdate())
    doc.db_set({"cancelada": 1, "cancelada_en": now_datetime(),
                # Si ya había empezado, termina hoy; si no, queda sin ningún día.
                "hasta": max(getdate(doc.desde), getdate(add_days(nowdate(), -1))) if empezo else doc.hasta})
    olvidar_delegaciones()
    _avisar([doc.a_usuario],
            _("{0} terminó la delegación: ya no apruebas en su lugar").format(_nombre(frappe.session.user)) if empezo
            else _("{0} canceló la delegación del {1}").format(_nombre(frappe.session.user), formatdate(doc.desde)),
            "Delegacion Aprobacion", doc.name, ruta=_RUTA_PANEL, correo=False)
    return get_delegacion()


def avisos_delegacion():
    """Diario (scheduler): al delegado, el día que empieza y el último día."""
    hoy = nowdate()
    for d in frappe.get_all("Delegacion Aprobacion", filters={"cancelada": 0, "desde": hoy},
                            fields=["name", "de_usuario", "a_usuario", "hasta", "creation"]):
        if getdate(d.creation) == getdate(hoy):
            continue  # se creó hoy: el aviso ya salió al crearla
        frappe.set_user(d.de_usuario)
        _avisar([d.a_usuario], _("Desde hoy apruebas en lugar de {0}, hasta el {1}").format(
            _nombre(d.de_usuario), formatdate(d.hasta)), "Delegacion Aprobacion", d.name, ruta=_RUTA_PANEL,
            boton=_("Abrir las aprobaciones"))
    for d in frappe.get_all("Delegacion Aprobacion", filters={"cancelada": 0, "hasta": hoy},
                            fields=["name", "de_usuario", "a_usuario"]):
        frappe.set_user(d.de_usuario)
        _avisar([d.a_usuario], _("Hoy es tu último día aprobando en lugar de {0}").format(_nombre(d.de_usuario)),
                "Delegacion Aprobacion", d.name, ruta=_RUTA_PANEL, correo=False)
    frappe.set_user("Administrator")
