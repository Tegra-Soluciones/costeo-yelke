"""Estado de aprobación en cada documento de roles.DOCUMENTOS_CON_APROBACION
(docs/plan-panel-direccion.md §3).

Los campos van OCULTOS: el estado lo pinta el SPA, y en el escritorio de ERPNext cada
cambio queda en la línea de tiempo (Comment). Son `no_copy` para que una copia o una
corrección (amend) nazca en Borrador, sin arrastrar la aprobación de la original.

Backfill: lo ya validado (o cancelado) queda Aprobado y lo que está en borrador queda
Borrador -- así ningún borrador viejo aparece de golpe en la bandeja de Dirección; solo
entra lo que alguien envíe a aprobación de aquí en adelante.

Costeo es doctype propio, pero va por el mismo camino que los de ERPNext para que los
cinco se definan en un solo lugar.

Los precios acordados (Item Price) no tienen docstatus: solo se les agrega la marca de
"regresado por Dirección" y su motivo (api/aprobaciones.regresar_precios).
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from costeo_yelke.roles import DOCUMENTOS_CON_APROBACION

ESTADOS = "Borrador\nPendiente\nRevisado\nDevuelto\nAprobado"


def _campos():
    base = {"read_only": 1, "hidden": 1, "no_copy": 1, "allow_on_submit": 1, "print_hide": 1}
    return [
        {**base, "fieldname": "estado_aprobacion_yelke", "label": "Estado de aprobación",
         "fieldtype": "Select", "options": ESTADOS, "default": "Borrador",
         "insert_after": "amended_from", "search_index": 1},
        {**base, "fieldname": "enviado_aprobacion_por", "label": "Enviado a aprobación por",
         "fieldtype": "Link", "options": "User", "insert_after": "estado_aprobacion_yelke"},
        {**base, "fieldname": "enviado_aprobacion_en", "label": "Enviado a aprobación el",
         "fieldtype": "Datetime", "insert_after": "enviado_aprobacion_por"},
        {**base, "fieldname": "aprobado_por_yelke", "label": "Aprobado por",
         "fieldtype": "Link", "options": "User", "insert_after": "enviado_aprobacion_en"},
        {**base, "fieldname": "aprobado_en_yelke", "label": "Aprobado el",
         "fieldtype": "Datetime", "insert_after": "aprobado_por_yelke"},
        {**base, "fieldname": "ultimo_motivo_devolucion", "label": "Último motivo de devolución",
         "fieldtype": "Small Text", "insert_after": "aprobado_en_yelke"},
        {**base, "fieldname": "cambio_tras_envio", "label": "Cambió después de enviarse",
         "fieldtype": "Check", "insert_after": "ultimo_motivo_devolucion"},
    ]


def execute():
    campos = {dt: _campos() for dt in DOCUMENTOS_CON_APROBACION}
    oculto = {"read_only": 1, "hidden": 1, "no_copy": 1}
    campos["Item Price"] = [
        {**oculto, "fieldname": "precio_devuelto_yelke", "label": "Regresado por Dirección",
         "fieldtype": "Check", "insert_after": "precio_acordado_validado"},
        {**oculto, "fieldname": "precio_motivo_devolucion", "label": "Motivo de la devolución",
         "fieldtype": "Small Text", "insert_after": "precio_devuelto_yelke"},
    ]
    create_custom_fields(campos, ignore_validate=True, update=True)

    # La revisión de la OC (v0_2_30) se copiaba al duplicar: una OC nueva nacía ya
    # "revisada" y se saltaba el paso del revisor.
    for campo in ("revisado_yelke", "revisado_por_yelke", "revisado_en_yelke"):
        nombre = frappe.db.get_value("Custom Field", {"dt": "Purchase Order", "fieldname": campo})
        if nombre:
            frappe.db.set_value("Custom Field", nombre, "no_copy", 1)

    for dt in DOCUMENTOS_CON_APROBACION:
        frappe.clear_cache(doctype=dt)
        tabla = f"tab{dt}"
        frappe.db.sql(f"""update `{tabla}` set estado_aprobacion_yelke='Aprobado'
                          where docstatus in (1, 2)""")
        frappe.db.sql(f"""update `{tabla}` set estado_aprobacion_yelke='Borrador'
                          where docstatus = 0 and ifnull(estado_aprobacion_yelke, '') = ''""")
