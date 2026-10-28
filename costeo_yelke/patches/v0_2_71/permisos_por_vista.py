"""Permisos de ERPNext por vista (docs/plan-accesos-ejecucion.md, fase 5).

Cada rol de vista recibe sobre los documentos de ERPNext lo que dice
roles.permisos_por_rol(): ver -> leer, imprimir, correo, reporte, exportar; editar ->
además escribir, crear y validar lo validable de su vista. Director y Supervisor,
todo. Así quien trabaja en el Escritorio (alta de proveedores, clientes...) puede
hacer lo suyo y nada más, y las llamadas estándar de la app (frappe.client) ya no
dependen de System Manager.

Solo AGREGA permisos (nunca quita los de System Manager ni los de los roles de
ERPNext). Antes de tocar un doctype copia sus permisos estándar a Custom DocPerm:
con uno solo personalizado, Frappe ignora los estándar. Idempotente.
"""
import frappe
from frappe.permissions import setup_custom_perms

from costeo_yelke.roles import permisos_por_rol

TODOS = ("read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "report", "export")


def execute():
    tocados = set()
    for (doctype, rol), ptypes in permisos_por_rol().items():
        if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Role", rol):
            continue
        meta = frappe.get_meta(doctype)
        if meta.istable:
            continue
        if not meta.is_submittable:
            ptypes = ptypes - {"submit", "cancel", "amend"}
        setup_custom_perms(doctype)
        nombre = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": rol, "permlevel": 0, "if_owner": 0})
        if nombre:
            actuales = frappe.db.get_value("Custom DocPerm", nombre, list(TODOS), as_dict=True)
            faltan = {p: 1 for p in ptypes if not actuales.get(p)}
            if faltan:
                frappe.db.set_value("Custom DocPerm", nombre, faltan, update_modified=False)
        else:
            perm = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType",
                                   "parentfield": "permissions", "role": rol, "permlevel": 0,
                                   **{p: 1 for p in ptypes}})
            perm.insert(ignore_permissions=True)
        tocados.add(doctype)
    for doctype in tocados:
        frappe.clear_cache(doctype=doctype)
    print(f"Permisos por vista: {len(tocados)} tipos de documento.")
