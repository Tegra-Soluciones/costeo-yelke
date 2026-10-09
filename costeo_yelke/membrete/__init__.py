"""Membrete de Yelke (encabezado y pie de página de todos los PDF).

Se creó a mano en producción como Letter Head "Encabezado Yelke"; desde
2026-10-09 vive aquí: encabezado.html, pie.html y encabezado_yelke.json. En cada
migrate (install.after_migrate) se crea o actualiza el Letter Head con esto y
queda como predeterminado, igual que los formatos de impresión estándar de la
app. Para cambiarlo, editar estos archivos (no el Letter Head en el sitio).
El logo de respaldo vive en public/images/logo-yelke-black.png.
"""
import json
import os

import frappe

_DIR = os.path.dirname(__file__)


def _leer(nombre):
    with open(os.path.join(_DIR, nombre), encoding="utf-8") as f:
        return f.read()


def sincronizar_membrete():
    datos = json.loads(_leer("encabezado_yelke.json"))
    datos.update({"content": _leer("encabezado.html"), "footer": _leer("pie.html"),
                  "is_default": 1, "disabled": 0})
    nombre = datos["letter_head_name"]
    doc = frappe.get_doc("Letter Head", nombre) if frappe.db.exists("Letter Head", nombre) \
        else frappe.new_doc("Letter Head")
    cambios = any(doc.get(k) != v for k, v in datos.items())
    if not cambios:
        return
    doc.update(datos)
    doc.flags.ignore_permissions = True
    doc.save() if not doc.is_new() else doc.insert()
