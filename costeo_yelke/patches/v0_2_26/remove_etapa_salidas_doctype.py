import frappe


def execute():
    """Termina la limpieza del patch v0_2_24: aquel patch ya había borrado el
    registro del DocType 'Etapa Costeo Salida' en la BD, pero como los archivos
    fuente (json/py) del doctype todavía existían en el app, el propio
    `bench migrate` lo volvía a crear en el mismo ciclo (sync doctypes lee de
    disco) -- por eso seguía apareciendo después de desplegar v0_2_24. Ahora que
    los archivos ya se borraron del app (este commit), esta vez sí se queda
    borrado."""
    if frappe.db.table_exists("Etapa Costeo Salida"):
        n = frappe.db.count("Etapa Costeo Salida")
        if n:
            frappe.logger().warning(
                f"[costeo_yelke v0_2_26] 'Etapa Costeo Salida' tiene {n} fila(s) -- "
                "se deja sin tocar, revisar a mano."
            )
            return

    if frappe.db.exists("DocType", "Etapa Costeo Salida"):
        frappe.delete_doc("DocType", "Etapa Costeo Salida", ignore_permissions=True, force=True)
        frappe.clear_cache(doctype="Etapa Costeo Salida")
