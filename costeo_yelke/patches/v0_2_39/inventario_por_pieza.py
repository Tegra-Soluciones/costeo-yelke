import frappe


def execute():
    """Rediseño a INVENTARIO POR PIEZA (ver _resolve_piece_states en costeo.py).

    La ruta de producción no pertenece a la etapa sino a cada pieza física, y cada
    paso que transforma una pieza produce un artículo semiterminado propio. Este
    patch solo ajusta los DATOS que ese modelo necesita; la lógica ya vive en el
    código y es inerte para cualquier costeo que no declare piezas.

    1. `Costeo Sub Ensamblaje.multiplicador` cambia de significado: antes era
       "cuántas olas de entrega toca esta pieza" (un número de conveniencia que
       servía para inflar la OC raíz, y que resultó ser la raíz del inventario
       inflado y del costo mal repartido). Ahora es CUÁNTAS LLEVA UNA PRENDA -- un
       dato físico real (2 puños, 1 frente). Todas las filas existentes valen 1.0,
       que es correcto en los dos significados, así que no hay que migrar valores:
       solo se corrigen etiqueta y descripción para que nadie lo capture mal.

    2. `Costeo Material Etapa.subensamblaje` (nuevo, opcional): permite decir "de
       los 1.45 m de gabardina, 0.40 son del frente". Sin capturar nada, la materia
       prima de una etapa se reparte sola y parejo entre las piezas que produce
       (ver _materiales_por_pieza), y la suma sigue dando exactamente la cantidad
       original -- por eso queda vacío para todos los costeos existentes.
    """
    campo = frappe.db.get_value(
        "DocField",
        {"parent": "Costeo Sub Ensamblaje", "fieldname": "multiplicador"},
        "name",
    )
    if campo:
        frappe.db.set_value("DocField", campo, {
            "label": "Cantidad por prenda",
            "description": (
                "Cuántas piezas de éstas lleva UNA prenda (2 puños, 1 frente). "
                "Casi siempre 1. No es un número de entregas: es la cantidad física, "
                "y con ella se dimensionan el BOM y el desarme del kit."
            ),
        }, update_modified=False)

    if not frappe.db.exists("Custom Field", "Costeo Material Etapa-subensamblaje"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Costeo Material Etapa",
            "module": "Costeo Yelke",
            "fieldname": "subensamblaje",
            "label": "Pieza",
            "fieldtype": "Data",
            "insert_after": "stage_id",
            "description": (
                "Opcional: a qué pieza (Costeo Sub Ensamblaje.nombre) se le carga esta "
                "cantidad. Vacío = se reparte parejo entre las piezas de la etapa."
            ),
        }).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Costeo Sub Ensamblaje")
    frappe.clear_cache(doctype="Costeo Material Etapa")
