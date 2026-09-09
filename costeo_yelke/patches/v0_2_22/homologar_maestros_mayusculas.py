"""Pasa a MAYÚSCULAS los datos maestros YA cargados, en los campos de
``uppercase_master.UPPER_FIELDS``.

De aquí en adelante lo hace el hook (before_insert/before_validate); este patch es
la corrida única sobre lo existente.

**No toca** Item Group / Customer Group / Supplier Group / Territory / Warehouse:
en esos el nombre del documento sale del campo (o de él + la abreviatura), así que
homologarlos implicaría renombrar taxonomía base de ERPNext -- referenciada por
cientos de asientos de inventario, defaults de compañía, reportes y print formats.
Los NUEVOS sí nacen en mayúsculas por el hook; los existentes se dejan.
"""

import frappe

from costeo_yelke.overrides.uppercase_master import UPPER_FIELDS

SKIP = {"Item Group", "Customer Group", "Supplier Group", "Territory", "Warehouse"}


def execute():
    for doctype, fields in UPPER_FIELDS.items():
        if doctype in SKIP:
            continue

        autoname = frappe.get_meta(doctype).autoname
        name_from_field = autoname[len("field:"):] if isinstance(autoname, str) and autoname.startswith("field:") else None

        rows = frappe.get_all(doctype, fields=["name"] + list(fields))
        for row in rows:
            updates = {}
            for f in fields:
                v = row.get(f)
                if isinstance(v, str) and v and v != v.upper():
                    updates[f] = v.upper()
            if not updates:
                continue

            # El nombre del documento cambia (Item = item_code) -> rename_doc,
            # que reescribe todos los enlaces.
            if name_from_field and name_from_field in updates and updates[name_from_field] != row["name"]:
                nuevo = updates.pop(name_from_field)
                if frappe.db.exists(doctype, nuevo):
                    frappe.log_error(
                        title="homologar mayúsculas: destino ya existe",
                        message=f"{doctype}: {row['name']} -> {nuevo} (ya existe, se omite)",
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
