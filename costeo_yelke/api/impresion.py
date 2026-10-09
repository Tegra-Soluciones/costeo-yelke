"""Datos para los formatos de impresión de Yelke (métodos jinja, ver hooks.py).

`firmas_documento(doc)` arma el bloque de firmas de cualquier documento con las
personas que de verdad intervinieron, con su firma de User.firma (patch v0_2_52):

  · Orden de compra (material o maquila): Elaboró · Revisó · Aprobó
    (revisó = revisado_por_yelke de la doble validación).
  · Todos los demás: Elaboró · Validó.

"Validó/Aprobó" es quien lo validó (submit): se toma del Version que registra el
cambio docstatus 0 -> 1, así sirve también para documentos ya validados.
"""
import frappe
from frappe.utils import formatdate


def _persona(usuario):
    if not usuario or usuario == "Guest":
        return {"nombre": "", "firma": None}
    campos = ["full_name", "firma"] if frappe.db.has_column("User", "firma") else ["full_name"]
    u = frappe.db.get_value("User", usuario, campos, as_dict=True) or {}
    nombre = u.get("full_name") or usuario
    if usuario == "Administrator":
        nombre = "Administrador"
    return {"nombre": nombre, "firma": u.get("firma") or None}


def _quien_valido(doc):
    if doc.docstatus != 1:
        return None, None
    v = frappe.get_all(
        "Version",
        filters={"ref_doctype": doc.doctype, "docname": doc.name, "data": ["like", '%"docstatus",0,1%']},
        fields=["owner", "creation"], order_by="creation asc", limit=1,
    )
    if v:
        return v[0].owner, v[0].creation
    return doc.modified_by, doc.modified


def _firma(titulo, usuario, fecha):
    p = _persona(usuario) if usuario else {"nombre": "", "firma": None}
    return {"titulo": titulo, "nombre": p["nombre"], "firma": p["firma"],
            "fecha": formatdate(fecha) if (usuario and fecha) else ""}


def firmas_documento(doc):
    valido, valido_en = _quien_valido(doc)
    if doc.doctype == "Purchase Order":
        return [
            _firma("Elaboró", doc.owner, doc.creation),
            _firma("Revisó", doc.get("revisado_por_yelke"), doc.get("revisado_en_yelke")),
            _firma("Aprobó", valido, valido_en),
        ]
    return [
        _firma("Elaboró", doc.owner, doc.creation),
        _firma("Validó", valido, valido_en),
    ]
