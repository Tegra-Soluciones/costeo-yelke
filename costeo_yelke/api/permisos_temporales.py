"""Préstamo temporal de permisos (panel de Dirección).

Dirección presta los permisos de un usuario a otro por unos días -- p. ej. Ana sale de
vacaciones y Pedro la cubre: Pedro recibe los roles de Ana que él no tiene, del día
"desde" al día "hasta", y al terminar se le quitan solo esos.

A diferencia de la delegación de aprobaciones (api/delegacion.py, que no reparte roles
y solo revisa fechas), aquí sí se agregan roles reales: los permisos de cada vista y
documento dependen de ellos. Dos detalles para que no se pierdan ni se queden:
  · el Perfil de Rol reescribe los roles del usuario cada vez que se guarda
    (User.validate_roles); el hook conservar_roles_prestados los vuelve a poner;
  · un job cada hora (procesar_permisos_temporales) aplica los programados y retira
    los vencidos.

Los roles de aprobar no se prestan aquí: eso se delega aparte, con sus propias reglas.
"""
import json

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate, now_datetime, nowdate

from costeo_yelke.api.aprobaciones import _avisar, _nombre
from costeo_yelke.roles import ROL_APROBADOR, ROL_CEO_LEGACY, ROL_DIRECTOR, puede_ver_panel_direccion

_RUTA_INICIO = "/costeo-yelke/"

# Nunca se prestan: administración y aprobaciones (esas van por la delegación).
NO_PRESTABLES = {"Administrator", "System Manager", "Guest", "All", "Desk User",
                 ROL_DIRECTOR, ROL_APROBADOR, ROL_CEO_LEGACY, "Aprobador de Precios Yelke"}


def _exigir_direccion():
    if not puede_ver_panel_direccion():
        frappe.throw(_("Solo Dirección puede prestar permisos."), frappe.PermissionError)


def _roles(user):
    return set(frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role"))


def roles_prestables(user):
    return sorted(r for r in _roles(user) if r not in NO_PRESTABLES)


def _activos_de(user, excepto=None):
    """Préstamos aplicados y vigentes que recibe `user` (para no quitarle un rol que
    otro préstamo también le da)."""
    filtros = {"a_usuario": user, "aplicado": 1, "terminado": 0}
    if excepto:
        filtros["name"] = ["!=", excepto]
    return frappe.get_all("Permiso Temporal Yelke", filters=filtros, fields=["name", "roles_agregados"])


def _fila(d):
    hoy = getdate(nowdate())
    if d.terminado:
        estado = "Terminado"
    elif getdate(d.desde) > hoy:
        estado = "Programado"
    elif getdate(d.hasta) < hoy:
        estado = "Vencido"
    else:
        estado = "Activo"
    return {
        "name": d.name, "estado": estado, "desde": str(d.desde), "hasta": str(d.hasta), "motivo": d.motivo,
        "de_usuario": d.de_usuario, "de_nombre": _nombre(d.de_usuario),
        "a_usuario": d.a_usuario, "a_nombre": _nombre(d.a_usuario),
        "roles": json.loads(d.roles_agregados or "[]"),
    }


@frappe.whitelist()
def get_permisos_temporales() -> dict:
    """Préstamos activos, programados y los últimos terminados, y los usuarios entre
    los que se puede prestar."""
    _exigir_direccion()
    filas = [_fila(f) for f in frappe.get_all(
        "Permiso Temporal Yelke",
        fields=["name", "de_usuario", "a_usuario", "desde", "hasta", "motivo", "roles_agregados", "terminado"],
        order_by="desde desc", limit=30)]
    usuarios = []
    for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User",
                                             "name": ["not in", ["Administrator", "Guest"]]},
                            fields=["name", "full_name"], order_by="full_name asc"):
        roles = _roles(u.name)
        if ROL_DIRECTOR in roles:
            continue
        usuarios.append({"name": u.name, "nombre": u.full_name or u.name,
                         "roles": [r for r in sorted(roles) if r not in NO_PRESTABLES]})
    # Nombre de cada rol en español (los de ERPNext vienen en inglés: "Purchase User").
    etiquetas = {r: _(r).replace(" Yelke", "") for u in usuarios for r in u["roles"]}
    return {
        "etiquetas": etiquetas,
        "activos": [f for f in filas if f["estado"] == "Activo"],
        "programados": [f for f in filas if f["estado"] == "Programado"],
        "anteriores": [f for f in filas if f["estado"] in ("Terminado", "Vencido")][:5],
        "usuarios": usuarios,
        "hoy": nowdate(),
    }


@frappe.whitelist()
def crear_permiso_temporal(de_usuario: str, a_usuario: str, desde: str, hasta: str, motivo: str = None) -> dict:
    _exigir_direccion()
    if de_usuario == a_usuario:
        frappe.throw(_("Elige a otra persona para recibir los permisos."))
    if getdate(hasta) < getdate(desde):
        frappe.throw(_("La fecha final no puede ser antes de la inicial."))
    if getdate(hasta) < getdate(nowdate()):
        frappe.throw(_("Ese periodo ya pasó."))
    faltan = set(roles_prestables(de_usuario)) - _roles(a_usuario)
    if not faltan:
        frappe.throw(_("{0} ya tiene todos los permisos de {1}.").format(_nombre(a_usuario), _nombre(de_usuario)))

    doc = frappe.get_doc({
        "doctype": "Permiso Temporal Yelke", "de_usuario": de_usuario, "a_usuario": a_usuario,
        "desde": desde, "hasta": hasta, "motivo": (motivo or "").strip() or None,
        "otorgado_por": frappe.session.user,
    })
    doc.insert(ignore_permissions=True)
    quien = _nombre(frappe.session.user)
    if getdate(desde) <= getdate(nowdate()):
        _aplicar(doc)
        asunto = _("{0} te prestó los permisos de {1} hasta el {2}").format(quien, _nombre(de_usuario), formatdate(hasta))
        mensaje = _("Desde hoy puedes hacer lo mismo que {0} en Costeo Yelke. Se termina solo el {1}.").format(
            _nombre(de_usuario), formatdate(hasta))
    else:
        asunto = _("{0} te prestará los permisos de {1} del {2} al {3}").format(
            quien, _nombre(de_usuario), formatdate(desde), formatdate(hasta))
        mensaje = _("Empiezan solos el {0}.").format(formatdate(desde))
    _avisar([a_usuario], asunto, "Permiso Temporal Yelke", doc.name, mensaje=mensaje, ruta=_RUTA_INICIO,
            boton=_("Abrir Costeo Yelke"))
    return get_permisos_temporales()


@frappe.whitelist()
def terminar_permiso_temporal(name: str) -> dict:
    """Termina ahora un préstamo activo o cancela uno programado."""
    _exigir_direccion()
    doc = frappe.get_doc("Permiso Temporal Yelke", name)
    if doc.terminado:
        return get_permisos_temporales()
    empezo = getdate(doc.desde) <= getdate(nowdate())
    _retirar(doc)
    doc.db_set({"terminado": 1, "terminado_en": now_datetime(),
                "hasta": max(getdate(doc.desde), getdate(add_days(nowdate(), -1))) if empezo else doc.hasta})
    _avisar([doc.a_usuario],
            _("{0} terminó el préstamo: ya no tienes los permisos de {1}").format(_nombre(frappe.session.user), _nombre(doc.de_usuario))
            if empezo else _("{0} canceló el préstamo de los permisos de {1}").format(_nombre(frappe.session.user), _nombre(doc.de_usuario)),
            "Permiso Temporal Yelke", doc.name, ruta=_RUTA_INICIO, correo=False)
    return get_permisos_temporales()


def _aplicar(doc):
    """Agrega al que recibe los roles prestables del otro que todavía no tiene."""
    if doc.aplicado or doc.terminado:
        return
    faltan = sorted(set(roles_prestables(doc.de_usuario)) - _roles(doc.a_usuario))
    for rol in faltan:
        frappe.get_doc({"doctype": "Has Role", "name": frappe.generate_hash(length=10), "parent": doc.a_usuario,
                        "parenttype": "User", "parentfield": "roles", "role": rol}).db_insert()
    doc.db_set({"roles_agregados": json.dumps(faltan, ensure_ascii=False), "aplicado": 1})
    frappe.clear_cache(user=doc.a_usuario)


def _retirar(doc):
    """Quita solo los roles que agregó este préstamo y que ningún otro préstamo vigente
    le sigue dando."""
    if not doc.aplicado:
        return
    otros = set()
    for o in _activos_de(doc.a_usuario, excepto=doc.name):
        otros |= set(json.loads(o.roles_agregados or "[]"))
    for rol in set(json.loads(doc.roles_agregados or "[]")) - otros:
        frappe.db.delete("Has Role", {"parent": doc.a_usuario, "parenttype": "User", "role": rol})
    frappe.clear_cache(user=doc.a_usuario)


def procesar_permisos_temporales():
    """Cada hora (scheduler): aplica los que empiezan y retira los vencidos."""
    hoy = nowdate()
    for d in frappe.get_all("Permiso Temporal Yelke", filters={
            "aplicado": 0, "terminado": 0, "desde": ["<=", hoy], "hasta": [">=", hoy]}, pluck="name"):
        doc = frappe.get_doc("Permiso Temporal Yelke", d)
        _aplicar(doc)
        frappe.set_user(doc.otorgado_por or "Administrator")
        _avisar([doc.a_usuario], _("Desde hoy tienes los permisos de {0}, hasta el {1}").format(
            _nombre(doc.de_usuario), formatdate(doc.hasta)), "Permiso Temporal Yelke", doc.name, ruta=_RUTA_INICIO)
    for d in frappe.get_all("Permiso Temporal Yelke", filters={
            "aplicado": 1, "terminado": 0, "hasta": ["<", hoy]}, pluck="name"):
        doc = frappe.get_doc("Permiso Temporal Yelke", d)
        _retirar(doc)
        doc.db_set({"terminado": 1, "terminado_en": now_datetime()})
    frappe.set_user("Administrator")
    frappe.db.commit()


def conservar_roles_prestados(doc, method=None):
    """validate de User (corre después de User.validate_roles): el Perfil de Rol
    reescribe los roles en cada guardado y borraría los prestados; aquí se vuelven a
    poner mientras el préstamo siga vigente."""
    if doc.is_new() or not frappe.db.table_exists("Permiso Temporal Yelke"):
        return
    tiene = {r.role for r in doc.get("roles") or []}
    for p in _activos_de(doc.name):
        for rol in json.loads(p.roles_agregados or "[]"):
            if rol not in tiene:
                doc.append("roles", {"role": rol})
                tiene.add(rol)
