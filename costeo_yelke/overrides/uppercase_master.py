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


# Doctypes cuyo nombre del documento sale del campo (o de él + abreviatura): homologar
# los existentes implicaría renombrar taxonomía base de ERPNext -- referenciada por
# asientos de inventario, defaults de compañía, reportes. Los NUEVOS sí nacen en
# mayúsculas por el hook; los existentes se dejan (salvo Item/Brand, que son seguros).
_SKIP_EXISTENTES = {"Item Group", "Customer Group", "Supplier Group", "Territory", "Warehouse"}


def homologar_existentes():
    """Corrida única: pasa a MAYÚSCULAS los maestros ya cargados. Idempotente."""
    for doctype, fields in UPPER_FIELDS.items():
        if doctype in _SKIP_EXISTENTES:
            continue

        autoname = frappe.get_meta(doctype).autoname
        name_from_field = (
            autoname[len("field:"):]
            if isinstance(autoname, str) and autoname.startswith("field:")
            else None
        )

        for row in frappe.get_all(doctype, fields=["name"] + list(fields)):
            updates = {}
            for f in fields:
                v = row.get(f)
                if isinstance(v, str) and v and v != v.upper():
                    updates[f] = v.upper()
            if not updates:
                continue

            if name_from_field and name_from_field in updates and updates[name_from_field] != row["name"]:
                nuevo = updates.pop(name_from_field)
                # MariaDB compara sin distinguir caja (collation _ci): db.exists(nuevo)
                # da True aunque el único match sea ESTE mismo doc. Solo es colisión real
                # si el nombre difiere en algo más que mayúsculas/minúsculas.
                if nuevo.casefold() != row["name"].casefold() and frappe.db.exists(doctype, nuevo):
                    frappe.log_error(
                        title="homologar mayúsculas: destino ya existe",
                        message=f"{doctype}: {row['name']} -> {nuevo}",
                    )
                    continue
                try:
                    frappe.rename_doc(doctype, row["name"], nuevo, force=True)
                except Exception:
                    frappe.log_error(title=f"homologar mayúsculas: rename falló ({doctype})")
                    continue
                if updates:
                    frappe.db.set_value(doctype, nuevo, updates, update_modified=False)
            else:
                frappe.db.set_value(doctype, row["name"], updates, update_modified=False)

    frappe.db.commit()
