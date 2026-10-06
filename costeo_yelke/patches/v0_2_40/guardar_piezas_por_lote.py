import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt


def execute():
    """Guarda las PIEZAS que le tocan a cada lote de entrega.

    Al dividir la Solicitud de Material "por piezas" la persona captura cuántas
    prendas terminadas lleva cada lote, pero ese dato se usaba solo para derivar la
    materia prima y después se tiraba (mr_dividir_en_lotes_por_piezas lo convertía a
    materiales y llamaba a mr_dividir_en_lotes, que solo recibe materiales).

    Consecuencia real: del lado de producción, get_lotes_produccion deriva la
    cantidad del lote de las Subcontracting Order que ya existan -- y en el primer
    paso todavía no hay ninguna, así que el lote aparecía "sin cantidad definida" y
    la pantalla le volvía a pedir a la persona un número que ya había capturado
    (sugiriéndole uno adivinado desde el stock).

    Esta tabla conserva ese dato. Queda VACÍA para los costeos existentes: sin
    filas, el comportamiento es exactamente el de antes (se deriva de las SCO), así
    que nada cambia para un lote ya en marcha.
    """
    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "tabla_lotes_costeo",
                "label": "Lotes de entrega",
                "fieldtype": "Table",
                "options": "Costeo Lote",
                "insert_after": "tabla_subensamblajes_costeo",
                "allow_on_submit": 1,
                "description": (
                    "Cuántas prendas terminadas de cada producto lleva cada lote de "
                    "entrega -- se llena solo al dividir la Solicitud de Material por "
                    "piezas, y es lo que la pantalla de Producción usa como cantidad "
                    "del lote sin volver a preguntarla."
                ),
            }],
        },
        ignore_validate=True,
        update=True,
    )

    # Backfill de lotes YA divididos: la cantidad de prendas se puede reconstruir
    # de las Subcontracting Order que ya existan (es de donde la leía la pantalla
    # hasta ahora), así que un lote en marcha no pierde su cifra.
    from costeo_yelke.api.costeo_api import _productos_terminados_de_costeo

    recuperados = 0
    for costeo in frappe.get_all("Costeo", pluck="name"):
        pts = _productos_terminados_de_costeo(costeo)
        if not pts:
            continue
        pos = frappe.get_all("Purchase Order",
                             filters={"costeo": costeo, "is_subcontracted": 1},
                             pluck="name") if frappe.db.has_column("Purchase Order", "costeo") else []
        if not pos:
            continue
        filas = {}
        for sco in frappe.get_all("Subcontracting Order",
                                  filters={"purchase_order": ["in", pos], "docstatus": ["<", 2]},
                                  fields=["name", "lote_ref"]):
            if not sco.lote_ref:
                continue
            for it in frappe.get_all("Subcontracting Order Item",
                                     filters={"parent": sco.name},
                                     fields=["item_code", "qty"]):
                # Solo el producto terminado representa "prendas del lote"; los
                # semiterminados pueden acumular varias entregas.
                if it.item_code in pts:
                    clave = (sco.lote_ref, it.item_code)
                    filas[clave] = filas.get(clave, 0) + flt(it.qty)
        if not filas:
            continue
        doc = frappe.get_doc("Costeo", costeo)
        if doc.get("tabla_lotes_costeo"):
            continue
        for (lote_ref, producto), piezas in sorted(filas.items()):
            doc.append("tabla_lotes_costeo", {
                "lote_ref": lote_ref, "producto_terminado": producto, "piezas": piezas,
            })
        doc.flags.ignore_permissions = True
        doc.flags.ignore_validate_update_after_submit = True
        doc.save()
        recuperados += 1

    frappe.clear_cache(doctype="Costeo")
    if recuperados:
        print(f"piezas por lote reconstruidas en {recuperados} costeo(s)")
