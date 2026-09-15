import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Agrega 'Nombre Comercial' a Proveedor (Supplier), justo debajo de 'Supplier
    Name' -- es el nombre con el que Yelke conoce al taller/proveedor en el día a
    día (ej. "Taller Alejandro"), a diferencia de la razón social/nombre con el
    que quedó registrado (ej. "ALEJANDRO TORRES AGUILERA S.A. DE C.V."). Vacío por
    default: si no se captura, todo sigue mostrando el nombre de siempre (ver
    costeo_yelke.api.item_api / frontend LinkInput.vue -- caen al nombre normal si
    nombre_comercial viene vacío)."""
    create_custom_fields(
        {
            "Supplier": [{
                "fieldname": "nombre_comercial",
                "label": "Nombre Comercial",
                "fieldtype": "Data",
                "insert_after": "supplier_name",
                "description": (
                    "Nombre con el que se conoce a este proveedor/taller en el día a día "
                    "(ej. \"Taller Alejandro\"), si es distinto de su razón social. Cuando "
                    "se captura, es el que se muestra en todos los selectores de proveedor "
                    "de la app de Costeo -- si se deja vacío, se sigue mostrando el nombre "
                    "de siempre."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Supplier")
