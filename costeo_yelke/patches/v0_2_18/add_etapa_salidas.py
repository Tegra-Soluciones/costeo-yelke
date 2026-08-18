import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Soporte para etapas de manufactura con múltiples resultados nombrados (una
    operación de corte que produce varias piezas distintas, cada una con su propio
    BOM/Subcontracting BOM y su propio camino de etapas siguientes).

    'tabla_salidas_etapa' vive en COSTEO como tabla HERMANA de tabla_etapas_costeo
    (relacionada por 'stage_id', igual que costeo_producto_detalle se relaciona con
    su etapa) -- NO como campo Table dentro de Etapas Costeo: Frappe no cascada el
    guardado de una tabla anidada dentro de OTRA tabla hija (Document.update_children
    solo hace db_update() de cada fila, nunca inserta las suyas propias), así que una
    tabla-dentro-de-tabla ahí se perdería silenciosamente al guardar.

    Queda vacía para todos los costeos existentes -- el pipeline entero
    (_resolve_stage_graph, crear_boms_spa, crear_subcontracting_bom, generación de OC
    de subcontratación) sigue comportándose exactamente igual que antes mientras esa
    tabla esté vacía, así que no hace falta backfill de datos.

    Los campos 'costeo'/'salida_id' en BOM y Subcontracting BOM son trazabilidad
    hacia el Costeo/salida que generó cada documento (para poder encontrarlos y
    limpiarlos al resetear las etapas de un costeo, sin adivinar por nombre de
    ítem)."""
    if frappe.db.exists("Custom Field", "Etapas Costeo-salidas"):
        frappe.delete_doc("Custom Field", "Etapas Costeo-salidas", ignore_permissions=True)

    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "tabla_salidas_etapa",
                "label": "Salidas de etapas",
                "fieldtype": "Table",
                "options": "Etapa Costeo Salida",
                "insert_after": "tabla_etapas_costeo",
                # Igual que tabla_etapas_costeo (ver costeo.json): "Preparar
                # Manufactura" se configura DESPUÉS de que el Costeo ya está
                # validado (docstatus=1), así que este campo necesita poder
                # seguir editándose post-submit -- sin esto, agregar/editar
                # salidas en un costeo ya avanzado a Cotización/Orden de Venta
                # truena con UpdateAfterSubmitError.
                "allow_on_submit": 1,
                "description": (
                    "Salidas declaradas para etapas que producen MÁS DE UN resultado "
                    "nombrado (ej. una etapa de corte que produce manga izquierda, manga "
                    "derecha y frente por separado). Cada fila se liga a su etapa dueña "
                    "por 'stage_id'. Una etapa sin filas aquí sigue usando su campo "
                    "Subensamblaje normal, como siempre."
                ),
            }],
            "BOM": [
                {
                    "fieldname": "costeo",
                    "label": "Costeo",
                    "fieldtype": "Link",
                    "options": "Costeo",
                    "insert_after": "item",
                    "read_only": 1,
                    "no_copy": 1,
                    "print_hide": 1,
                },
                {
                    "fieldname": "salida_id",
                    "label": "ID de salida (Costeo)",
                    "fieldtype": "Data",
                    "insert_after": "costeo",
                    "hidden": 1,
                    "read_only": 1,
                    "no_copy": 1,
                },
            ],
            "Subcontracting BOM": [
                {
                    "fieldname": "costeo",
                    "label": "Costeo",
                    "fieldtype": "Link",
                    "options": "Costeo",
                    "insert_after": "finished_good",
                    "read_only": 1,
                    "no_copy": 1,
                    "print_hide": 1,
                },
                {
                    "fieldname": "salida_id",
                    "label": "ID de salida (Costeo)",
                    "fieldtype": "Data",
                    "insert_after": "costeo",
                    "hidden": 1,
                    "read_only": 1,
                    "no_copy": 1,
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Costeo")
    frappe.clear_cache(doctype="BOM")
    frappe.clear_cache(doctype="Subcontracting BOM")
