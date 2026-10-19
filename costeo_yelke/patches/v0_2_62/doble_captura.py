"""Doble captura de RFC y cuentas de banco (api/confirmaciones.py).

- Campos de confirmación junto al dato. Se validan y se vacían antes de guardar
  (no guardan nada), y no se copian al duplicar.
- El RFC (campo nativo tax_id; ya no hay app de facturación con su propio campo)
  se etiqueta "RFC" en Cliente y Proveedor.
- Sin captura rápida en Cliente y Proveedor: ese diálogo no trae la confirmación y
  el alta rebotaría; se abre el formulario completo.
"""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
    conf = {"fieldtype": "Data", "no_copy": 1, "print_hide": 1, "report_hide": 1, "in_list_view": 0,
            "allow_in_quick_entry": 0}
    rfc = [{**conf, "fieldname": "confirmar_rfc", "label": "Confirma el RFC", "insert_after": "tax_id",
            "description": "Escríbelo otra vez. El de arriba se oculta mientras lo capturas, para que no se copie."}]
    cuenta = lambda campo, despues, etq: {**conf, "fieldname": campo, "label": f"Confirma {etq}", "insert_after": despues,
                                         "depends_on": f"eval:doc.{despues}",
                                         "description": "Escríbelo otra vez: el de arriba se oculta mientras lo capturas."}
    create_custom_fields({
        "Customer": rfc,
        "Supplier": rfc,
        "Bank Account": [
            cuenta("confirmar_cuenta", "bank_account_no", "el número de cuenta"),
            cuenta("confirmar_clabe", "cuenta_clabe", "la CLABE"),
            cuenta("confirmar_tarjeta", "numero_tarjeta", "el número de tarjeta"),
        ],
    }, ignore_validate=True, update=True)
    for dt in ("Customer", "Supplier"):
        make_property_setter(dt, "tax_id", "label", "RFC", "Data", validate_fields_for_doctype=False)
        make_property_setter(dt, None, "quick_entry", "0", "Check", for_doctype=True, validate_fields_for_doctype=False)
