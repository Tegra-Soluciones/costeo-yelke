import frappe


def execute():
    """Rol "CEO" -- puede generar réplicas de Orden de Venta con precio acordado
    aunque la vigencia ("Fijar Precio") ya haya vencido; para cualquier otro usuario
    esa acción se bloquea (no se elimina el precio acordado, solo se impide generar
    réplicas nuevas hasta que alguien con este rol lo autorice)."""
    if frappe.db.exists("Role", "CEO"):
        return
    role = frappe.new_doc("Role")
    role.role_name = "CEO"
    role.desk_access = 1
    role.flags.ignore_permissions = True
    role.insert()
    frappe.db.commit()
