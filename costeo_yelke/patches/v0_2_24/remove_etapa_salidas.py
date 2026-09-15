import frappe


def execute():
    """Retira el mecanismo de "salidas múltiples por etapa" (patches v0_2_18 /
    v0_2_20): una etapa ya no puede declarar varios resultados nombrados con
    reparto de costo/material por porcentaje. Nunca tuvo UI de captura -- la tabla
    quedó vacía en todos los costeos desde que se creó -- y no representaba bien
    el caso real que debía resolver: un taller que reparte piezas de una misma
    prenda a varios caminos en paralelo (una va a bordado, otra a colocación de
    cinta, otra se une directo) no es "un resultado dividido en fracciones", es
    "el mismo resultado, entero, alimentando más de un camino siguiente" -- eso
    ahora lo resuelve directamente 'recibe_de' (varias etapas pueden seleccionar
    la MISMA etapa origen, cada una recibiendo la pieza completa; ver
    _resolve_production_operations en costeo.py, "sin reducción transitiva").

    Por seguridad, solo borra 'Etapa Costeo Salida' si de verdad está vacía en
    ESTE sitio -- si alguien llegó a capturar algo a mano (nunca hubo botón para
    hacerlo, pero por si acaso), se deja la tabla y el campo intactos en vez de
    perder datos, y se avisa en el log para revisarlo a mano."""
    if frappe.db.table_exists("Etapa Costeo Salida"):
        n = frappe.db.count("Etapa Costeo Salida")
        if n:
            frappe.logger().warning(
                f"[costeo_yelke v0_2_24] 'Etapa Costeo Salida' tiene {n} fila(s) -- "
                "se deja la tabla/campo sin tocar, revisar a mano antes de limpiar."
            )
            return

    for doctype, fieldname in (
        ("Costeo", "tabla_salidas_etapa"),
        ("BOM", "salida_id"),
        ("Subcontracting BOM", "salida_id"),
    ):
        name = f"{doctype}-{fieldname}"
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

    if frappe.db.exists("DocType", "Etapa Costeo Salida"):
        frappe.delete_doc("DocType", "Etapa Costeo Salida", ignore_permissions=True, force=True)

    frappe.clear_cache(doctype="Costeo")
    frappe.clear_cache(doctype="BOM")
    frappe.clear_cache(doctype="Subcontracting BOM")
