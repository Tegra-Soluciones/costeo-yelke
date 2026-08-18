import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Reparto de UN material entre VARIAS etapas, con cantidad explícita por etapa.

    Hasta ahora un material se atribuía a UNA sola etapa (campo escalar 'etapa' de
    Costeo Producto Detalle) y su consumo completo (internal_qty) se iba entero a esa
    etapa. Eso no alcanza cuando el mismo insumo lo consumen dos operaciones
    distintas: ej. 4 unidades de CINTA-REFLEJANTE donde 2 las coloca la etapa de la
    manga y 2 la del frente. 'tabla_materiales_etapa' permite declarar esas
    porciones explícitamente (material_id + stage_id + qty).

    Vive en COSTEO como tabla HERMANA de costeo_producto_detalle -- NO como campo
    Table dentro de Costeo Producto Detalle: Frappe no cascada el guardado de una
    tabla anidada dentro de OTRA tabla hija (Document.update_children solo hace
    db_update() de cada fila, nunca inserta las suyas propias), así que una
    tabla-dentro-de-tabla ahí se perdería silenciosamente al guardar. Mismo motivo
    y misma forma que 'tabla_salidas_etapa' (ver patch v0_2_18).

    Queda VACÍA para todos los costeos existentes -- crear_boms_spa solo la usa si
    el material tiene filas propias ahí; si no, cae exactamente al comportamiento de
    siempre (campo 'etapa' + internal_qty completo). Así ningún costeo ya capturado
    cambia de resultado sin que alguien lo reconfigure a propósito.

    El backfill de 'material_id' es lo único que sí toca datos existentes: es un id
    interno nuevo (mismo rol que stage_id en Etapas Costeo) y hace falta para poder
    referenciar una fila de material sin depender de su posición ni de su item_code.
    """
    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "tabla_materiales_etapa",
                "label": "Reparto de materiales por etapa",
                "fieldtype": "Table",
                "options": "Costeo Material Etapa",
                "insert_after": "tabla_salidas_etapa",
                # Igual que tabla_etapas_costeo / tabla_salidas_etapa: "Preparar
                # Manufactura" se configura DESPUÉS de que el Costeo ya está
                # validado (docstatus=1), así que este campo necesita poder
                # seguir editándose post-submit -- sin esto, repartir un material
                # en un costeo ya avanzado a Cotización/Orden de Venta truena con
                # UpdateAfterSubmitError.
                "allow_on_submit": 1,
                "description": (
                    "Cuánto de cada materia prima consume cada etapa, cuando el mismo "
                    "insumo se reparte entre varias operaciones (ej. 4 de cinta reflejante: "
                    "2 en la manga, 2 en el frente). Un material sin filas aquí se atribuye "
                    "completo a la etapa de su campo 'etapa', como siempre."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )

    # Backfill de material_id en las filas ya existentes -- se genera uno estable por
    # fila (frappe.generate_hash da el mismo formato corto que usa el SPA para
    # stage_id/salida_id). update_modified=False: es un id interno, no un cambio de
    # negocio, no debe mover el 'modified' del Costeo padre ni invalidar nada.
    if frappe.db.has_column("Costeo Producto Detalle", "material_id"):
        rows = frappe.get_all(
            "Costeo Producto Detalle",
            filters={"material_id": ["in", ["", None]]},
            pluck="name",
        )
        for name in rows:
            frappe.db.set_value(
                "Costeo Producto Detalle", name, "material_id",
                frappe.generate_hash(length=12), update_modified=False,
            )

    frappe.clear_cache(doctype="Costeo")
    frappe.clear_cache(doctype="Costeo Producto Detalle")
