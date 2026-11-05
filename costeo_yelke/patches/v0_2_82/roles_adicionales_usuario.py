"""User.roles_adicionales_yelke: roles propios de una persona además de su Perfil de Rol
(permisos_temporales.conservar_roles_adicionales los vuelve a poner en cada guardado).
Idempotente."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"User": [{
        "fieldname": "roles_adicionales_yelke", "label": "Roles adicionales (además del perfil)",
        "fieldtype": "Small Text", "insert_after": "role_profile_name",
        "description": "Un rol por renglón. Se conservan aunque el Perfil de Rol reescriba los roles al guardar.",
    }]}, update=True)
