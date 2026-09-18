"""Utilidades compartidas chicas, sin un hogar obvio en un api/*.py de un solo
doctype/proceso."""

import frappe


def nombres_comerciales(doctype, names, real_field):
    """Batch: name real -> "Nombre Comercial" si lo tiene capturado, si no el
    nombre real de siempre (real_field). Cliente y Proveedor tienen ambos un
    campo opcional 'nombre_comercial' (ver patches v0_2_25 y v0_2_31) -- este es
    el mismo fallback que ya resuelve solo cualquier LinkInput ya resuelto en el
    SPA (frontend utils/frappe.js LINK_DISPLAY_FIELD); aquí es para las listas y
    detalles que traen el nombre ya resuelto desde el backend, sin pasar por
    LinkInput."""
    names = {n for n in names if n}
    if not names:
        return {}
    filas = frappe.get_all(
        doctype, filters={"name": ["in", list(names)]},
        fields=["name", real_field, "nombre_comercial"],
    )
    return {f.name: (f.nombre_comercial or f.get(real_field)) for f in filas}


def resolver_terminos(tc_name):
    """Texto de un "Términos y Condiciones" (tc_name) listo para guardar en el
    campo `terms` del documento. ERPNext solo hace este fetch del lado del
    cliente (ver erpnext/public/js/utils.js -> get_terms, disparado por el
    onchange de tc_name en el formulario de escritorio) -- las API de este app
    arman los documentos del lado del servidor sin pasar por ese JS, así que si
    no se resuelve aquí, `terms` se queda vacío para siempre aunque tc_name sí
    esté capturado, y el formato de impresión (que solo pinta `doc.terms`)
    nunca muestra nada."""
    if not tc_name:
        return None
    return frappe.db.get_value("Terms and Conditions", tc_name, "terms")
