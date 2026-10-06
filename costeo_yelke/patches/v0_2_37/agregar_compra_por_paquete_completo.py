import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Marca qué artículos se compran en paquetes completos (Mazo, Gruesa, Pieza...
    -- no se puede pedir una fracción a un proveedor, a diferencia de metros de tela
    o kilos de hilo) -- usado por costeo_api._es_compra_por_paquete para redondear
    la cantidad de compra hacia arriba (ver mr_crear_oc / guardar_documento_compra).

    Se intentó primero marcar esto en la UDM (`UOM.must_be_whole_number`), pero ese
    campo SÍ lo valida ERPNext nativamente (`validate_uom_is_integer`) en cualquier
    documento que use esa UDM -- incluida la Solicitud de Material, que
    deliberadamente guarda cantidades fraccionarias por lote (mr_dividir_en_lotes_
    por_piezas) y solo se redondea hasta la Orden de Compra. Marcarlo ahí rompía el
    guardado de la Solicitud. Por eso el campo vive en el ARTÍCULO, no en la UDM --
    no dispara ninguna validación nativa de ERPNext, solo la nuestra.

    También sube `Item.over_delivery_receipt_allowance` (nativo de ERPNext, ver
    erpnext/controllers/status_updater.py get_allowance_for) al 100% para estos
    artículos -- al redondear hacia arriba, la OC de un lote pide MÁS que la línea
    de la Solicitud de Material que la originó (a propósito, ver mr_crear_oc), y sin
    este margen ERPNext bloquea el VALIDAR de esa OC con "This document is over
    limit". El redondeo nunca pasa de UN paquete completo de margen -- 100% es
    generoso de sobra para los tamaños de lote reales de este negocio (siempre
    bastantes unidades), y solo afecta a estos artículos, no al resto del sistema."""
    create_custom_fields(
        {
            "Item": [{
                "fieldname": "compra_por_paquete_completo",
                "label": "Se compra en paquetes completos",
                "fieldtype": "Check",
                "insert_after": "stock_uom",
                "description": (
                    "No se puede pedir una fracción a un proveedor (ej. Mazo, Gruesa, "
                    "Pieza) -- la cantidad de compra se redondea hacia arriba, "
                    "compensando el sobrante entre los lotes de la misma solicitud."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Item")

    for item_code in ("BOTON-DE-PASTA-18-L", "BOTON DE PASTA"):
        if frappe.db.exists("Item", item_code):
            frappe.db.set_value("Item", item_code, "compra_por_paquete_completo", 1)
            frappe.db.set_value("Item", item_code, "over_delivery_receipt_allowance", 100)

    frappe.db.commit()
