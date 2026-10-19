"""Que quien aprueba, revisa o captura pueda ABRIR los documentos de los que le
avisan (docs/plan-panel-direccion.md).

El panel de Dirección lee por sus propios métodos, pero el documento original (el
enlace de la campana, del correo o "Abrir el documento completo") lo carga el
SPA con los permisos normales de ERPNext. Sin estos permisos, Ana (Enviar
Documentos) veía "No se pudo cargar el costeo" al abrir el aviso de su costeo
aprobado, y el CEO no podía abrir ningún documento desde el panel.

Antes, el permiso de Costeo de producción vivía solo en su base (Custom DocPerm
hecho a mano el 2026-10-08); aquí queda en la app para cualquier sitio.

Solo AGREGA lo que falta: nunca quita ni baja un permiso que ya exista.
frappe.permissions.add_permission copia primero los permisos estándar a Custom
DocPerm, así que tampoco se pierde lo que el doctype ya traía.
"""
import frappe
from frappe.permissions import add_permission, update_permission_property

from costeo_yelke.roles import DOCUMENTOS_CON_APROBACION, ROL_APROBADOR, ROL_DIRECTOR, ROL_REVISOR

ROL_CAPTURA = "Enviar Documentos Yelke"

# Quien decide necesita ver el documento completo y lo que muestra (cliente,
# proveedor, artículos), no editarlo.
LECTURA = ("read", "print", "report", "export")
MAESTROS = ("Customer", "Supplier", "Item", "Company", "Talla")

# Quien arma el costeo lo captura y lo envía; validar lo decide el candado de
# aprobación (api/aprobaciones.candado_aprobacion), no este permiso.
CAPTURA_COSTEO = ("read", "write", "create", "submit", "cancel", "amend", "print", "email", "export", "report", "share")


def _asegurar(doctype, rol, ptypes):
    if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Role", rol):
        return
    if not frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": rol, "permlevel": 0, "if_owner": 0}):
        add_permission(doctype, rol, 0)
    fila = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": rol, "permlevel": 0, "if_owner": 0},
                               list(ptypes), as_dict=True) or {}
    for ptype in ptypes:
        if not fila.get(ptype):
            update_permission_property(doctype, rol, 0, ptype, 1, validate=False)


def execute():
    for rol in (ROL_DIRECTOR, ROL_APROBADOR, ROL_REVISOR):
        for doctype in (*DOCUMENTOS_CON_APROBACION, *MAESTROS):
            _asegurar(doctype, rol, LECTURA if doctype in DOCUMENTOS_CON_APROBACION else ("read",))
    _asegurar("Costeo", ROL_CAPTURA, CAPTURA_COSTEO)
    _asegurar("Talla", ROL_CAPTURA, ("read",))  # la pantalla del costeo lee el catálogo de tallas
    for doctype in (*DOCUMENTOS_CON_APROBACION, *MAESTROS):
        frappe.clear_cache(doctype=doctype)
