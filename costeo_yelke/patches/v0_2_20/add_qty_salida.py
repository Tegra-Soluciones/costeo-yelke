import frappe


def execute():
    """La salida de una etapa se captura ahora en UNIDADES producidas, no en % de
    participación.

    El % nunca describió el resultado: existe solo para repartir un costo COMPARTIDO
    (la operación se paga y consume materia prima una sola vez aunque produzca varios
    resultados). Pero lo que el usuario conoce es cuántas piezas salen -- un corte da
    1 manga izquierda, 1 manga derecha y 1 frente -- así que ese es el dato que se
    pide, y el % pasa a derivarse de él (qty_salida / suma de la etapa) en
    _explode_stage_nodes.

    Backfill: las salidas existentes se capturaron repartiendo el 100% a partes
    iguales, así que 1 unidad por salida reproduce EXACTAMENTE el mismo reparto (3
    salidas de 1 -> 33.33% cada una, igual que hoy). No se toca pct_participacion: el
    valor guardado sigue sirviendo de respaldo para cualquier fila que quedara sin
    cantidad.
    """
    if not frappe.db.has_column("Etapa Costeo Salida", "qty_salida"):
        return

    frappe.db.sql(
        """
        UPDATE `tabEtapa Costeo Salida`
           SET qty_salida = 1
         WHERE qty_salida IS NULL OR qty_salida = 0
        """
    )
    frappe.clear_cache(doctype="Etapa Costeo Salida")
