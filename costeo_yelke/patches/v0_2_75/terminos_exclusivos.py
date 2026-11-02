"""Términos y condiciones exclusivos de un cliente o proveedor (overrides/terminos.py).

Agrega «Exclusivo del cliente» / «Exclusivo del proveedor» al término, deja «VENTA -
BOMBARDIER» como exclusivo de Bombardier y pone los términos generales como los de
cada compañía (estaban vacíos), para que un documento nuevo los traiga solos."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Terms and Conditions": [
        {"fieldname": "exclusivo_cliente", "label": "Exclusivo del cliente", "fieldtype": "Link",
         "options": "Customer", "insert_after": "buying", "depends_on": "eval:doc.selling",
         "description": "Solo se ofrece en los documentos de este cliente. Vacío = para todos."},
        {"fieldname": "exclusivo_proveedor", "label": "Exclusivo del proveedor", "fieldtype": "Link",
         "options": "Supplier", "insert_after": "exclusivo_cliente", "depends_on": "eval:doc.buying",
         "description": "Solo se ofrece en los documentos de este proveedor. Vacío = para todos."},
    ]}, update=True)
    frappe.clear_cache(doctype="Terms and Conditions")

    if frappe.db.exists("Terms and Conditions", "VENTA - BOMBARDIER") and \
            frappe.db.exists("Customer", "BOMBARDIER AEROSPACE MEXICO"):
        frappe.db.set_value("Terms and Conditions", "VENTA - BOMBARDIER",
                            "exclusivo_cliente", "BOMBARDIER AEROSPACE MEXICO", update_modified=False)

    for company in frappe.get_all("Company", pluck="name"):
        for campo, termino in (("default_selling_terms", "VENTA - CONDICIONES GENERALES"),
                               ("default_buying_terms", "COMPRA - CONDICIONES GENERALES")):
            if not frappe.db.get_value("Company", company, campo) and frappe.db.exists("Terms and Conditions", termino):
                frappe.db.set_value("Company", company, campo, termino, update_modified=False)
