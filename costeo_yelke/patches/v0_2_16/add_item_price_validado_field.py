import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campo 'precio_acordado_validado' en Item Price -- cualquier usuario interno puede
    capturar/editar un precio acordado (queda en borrador), pero solo un usuario con rol
    CEO puede validarlo (ver item_api.validar_precio_acordado). Mientras no esté
    validado, no cuenta como vigente para generar réplicas de Orden de Venta (ver
    costeo_api._precio_acordado_vigente) -- mismo criterio de "borrador -> validado" que
    ya se usa en el resto de la app para Cotización/Orden de Venta/Recibos, aplicado
    aquí como campo propio porque Item Price no es un doctype submittable nativo."""
    create_custom_fields(
        {
            "Item Price": [{
                "fieldname": "precio_acordado_validado",
                "label": "Precio acordado validado",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "costeo",
                "read_only": 1,
                "no_copy": 1,
                "print_hide": 1,
            }]
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Item Price")
