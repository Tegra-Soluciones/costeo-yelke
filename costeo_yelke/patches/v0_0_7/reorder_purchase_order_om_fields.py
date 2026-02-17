import frappe
from frappe.utils import cint


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


def get_field_idx(doctype: str, fieldname: str) -> int:
    idx = frappe.db.get_value("DocField", {"parent": doctype, "fieldname": fieldname}, "idx")
    if idx is None:
        idx = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "idx")
    return cint(idx)


def execute():
    """Keep OM total fields near their corresponding size tables in Purchase Order."""
    doctype = "Purchase Order"
    anchor_field = "om_ubicacion"

    anchor_idx = get_field_idx(doctype, anchor_field)
    if not anchor_idx:
        frappe.clear_cache(doctype=doctype)
        return

    current_idx = anchor_idx + 1
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
            {
                "insert_after": insert_after,
                "idx": current_idx,
            },
            update_modified=False,
        )

        insert_after = fieldname
        current_idx += 1

    frappe.clear_cache(doctype=doctype)
