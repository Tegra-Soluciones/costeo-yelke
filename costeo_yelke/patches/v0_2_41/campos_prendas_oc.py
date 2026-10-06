import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Campos que necesita el formato de impresión de la orden de maquila.

    Con el modelo por pieza, una OC de subcontratación trae un renglón por pieza
    (frente, espalda, puños...) para poder avanzar cada una por separado. El
    proveedor, en cambio, cobra POR PRENDA y debe seguir viendo lo de siempre --
    "servicio de corte, 7,494 prendas x $5". El formato agrupa los renglones por
    servicio, pero para eso necesita dos datos que no se pueden deducir del renglón:

    - `prendas`: cuántas prendas representa. NO se puede sumar la cantidad de los
      renglones, porque los puños van 2 por prenda y darían 14,988 en vez de 7,494.
    - `producto_terminado`: para no mezclar la camisola base con su variante de
      talla, que tienen precios y cantidades distintas.

    Los llena _create_subcontracting_pos_from_stages al crear la OC. Quedan vacíos
    en cualquier otra OC (compra de materia prima), y el formato cae a mostrar el
    renglón tal cual.
    """
    create_custom_fields(
        {
            "Purchase Order Item": [
                {
                    "fieldname": "prendas",
                    "label": "Prendas",
                    "fieldtype": "Float",
                    "insert_after": "fg_item_qty",
                    "read_only": 1,
                    "no_copy": 1,
                    "precision": "3",
                    "description": (
                        "Prendas terminadas que representa este renglón. Lo usa el "
                        "formato impreso para mostrar el cobro por prenda; no se suma "
                        "entre renglones."
                    ),
                },
                {
                    "fieldname": "producto_terminado",
                    "label": "Producto Terminado",
                    "fieldtype": "Data",
                    "insert_after": "prendas",
                    "read_only": 1,
                    "no_copy": 1,
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Purchase Order Item")
