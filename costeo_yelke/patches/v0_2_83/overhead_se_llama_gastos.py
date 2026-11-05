"""En pantalla, «overhead» ahora se llama «gastos» (pedido de Yelke). Solo cambia la
etiqueta del campo de la factura de venta creado en v0_2_3; el nombre interno
(overhead_journal_entry) se queda."""
import frappe


def execute():
    nombre = frappe.db.get_value("Custom Field", {"dt": "Sales Invoice", "fieldname": "overhead_journal_entry"})
    if nombre:
        frappe.db.set_value("Custom Field", nombre, "label", "Póliza de gastos", update_modified=False)
        frappe.clear_cache(doctype="Sales Invoice")
