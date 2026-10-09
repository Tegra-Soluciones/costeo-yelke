"""Campo Firma en el usuario (se creó a mano en producción; desde 2026-10-09 vive en
la app). Lo usan las firmas de los formatos de impresión (api/impresion.py)."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"User": [{
        "fieldname": "firma", "label": "Firma", "fieldtype": "Signature", "insert_after": "user_image",
        "description": "Firma de la persona, trazada en pantalla. Se recopila una vez y se reutiliza en los documentos que la requieran.",
    }]}, update=True)
