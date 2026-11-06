"""UDM «Kit» (pedido de Yelke, 2026-11-06) y «Par», por si no existe: unidades base y
enteras, como el resto del catálogo de v0_2_76."""
import frappe


def execute():
    for nombre in ("Kit", "Par"):
        if frappe.db.exists("UOM", nombre):
            # Ya existe: solo se asegura que esté activa (no se cambia si acepta decimales,
            # podría haber documentos que ya la usan con fracciones).
            frappe.db.set_value("UOM", nombre, "enabled", 1, update_modified=False)
            continue
        frappe.get_doc({"doctype": "UOM", "uom_name": nombre, "enabled": 1,
                        "must_be_whole_number": 1}).insert(ignore_permissions=True)
