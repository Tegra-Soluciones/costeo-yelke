import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """"Se compra en paquetes completos" (ver Item.compra_por_paquete_completo,
    patch v0_2_37) resultó ser una propiedad del PAR (artículo, UDM), no solo del
    artículo -- la misma cinta puede comprarse suelta (Metro, fraccionable) o en
    rollo cerrado (Rollo, entero). Se agrega el mismo campo a cada fila de UOM
    Conversion Detail (una UDM alterna del artículo) -- ver costeo_api.
    _es_compra_por_paquete, ya rediseñado para consultar aquí en vez del artículo
    completo quando la UDM en juego no es la stock_uom.

    Backfill: los múltiplos que YA sabíamos que son paquete completo -- Gruesa y
    Pieza de los botones (antes cubiertos por el flag del artículo, que solo
    aplicaba a su stock_uom Mazo) y Rollo de la cinta reflejante gris (dato de
    prueba, pedido explícitamente por el usuario). También asegura
    Item.over_delivery_receipt_allowance en estos artículos (ver
    item_api._asegurar_allowance_si_paquete) -- sin esto, en cuanto la OC
    redondeada pide más que la línea de la Solicitud de Material que la originó,
    ERPNext bloquea el Validar con "This document is over limit" (encontrado en
    vivo con la cinta: redondeó 86.054 -> 87 Rollo, 94.6 Metro de más)."""
    create_custom_fields(
        {
            "UOM Conversion Detail": [{
                "fieldname": "compra_por_paquete_completo",
                "label": "Se compra en paquetes completos",
                "fieldtype": "Check",
                "insert_after": "conversion_factor",
                "description": (
                    "No se puede pedir una fracción a un proveedor en esta UDM -- la "
                    "cantidad de compra se redondea hacia arriba."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="UOM Conversion Detail")
    frappe.clear_cache(doctype="Item")

    backfill = {
        "BOTON-DE-PASTA-18-L": ["Gruesa", "H87 - Pieza"],
        "BOTON DE PASTA": ["Gruesa", "H87 - Pieza"],
        "CINTA REFLEJANTE GRIS": ["Rollo"],
    }
    for item_code, uoms in backfill.items():
        for uom in uoms:
            name = frappe.db.get_value(
                "UOM Conversion Detail",
                {"parent": item_code, "parenttype": "Item", "uom": uom},
                "name",
            )
            if name:
                frappe.db.set_value("UOM Conversion Detail", name, "compra_por_paquete_completo", 1)
        from costeo_yelke.api.item_api import ALLOWANCE_PAQUETE_COMPLETO
        actual = frappe.db.get_value("Item", item_code, "over_delivery_receipt_allowance")
        if frappe.utils.flt(actual) < ALLOWANCE_PAQUETE_COMPLETO:
            frappe.db.set_value("Item", item_code, "over_delivery_receipt_allowance", ALLOWANCE_PAQUETE_COMPLETO)

    frappe.db.commit()
