"""Motivo de cancelación de la Orden de Venta: se pide al cancelarla desde la app
(costeo_api.cancelar_orden_venta) y la OV cancelada se queda en el costeo como
historial, con este motivo a la vista, y le avisa a quien la hizo para que la rehaga
(rehacer_por)."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Sales Order": [
            {"fieldname": "motivo_cancelacion", "label": "Motivo de cancelación", "fieldtype": "Small Text",
             "insert_after": "po_no", "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "print_hide": 1},
            # Quién debe rehacerla: la última persona que la editó sin ser quien la canceló.
            # Le sale en su Inicio ("Te regresaron...") hasta que el costeo tenga una OV nueva.
            {"fieldname": "rehacer_por", "label": "Rehacer por", "fieldtype": "Link", "options": "User",
             "insert_after": "motivo_cancelacion", "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "print_hide": 1},
        ],
    })
