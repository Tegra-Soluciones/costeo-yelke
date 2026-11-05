"""Vista «Levantamiento» (roles.VISTAS): sus dos roles y sus permisos de ERPNext.

Antes era una pestaña del Panel de Dirección; ahora es su propia pantalla para darla
también a quien no es Dirección. Dirección la sigue teniendo sola (roles.accesos).
Idempotente: crea los roles que falten y vuelve a correr los permisos por vista
(v0_2_71, que solo agrega).
"""
import frappe

from costeo_yelke.roles import VISTAS


def execute():
    v = VISTAS["levantamiento"]
    for rol in (v["rol"], v["rol_ver"]):
        if not frappe.db.exists("Role", rol):
            frappe.get_doc({"doctype": "Role", "role_name": rol, "desk_access": 1}).insert(ignore_permissions=True)
    from costeo_yelke.patches.v0_2_71 import permisos_por_vista

    permisos_por_vista.execute()
    frappe.clear_cache()
