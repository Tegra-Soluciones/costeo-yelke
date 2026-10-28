"""Pantalla de Accesos (docs/plan-accesos-ejecucion.md, fase 8): qué vistas tiene cada
puesto (Role Profile) y cada usuario, en "editar" o "ver".

Los roles de vista se asignan por PERFIL de puesto: al guardar un perfil se reescriben
sus roles de vista y se re-guardan sus usuarios (Frappe copia los roles del perfil al
usuario en cada guardado, ver memoria "El Perfil de Rol manda"; los préstamos de
permisos se conservan solos, ver permisos_temporales.conservar_roles_prestados). Un
usuario sin perfil lleva sus roles de vista directo.

Solo quien tiene la vista Accesos (o Director / Supervisor) puede ver y cambiar esto.
"""
import json

import frappe
from frappe import _

from costeo_yelke.roles import PASE_LIBRE, VISTAS, puede

# Perfiles de fábrica de ERPNext que no son puestos de Yelke.
PERFILES_ERPNEXT = ("HR", "Purchase", "Sales", "Accounts", "Manufacturing", "Inventory")


def _exigir():
    if not puede("accesos", "editar"):
        frappe.throw(_("Necesitas la vista Accesos para administrar los accesos."), frappe.PermissionError)


def _niveles(roles):
    """{clave: "editar" | "ver"} a partir de una lista de roles (editar gana)."""
    roles = set(roles)
    out = {}
    for clave, v in VISTAS.items():
        if v["rol"] in roles:
            out[clave] = "editar"
        elif v["rol_ver"] in roles:
            out[clave] = "ver"
    return out


def _roles_de_vista():
    return {r for v in VISTAS.values() for r in (v["rol"], v["rol_ver"])}


def _roles_desde_niveles(niveles):
    out = []
    for clave, nivel in (niveles or {}).items():
        if clave in VISTAS and nivel in ("editar", "ver"):
            out.append(VISTAS[clave]["rol"] if nivel == "editar" else VISTAS[clave]["rol_ver"])
    return out


def _usuarios_activos():
    return frappe.get_all("User", filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
                          fields=["name", "full_name", "role_profile_name"], order_by="full_name asc")


@frappe.whitelist()
def get_matriz() -> dict:
    _exigir()
    vistas = [{"clave": c, "etiqueta": v["etiqueta"], "grupo": v["grupo"], "descripcion": v["descripcion"]} for c, v in VISTAS.items()]
    perfiles = []
    for nombre in frappe.get_all("Role Profile", pluck="name", order_by="name asc"):
        if nombre in PERFILES_ERPNEXT:
            continue
        roles = frappe.get_all("Has Role", filters={"parent": nombre, "parenttype": "Role Profile"}, pluck="role")
        perfiles.append({"nombre": nombre, "niveles": _niveles(roles), "pase_libre": bool(set(roles) & set(PASE_LIBRE)),
                         "usuarios": frappe.db.count("User", {"role_profile_name": nombre, "enabled": 1})})
    usuarios = []
    for u in _usuarios_activos():
        roles = frappe.get_all("Has Role", filters={"parent": u.name, "parenttype": "User"}, pluck="role")
        prestamos = frappe.get_all("Permiso Temporal Yelke", filters={"a_usuario": u.name, "aplicado": 1, "terminado": 0},
                                   fields=["de_usuario", "hasta"]) if frappe.db.exists("DocType", "Permiso Temporal Yelke") else []
        usuarios.append({"usuario": u.name, "nombre": u.full_name or u.name, "perfil": u.role_profile_name or "",
                         "niveles": _niveles(roles), "pase_libre": bool(set(roles) & set(PASE_LIBRE)),
                         "prestamos": [{"de": p.de_usuario, "hasta": str(p.hasta)} for p in prestamos]})
    return {"vistas": vistas, "perfiles": perfiles, "usuarios": usuarios}


@frappe.whitelist()
def guardar_perfil(perfil: str, niveles) -> dict:
    """Reescribe los roles de vista del perfil y los aplica a sus usuarios."""
    _exigir()
    niveles = json.loads(niveles) if isinstance(niveles, str) else niveles
    doc = frappe.get_doc("Role Profile", perfil)
    doc.unlock()  # un trabajo pendiente de Frappe sobre el perfil no debe frenar el cambio
    de_vista = _roles_de_vista()
    antes = _niveles([r.role for r in doc.roles])
    doc.roles = [r for r in doc.roles if r.role not in de_vista]
    for rol in _roles_desde_niveles(niveles):
        doc.append("roles", {"role": rol})
    doc.save(ignore_permissions=True)
    # Frappe pasa los roles a los usuarios del perfil en un trabajo en segundo plano y
    # deja el perfil bloqueado mientras tanto: se hace aquí mismo (para que se vea al
    # recargar) y se suelta el bloqueo; el trabajo de Frappe ya no encuentra qué cambiar.
    doc.update_all_users()
    doc.unlock()
    usuarios = frappe.get_all("User", filters={"role_profile_name": perfil}, pluck="name")
    for u in usuarios:
        frappe.clear_cache(user=u)
    despues = _niveles([r.role for r in doc.roles])
    cambios = [f"{VISTAS[c]['etiqueta']}: {antes.get(c, '—')} → {despues.get(c, '—')}"
               for c in VISTAS if antes.get(c) != despues.get(c)]
    if cambios:
        doc.add_comment("Info", _("Accesos cambiados por {0}: {1}").format(frappe.session.user, "; ".join(cambios)))
    return {"usuarios": len(usuarios), "cambios": len(cambios)}


@frappe.whitelist()
def crear_perfil(nombre: str) -> dict:
    _exigir()
    nombre = (nombre or "").strip()
    if not nombre:
        frappe.throw(_("Escribe el nombre del puesto."))
    if frappe.db.exists("Role Profile", nombre):
        frappe.throw(_("Ya existe el perfil {0}.").format(nombre))
    doc = frappe.get_doc({"doctype": "Role Profile", "role_profile": nombre}).insert(ignore_permissions=True)
    doc.unlock()  # perfil nuevo, sin usuarios: el trabajo de Frappe no tiene nada que hacer
    return {"nombre": nombre}


@frappe.whitelist()
def asignar_perfil(usuario: str, perfil: str = None) -> dict:
    """Pone (o quita) el perfil del usuario. Con perfil, sus roles pasan a ser los del
    perfil -- así lo hace Frappe; los préstamos vigentes se conservan."""
    _exigir()
    doc = frappe.get_doc("User", usuario)
    doc.role_profile_name = perfil or None
    doc.save(ignore_permissions=True)
    frappe.clear_cache(user=usuario)
    return {"usuario": usuario, "perfil": perfil or ""}


@frappe.whitelist()
def guardar_usuario(usuario: str, niveles) -> dict:
    """Vistas de un usuario SIN perfil (con perfil se cambian en el perfil)."""
    _exigir()
    niveles = json.loads(niveles) if isinstance(niveles, str) else niveles
    doc = frappe.get_doc("User", usuario)
    if doc.role_profile_name:
        frappe.throw(_("{0} tiene el perfil {1}: cambia sus accesos en el perfil.").format(usuario, doc.role_profile_name))
    de_vista = _roles_de_vista()
    doc.roles = [r for r in doc.roles if r.role not in de_vista]
    for rol in _roles_desde_niveles(niveles):
        doc.append("roles", {"role": rol})
    doc.save(ignore_permissions=True)
    frappe.clear_cache(user=usuario)
    return {"usuario": usuario}
