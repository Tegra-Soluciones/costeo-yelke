import frappe


OM_ORDERED_FIELDS = [
    "om_section_tallas_caballero",
    "om_tallas_caballero",
    "om_prendas_caballero_total",
    "om_section_tallas_dama",
    "om_tallas_dama",
    "om_prendas_dama_total",
    "om_section_procesos",
    "om_procesos",
    "om_section_observaciones",
    "om_observaciones",
    "om_section_tablas_flexibles",
    "om_tablas_html",
    "om_tablas_flexibles",
    "om_section_archivos",
    "om_archivos",
]


def execute():
    """Force a deterministic OM field chain in Purchase Order based on insert_after."""
    doctype = "Purchase Order"
    anchor_field = "om_ubicacion"

    meta = frappe.get_meta(doctype, cached=False)
    fieldnames = [df.fieldname for df in meta.fields]
    if anchor_field not in fieldnames:
        frappe.clear_cache(doctype=doctype)
        return

    insert_after = anchor_field

    for fieldname in OM_ORDERED_FIELDS:
        custom_field_name = frappe.db.get_value(
            "Custom Field", {"dt": doctype, "fieldname": fieldname}, "name"
        )
        if not custom_field_name:
            continue

        frappe.db.set_value(
            "Custom Field",
            custom_field_name,
            "insert_after",
            insert_after,
            update_modified=False,
        )

        insert_after = fieldname

    frappe.clear_cache(doctype=doctype)
