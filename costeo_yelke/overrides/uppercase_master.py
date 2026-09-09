"""Homologa a MAYÚSCULAS los campos de nombre / identificador de los datos maestros.

Se aplica al guardar (before_insert + before_validate) sobre los doctypes de
``UPPER_FIELDS``. Solo toca campos de NOMBRE o CÓDIGO -- nunca correos, teléfonos,
sitios web, IDs externos ni descripciones largas (esos se dejan tal cual por
correción técnica y legibilidad).

`before_insert` corre ANTES de `set_new_name`, así que en los doctypes cuyo nombre
sale de un campo (Item = item_code, grupos = *_name) el folio también queda en
mayúsculas. `before_validate` cubre las ediciones posteriores.
"""

import frappe

UPPER_FIELDS = {
    "Customer":       ("customer_name", "tax_id"),
    "Supplier":       ("supplier_name", "tax_id"),
    "Item":           ("item_code", "item_name", "customer_code", "default_manufacturer_part_no"),
    "Address":        ("address_title", "address_line1", "address_line2", "city", "county", "state"),
    "Contact":        ("first_name", "middle_name", "last_name", "full_name",
                       "designation", "company_name", "department"),
    "Lead":           ("first_name", "middle_name", "last_name", "lead_name", "company_name",
                       "job_title", "title", "city", "state"),
    "Warehouse":      ("warehouse_name",),
    "Brand":          ("brand",),
    "Item Group":     ("item_group_name",),
    "Customer Group": ("customer_group_name",),
    "Supplier Group": ("supplier_group_name",),
    "Territory":      ("territory_name",),
}


def upper(doc, method=None):
    fields = UPPER_FIELDS.get(doc.doctype)
    if not fields:
        return
    for fieldname in fields:
        value = doc.get(fieldname)
        if isinstance(value, str) and value:
            upper_value = value.upper()
            if upper_value != value:
                doc.set(fieldname, upper_value)
