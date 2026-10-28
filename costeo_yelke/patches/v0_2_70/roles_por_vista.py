"""Roles por vista (docs/plan-accesos-ejecucion.md, fase 2), sin que nadie pierda acceso.

1. Crea los roles de roles.VISTAS que falten: el de editar de cada vista nueva y el
   "Ver ..." de todas (las 9 de Producción ya existían).
2. Role Profile "Acceso completo Yelke" con todos los roles de editar, para asignarlo
   después a quien deba ver todo.
3. A todos los usuarios activos de la app les da los roles de EDITAR de todas las
   vistas, como ya tenían de hecho (hasta hoy nada se restringía fuera de Producción):
   - si el usuario tiene Role Profile, el rol va AL PERFIL y se re-guardan sus
     usuarios (el perfil reemplaza los roles del usuario en cada guardado, ver
     memoria "El Perfil de Rol manda");
   - si no, va directo al usuario.
   Recortar lo que no le toca a cada quien se hace después, en la pantalla de Accesos.
Idempotente.
"""
import frappe

from costeo_yelke.roles import VISTAS

PERFIL = "Acceso completo Yelke"


def execute():
    editar = [v["rol"] for v in VISTAS.values()]
    for rol in editar + [v["rol_ver"] for v in VISTAS.values()]:
        if not frappe.db.exists("Role", rol):
            frappe.get_doc({"doctype": "Role", "role_name": rol, "desk_access": 1}).insert(ignore_permissions=True)

    _perfil(PERFIL, editar, crear=True)

    usuarios = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User",
                                               "name": ["not in", ["Administrator", "Guest"]]},
                              fields=["name", "role_profile_name"])
    perfiles = {u.role_profile_name for u in usuarios if u.role_profile_name}
    for perfil in perfiles:
        _perfil(perfil, editar)
    for u in usuarios:
        doc = frappe.get_doc("User", u.name)
        if u.role_profile_name:
            # Re-guardar copia los roles del perfil al usuario.
            doc.flags.ignore_permissions = True
            doc.save(ignore_permissions=True)
            continue
        actuales = {r.role for r in doc.roles}
        faltan = [r for r in editar if r not in actuales]
        if faltan:
            for r in faltan:
                doc.append("roles", {"role": r})
            doc.save(ignore_permissions=True)
    frappe.clear_cache()


def _perfil(nombre, roles, crear=False):
    if not frappe.db.exists("Role Profile", nombre):
        if not crear:
            return
        frappe.get_doc({"doctype": "Role Profile", "role_profile": nombre,
                        "roles": [{"role": r} for r in roles]}).insert(ignore_permissions=True)
        return
    perfil = frappe.get_doc("Role Profile", nombre)
    actuales = {r.role for r in perfil.roles}
    faltan = [r for r in roles if r not in actuales]
    if faltan:
        for r in faltan:
            perfil.append("roles", {"role": r})
        perfil.save(ignore_permissions=True)
