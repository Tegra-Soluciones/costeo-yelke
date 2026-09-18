import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Doble validación (Enviar -> Revisor -> Aprobador, ver costeo_yelke/roles.py)
    para la Orden de Compra -- de materia prima o subcontratada, ambas son el
    mismo doctype 'Purchase Order' en esta app. Guarda quién dio la verificación
    intermedia antes de que validar_documento permita la aprobación final (ver
    costeo_api.py marcar_revisado_documento / validar_documento).

    Los demás documentos del flujo (Cotización, Orden de Venta, Factura, Plan de
    Producción, Recibos, Orden de Subcontratación...) NO llevan estos campos --
    siguen con la validación normal, sin gating por rol."""
    create_custom_fields(
        {
            "Purchase Order": [
                {
                    "fieldname": "revisado_yelke",
                    "label": "Revisado (doble validación)",
                    "fieldtype": "Check",
                    "insert_after": "status",
                    "read_only": 1,
                    "allow_on_submit": 1,
                    "description": "Se marca al dar 'Revisar' -- requisito previo para poder Validar esta Orden de Compra.",
                },
                {
                    "fieldname": "revisado_por_yelke",
                    "label": "Revisado por",
                    "fieldtype": "Data",
                    "insert_after": "revisado_yelke",
                    "read_only": 1,
                    "allow_on_submit": 1,
                },
                {
                    "fieldname": "revisado_en_yelke",
                    "label": "Revisado el",
                    "fieldtype": "Datetime",
                    "insert_after": "revisado_por_yelke",
                    "read_only": 1,
                    "allow_on_submit": 1,
                },
            ]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Purchase Order")
