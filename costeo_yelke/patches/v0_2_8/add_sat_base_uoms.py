import frappe

# "MTR - Metro" y "H87 - Pieza" y "E48 - Unidad de servicio" -- claves SAT que la app
# usa como default en varios campos (Etapas Costeo.lote_uom, materias primas tipo Tela,
# servicios de etapa, etc.). Hasta ahora solo se creaban al correr manualmente
# costeo_yelke/scripts/import_sample_items.py -- en un sitio nuevo (bench new-site +
# install-app, sin correr ese script) esos Link truenan al guardar. Se separan aquí en
# un patch para que cualquier instalación nueva las tenga sin depender de acordarse de
# correr el script de datos de ejemplo.
UOMS = ["MTR - Metro", "H87 - Pieza", "E48 - Unidad de servicio"]


def execute():
    for uom_name in UOMS:
        if frappe.db.exists("UOM", uom_name):
            continue
        uom = frappe.new_doc("UOM")
        uom.uom_name = uom_name
        uom.flags.ignore_permissions = True
        uom.insert()
    frappe.db.commit()
