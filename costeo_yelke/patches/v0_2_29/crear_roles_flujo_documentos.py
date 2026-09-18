import frappe

from costeo_yelke.roles import ROLES_YELKE


def execute():
    """Agrega los 3 roles genéricos de flujo de documentos (ver costeo_yelke/roles.py
    ROLES_FLUJO_DOCUMENTOS) -- 'Enviar Documentos Yelke', 'Revisor de Documentos
    Yelke' y 'Aprobador de Documentos Yelke' -- pensados para servir tanto al
    esquema Simple (Enviar -> Aprobador) como al Doble (Enviar -> Revisor ->
    Aprobador) en cualquier documento del flujo, no solo el Costeo.

    Reutiliza la misma lógica idempotente del patch v0_2_21 (que ya corrió y no
    puede volver a dispararse solo) -- ROLES_YELKE ahora incluye estos 3 roles
    nuevos, así que re-ejecutarla aquí los crea sin tocar los que ya existían.

    Nota: el DocType 'Role' de esta versión de Frappe NO tiene campo 'description'
    (a diferencia de lo que asumía v0_2_21) -- las descripciones de ROLES_YELKE
    solo viven en costeo_yelke/roles.py como documentación, no se guardan en el rol."""
    for role_name in ROLES_YELKE:
        if frappe.db.exists("Role", role_name):
            continue
        role = frappe.new_doc("Role")
        role.role_name = role_name
        role.desk_access = 1
        role.flags.ignore_permissions = True
        role.insert()

    frappe.db.commit()
