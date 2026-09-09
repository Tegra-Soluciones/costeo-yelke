import frappe

from costeo_yelke.roles import ROLES_YELKE


def execute():
    """Crea un rol por cada proceso del flujo del Costeo + los roles transversales de
    aprobación (ver costeo_yelke/roles.py). Idempotente: solo crea los que faltan y
    completa la descripción de los que ya existieran sin ella.

    Todos con desk_access=1 (los usuarios de la app son System Users y entran también
    al escritorio de ERPNext). NO se asignan permisos de doctype aquí -- eso se hace
    por partes conforme se definan; por ahora los roles solo existen para poder
    asignarlos a las personas.
    """
    for role_name, descripcion in ROLES_YELKE.items():
        if frappe.db.exists("Role", role_name):
            if not frappe.db.get_value("Role", role_name, "description"):
                frappe.db.set_value("Role", role_name, "description", descripcion, update_modified=False)
            continue
        role = frappe.new_doc("Role")
        role.role_name = role_name
        role.description = descripcion
        role.desk_access = 1
        role.flags.ignore_permissions = True
        role.insert()

    frappe.db.commit()
