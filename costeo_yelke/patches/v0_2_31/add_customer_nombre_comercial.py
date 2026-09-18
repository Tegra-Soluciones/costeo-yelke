import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Agrega 'Nombre Comercial' a Cliente (Customer), justo debajo de 'Customer
    Name' -- la contraparte de la que ya tiene Proveedor (ver patch v0_2_25): el
    nombre con el que Yelke conoce al cliente en el día a día, a diferencia de la
    razón social/nombre con el que quedó registrado. Vacío por default: si no se
    captura, todo sigue mostrando el nombre de siempre (ver frontend
    utils/frappe.js LINK_DISPLAY_FIELD -- cae al nombre normal si nombre_comercial
    viene vacío)."""
    create_custom_fields(
        {
            "Customer": [{
                "fieldname": "nombre_comercial",
                "label": "Nombre Comercial",
                "fieldtype": "Data",
                "insert_after": "customer_name",
                "description": (
                    "Nombre con el que se conoce a este cliente en el día a día, si es "
                    "distinto de su razón social. Cuando se captura, es el que se muestra "
                    "en toda la app de Costeo -- si se deja vacío, se sigue mostrando el "
                    "nombre de siempre."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Customer")
