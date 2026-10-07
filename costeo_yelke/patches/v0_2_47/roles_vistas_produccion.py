import frappe

from costeo_yelke.roles import ROLES_VISTA_PRODUCCION


def execute():
    """Crea los 9 roles por VISTA de Producción (ver costeo_yelke/roles.py
    ROLES_VISTA_PRODUCCION) y, para no dejar a nadie fuera al desplegar, se los
    asigna a todos los usuarios habilitados de tipo System User.

    La idea es que nadie pierda acceso el día del despliegue: después, quien
    administra los usuarios QUITA los roles que no le toquen a cada quien. Si se
    repartieran solo a algunos, el resto se quedaría sin poder trabajar sin aviso.

    Idempotente: el rol que ya existe no se vuelve a crear, y el usuario que ya lo
    tiene no recibe un duplicado. Igual que v0_2_21 y v0_2_29, el DocType 'Role' de
    esta versión de Frappe no tiene campo 'description' -- las descripciones viven
    solo en roles.py como documentación.
    """
    for role_name in ROLES_VISTA_PRODUCCION:
        if frappe.db.exists("Role", role_name):
            continue
        role = frappe.new_doc("Role")
        role.role_name = role_name
        role.desk_access = 1
        role.flags.ignore_permissions = True
        role.insert()

    usuarios = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
        pluck="name",
    )
    for user in usuarios:
        doc = frappe.get_doc("User", user)
        actuales = {r.role for r in doc.get("roles") or []}
        faltantes = [r for r in ROLES_VISTA_PRODUCCION if r not in actuales]
        if not faltantes:
            continue
        for role_name in faltantes:
            doc.append("roles", {"role": role_name})
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)

    frappe.db.commit()
