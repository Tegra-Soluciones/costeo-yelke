import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """El conversor $/kg -> $/m de telas del Costeo cambió: en vez de derivar el
    precio por metro con gramaje+ancho (fórmula textil que no es como se calcula
    en la práctica), ahora se captura directamente cuántos metros salen de 1 kilo
    de esa tela (dato que ya se conoce por experiencia) -- reemplaza los dos campos
    del patch v0_2_4 por uno solo."""
    for fieldname in ("gramaje", "ancho", "costeo_tela_column_break", "costeo_tela_section"):
        frappe.db.delete("Custom Field", {"dt": "Item", "fieldname": fieldname})

    create_custom_fields(
        {
            "Item": [
                {
                    "fieldname": "metros_por_kilo",
                    "label": "Metros por kilo",
                    "fieldtype": "Float",
                    "precision": "2",
                    "insert_after": "weight_uom",
                    "description": "Cuántos metros salen de 1 kilo de esta tela -- usado para convertir su precio de $/kg a $/m en el Costeo.",
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )

    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
