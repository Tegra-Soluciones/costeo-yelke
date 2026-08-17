import frappe

# "MTR - Metro" y "H87 - Pieza" ya existen (creadas por import_sample_items). Kilogramo
# usa la misma convención de clave SAT que esas dos (KGM); Mazo/Gruesa no tienen clave
# SAT -- son unidades de empaque de avíos (botones, broches...), no de facturación.
UOMS = ["KGM - Kilogramo", "Mazo", "Gruesa"]


def execute():
    """Crea las UOM que necesita el selector Tipo (Tela/Avío) del detalle de materia
    prima del Costeo -- sin esto, elegir Kilogramo/Mazo/Gruesa en esa UDM truena al
    guardar (Link inválido) porque esos registros no existen en el catálogo estándar
    de Frappe/ERPNext."""
    for uom_name in UOMS:
        if frappe.db.exists("UOM", uom_name):
            continue
        uom = frappe.new_doc("UOM")
        uom.uom_name = uom_name
        uom.flags.ignore_permissions = True
        uom.insert()
    frappe.db.commit()
