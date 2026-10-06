"""Esconde de los formatos impresos los campos internos de la OC de maquila.

`prendas` y `producto_terminado` (patch v0_2_41) existen para que el formato
"Orden de Maquila" pueda reagrupar los renglones por servicio y cobrar por
prenda. No son información para el proveedor: impresos con un formato estándar
salían como dos columnas más del volcado, y `prendas` hasta con un renglón de
total ("Prendas (Total): 0") que no significa nada.

Se marcan print_hide. Los formatos de la app los leen igual -- print_hide solo
afecta al render automático de los formatos estándar, no a `it.get("prendas")`
dentro de una plantilla Jinja.
"""

import frappe


def execute():
    for fieldname in ("prendas", "producto_terminado"):
        name = frappe.db.get_value(
            "Custom Field", {"dt": "Purchase Order Item", "fieldname": fieldname}, "name"
        )
        if not name:
            continue
        frappe.db.set_value("Custom Field", name, "print_hide", 1, update_modified=False)
        print(f"Purchase Order Item.{fieldname}: print_hide = 1")
    frappe.clear_cache(doctype="Purchase Order Item")
