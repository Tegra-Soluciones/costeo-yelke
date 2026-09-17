"""Utilidades compartidas chicas, sin un hogar obvio en un api/*.py de un solo
doctype/proceso."""

import frappe


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
