"""Catálogo de unidades de medida en español y sin claves SAT.

- Solo unidades BASE: la conversión (un rollo trae 50 m, un mazo 1,728 piezas) se captura
  en cada artículo, así que no deben existir UDM como «Rollo de 10 mts» o «25 Kilos».
- Nombre simple, sin clave SAT: Yelke no timbra desde ERPNext. Las que ya tenían
  registros se renombran (rename_doc actualiza todos los documentos que las citan).
- Las de fábrica de ERPNext que sirven se traducen; las demás (Abampere, Acre…) se
  borran con sus conversiones genéricas, solo si nada las usa.
"""
import frappe
from frappe.model.rename_doc import rename_doc

RENOMBRAR = {
    "H87 - Pieza": "Pieza", "MTR - Metro": "Metro", "KGM - Kilogramo": "Kilogramo",
    "E48 - Unidad de servicio": "Unidad de servicio", "MILLAR": "Millar",
    "Pair": "Par", "Box": "Caja", "Centimeter": "Centímetro", "Millimeter": "Milímetro",
    "Yard": "Yarda", "Inch": "Pulgada", "Gram": "Gramo", "Tonne": "Tonelada",
    "Litre": "Litro", "Millilitre": "Mililitro", "Gallon Liquid (US)": "Galón",
    "Square Meter": "Metro cuadrado",
}
NUEVAS = ["Docena", "Juego", "Bolsa", "Carrete"]
CONSERVAR = {"Paquete", "Cono", "Rollo", "Mazo", "Gruesa", "Hora", "Día", "Semana"} | set(RENOMBRAR.values()) | set(NUEVAS)


def _campos_uom():
    return frappe.db.sql("""
        select parent, fieldname from tabDocField where fieldtype = 'Link' and options = 'UOM'
        union select dt, fieldname from `tabCustom Field` where fieldtype = 'Link' and options = 'UOM'""")


def _en_uso(uom, campos):
    for dt, f in campos:
        if dt == "UOM Conversion Factor" or not frappe.db.table_exists(dt) or not frappe.db.has_column(dt, f):
            continue
        if frappe.db.sql(f"select 1 from `tab{dt}` where `{f}` = %s limit 1", (uom,)):
            return f"{dt}.{f}"
    return None


def _renombrar(viejo, nuevo):
    if not frappe.db.exists("UOM", viejo):
        return
    if viejo != nuevo and viejo.lower() == nuevo.lower():
        # Solo cambian mayúsculas: MariaDB las ve iguales, se pasa por un nombre temporal.
        rename_doc("UOM", viejo, f"{nuevo} (tmp)", force=True, show_alert=False)
        viejo = f"{nuevo} (tmp)"
    existe = frappe.db.exists("UOM", nuevo)
    rename_doc("UOM", viejo, nuevo, force=True, merge=bool(existe), show_alert=False)
    frappe.db.set_value("UOM", nuevo, "uom_name", nuevo, update_modified=False)


# Precios que se quedaron con una UDM que ya no existe y que decía su cantidad: pasan a
# la base del paquete (Rollo) solo si el artículo tiene esa conversión dada de alta.
HUERFANAS = {"Rollo de 100 mts": "Rollo", "Rollo 25 metros": "Rollo"}


def _precios_huerfanos():
    for p in frappe.db.sql("""select name, item_code, uom from `tabItem Price`
            where ifnull(uom, '') != '' and uom not in (select name from tabUOM)""", as_dict=True):
        destino = HUERFANAS.get(p.uom)
        if destino and frappe.db.exists("UOM Conversion Detail", {"parent": p.item_code, "uom": destino}):
            frappe.db.set_value("Item Price", p.name, "uom", destino, update_modified=False)
        else:
            print(f"Precio {p.name} ({p.item_code}) se queda con la UDM «{p.uom}»: revisar a mano.")


def execute():
    _precios_huerfanos()
    for viejo, nuevo in RENOMBRAR.items():
        _renombrar(viejo, nuevo)
    for nombre in NUEVAS:
        if not frappe.db.exists("UOM", nombre):
            frappe.get_doc({"doctype": "UOM", "uom_name": nombre, "enabled": 1}).insert(ignore_permissions=True)
    if frappe.db.get_single_value("Stock Settings", "stock_uom") not in CONSERVAR:
        frappe.db.set_single_value("Stock Settings", "stock_uom", "Pieza")

    campos = _campos_uom()
    for uom in frappe.get_all("UOM", pluck="name"):
        if uom in CONSERVAR:
            continue
        uso = _en_uso(uom, campos)
        if uso:
            print(f"UDM «{uom}» se conserva: está en uso ({uso}).")
            continue
        frappe.db.delete("UOM Conversion Factor", {"from_uom": uom})
        frappe.db.delete("UOM Conversion Factor", {"to_uom": uom})
        frappe.delete_doc("UOM", uom, ignore_permissions=True, force=True)
    frappe.clear_cache()
