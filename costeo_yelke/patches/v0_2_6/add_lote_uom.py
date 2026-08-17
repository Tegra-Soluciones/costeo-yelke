import frappe


def execute():
    """UOM "Lote" para servicios de maquila que el proveedor cobra por lote (ej. $19
    por 25 confecciones) en vez de por pieza -- usada como service_item_uom en el
    Subcontracting BOM y en la Orden de Compra cuando la etapa tiene lote_qty > 1,
    mismo criterio que add_tela_avio_uoms.py (v0_2_0) para Mazo/Gruesa."""
    if frappe.db.exists("UOM", "Lote"):
        return
    uom = frappe.new_doc("UOM")
    uom.uom_name = "Lote"
    uom.flags.ignore_permissions = True
    uom.insert()
    frappe.db.commit()
