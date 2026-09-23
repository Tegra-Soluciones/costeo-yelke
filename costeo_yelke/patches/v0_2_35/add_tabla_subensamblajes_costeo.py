import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Declaración de sub-ensamblajes por producto (ver costeo_api.py,
    _multiplicador_por_operacion / parada_registrar_entrega): cuando un mismo
    lote se entrega en varias "olas" físicas (puños, mangas, cuellos...) que
    NO se registran como Artículo, cada una toma un subconjunto distinto de
    las operaciones del flujo (ver Etapas Costeo.stage_id). Sin declarar esto
    de antemano, la OC raíz de una operación intermedia visitada por varias
    olas se queda sin saldo a medio camino -- probado en vivo que ampliarla
    in-place es imposible con ERPNext (Purchase Order.can_update_items()
    bloquea cualquier cambio de cantidad en cuanto tiene una sola
    Subcontracting Order creada contra ella). La salida es dimensionar la OC
    raíz de una vez para el número real de olas -- ver
    _build_stage_subcontracting_rows.

    Vive como tabla HERMANA de costeo_producto (no anidada en ninguna otra
    tabla hija, mismo motivo que tabla_materiales_etapa/tabla_salidas_etapa:
    Frappe no cascada el guardado de una tabla dentro de otra tabla hija).

    Queda VACÍA para todos los costeos existentes -- un producto sin filas
    aquí sigue exactamente como hoy (multiplicador 1 en toda operación)."""
    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "tabla_subensamblajes_costeo",
                "label": "Sub-ensamblajes declarados",
                "fieldtype": "Table",
                "options": "Costeo Sub Ensamblaje",
                "insert_after": "tabla_materiales_etapa",
                "allow_on_submit": 1,
                "description": (
                    "Sub-ensamblajes físicos (puños, mangas...) que un mismo lote puede "
                    "entregar en varias tandas -- por cuáles operaciones pasa cada uno, para "
                    "dimensionar bien la OC de maquila de cada taller. No crea ningún Artículo."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Costeo")
