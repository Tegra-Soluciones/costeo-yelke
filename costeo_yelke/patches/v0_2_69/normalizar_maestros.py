"""Reglas de captura sobre los datos que ya existen (overrides/captura.py), una sola vez.

Corrige lo que tiene una sola forma correcta -- espacios, mayúsculas, estado oficial,
CP, teléfono `442 467 8939`, correos en minúsculas, RFC sin guiones, folios -- sin
disparar validaciones (db_set), así que nunca truena por un dato viejo. Lo que no se
puede adivinar (un estado que es una ciudad, un CP de 4 dígitos, un RFC repetido, una
dirección o contacto sin dueño) NO se toca: queda en el archivo privado
"Revision datos maestros.csv" para corregirlo a mano.

Al final, el campo Estado de la dirección pasa a sugerir las 32 entidades
(Autocomplete: acepta otros países; la regla de captura exige una de las 32 en México).
Idempotente: una segunda corrida no cambia nada.
"""
import csv
import io

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from costeo_yelke.overrides import captura as C
from costeo_yelke.overrides.uppercase_master import UPPER_FIELDS

ARCHIVO = "Revision datos maestros.csv"


def execute():
    pendientes = []
    _textos()
    _partes(pendientes)
    _direcciones(pendientes)
    _contactos(pendientes)
    _folios()
    _rfc_repetidos(pendientes)
    _campo_estado()
    _reporte(pendientes)


def _set(doctype, name, cambios):
    if cambios:
        frappe.db.set_value(doctype, name, cambios, update_modified=False)


def _intenta(fn, valor, doctype, name, campo, pendientes):
    try:
        return fn(valor)
    except C.Invalido as e:
        pendientes.append((doctype, name, campo, valor, str(e)))
        return valor


def _ligas(parenttype, parent, doctypes):
    # Consulta directa: get_all sobre la tabla hija Dynamic Link no devuelve nada aquí.
    return frappe.db.sql(
        """select 1 from `tabDynamic Link` where parenttype = %s and parent = %s
           and link_doctype in %s and ifnull(link_name, '') != '' limit 1""", (parenttype, parent, doctypes))


def _textos():
    """Espacios dobles, al inicio y al final en los campos de nombre (las mayúsculas ya
    las aplicó el patch v0_2_22/23). El campo que da nombre al documento no se toca:
    cambiarlo implicaría renombrar."""
    for doctype, campos in UPPER_FIELDS.items():
        autoname = frappe.get_meta(doctype).autoname or ""
        del_nombre = autoname[6:] if autoname.startswith("field:") else None
        campos = [c for c in campos if c != del_nombre and frappe.db.has_column(doctype, c)]
        if not campos:
            continue
        for r in frappe.get_all(doctype, fields=["name", *campos]):
            _set(doctype, r.name, {c: C.texto(r[c]) for c in campos
                                   if isinstance(r[c], str) and r[c] and C.texto(r[c]) != r[c]})


def _partes(pendientes):
    for doctype, campo_nombre in (("Customer", "customer_name"), ("Supplier", "supplier_name")):
        campos = ["name", campo_nombre, "tax_id"] + (["nombre_comercial"] if frappe.db.has_column(doctype, "nombre_comercial") else [])
        for r in frappe.get_all(doctype, fields=campos):
            cambios = {}
            for c in (campo_nombre, "nombre_comercial"):
                if r.get(c) and C.texto(r[c]) != r[c]:
                    cambios[c] = C.texto(r[c])
            if r.tax_id and C.rfc(r.tax_id) != r.tax_id:
                cambios["tax_id"] = C.rfc(r.tax_id)
            _set(doctype, r.name, cambios)


def _direcciones(pendientes):
    for r in frappe.get_all("Address", fields=["name", "country", "state", "pincode", "phone", "fax", "email_id",
                                               "is_your_company_address"]):
        cambios, mexico = {}, C._es_mexico(r.country)
        if not r.country:
            cambios["country"] = "Mexico"
        reglas = [("email_id", C.correo)]
        if mexico:
            reglas += [("state", C.estado_mx), ("pincode", C.cp_mx), ("phone", C.telefono_mx), ("fax", C.telefono_mx)]
        for campo, fn in reglas:
            if r[campo]:
                nuevo = _intenta(fn, r[campo], "Address", r.name, campo, pendientes)
                if nuevo != r[campo]:
                    cambios[campo] = nuevo
        _set("Address", r.name, cambios)
        ligas = _ligas("Address", r.name, ("Customer", "Supplier", "Company"))
        if not ligas and not r.is_your_company_address:
            pendientes.append(("Address", r.name, "links", "", "Dirección sin cliente, proveedor ni compañía."))


def _contactos(pendientes):
    for r in frappe.get_all("Contact", fields=["name", "email_id", "phone", "mobile_no", "user"]):
        cambios = {}
        for campo, fn in (("email_id", C.correo), ("phone", C.telefono), ("mobile_no", C.telefono)):
            if r[campo]:
                nuevo = _intenta(fn, r[campo], "Contact", r.name, campo, pendientes)
                if nuevo != r[campo]:
                    cambios[campo] = nuevo
        _set("Contact", r.name, cambios)
        ligas = _ligas("Contact", r.name, ("Customer", "Supplier", "Lead", "Company"))
        if not ligas and not r.user:
            pendientes.append(("Contact", r.name, "links", "", "Contacto sin cliente ni proveedor."))
    for hijo, campo, fn in (("Contact Email", "email_id", C.correo), ("Contact Phone", "phone", C.telefono)):
        for r in frappe.get_all(hijo, fields=["name", "parent", campo]):
            if r[campo]:
                nuevo = _intenta(fn, r[campo], "Contact", r.parent, campo, pendientes)
                if nuevo != r[campo]:
                    _set(hijo, r.name, {campo: nuevo})


def _folios():
    for doctype, campo in (("Sales Order", "po_no"), ("Purchase Invoice", "bill_no")):
        for r in frappe.get_all(doctype, filters={campo: ["is", "set"]}, fields=["name", campo]):
            if C.texto(r[campo]) != r[campo]:
                _set(doctype, r.name, {campo: C.texto(r[campo])})


def _rfc_repetidos(pendientes):
    for doctype in ("Customer", "Supplier"):
        for rfc, nombres in frappe.db.sql(
                f"""select tax_id, group_concat(name separator ' / ') from `tab{doctype}`
                    where ifnull(tax_id, '') not in ('', %s, %s) group by tax_id having count(*) > 1""",
                C.RFC_GENERICOS):
            pendientes.append((doctype, nombres, "tax_id", rfc, "El mismo RFC está en varios registros."))


def _campo_estado():
    make_property_setter("Address", "state", "fieldtype", "Autocomplete", "Select", validate_fields_for_doctype=False)
    make_property_setter("Address", "state", "options", "\n".join(C.ESTADOS_MX), "Text", validate_fields_for_doctype=False)
    frappe.clear_cache(doctype="Address")


def _reporte(pendientes):
    previo = frappe.db.get_value("File", {"file_name": ARCHIVO, "is_private": 1})
    if previo:
        frappe.delete_doc("File", previo, ignore_permissions=True, force=True)
    if not pendientes:
        return
    salida = io.StringIO()
    w = csv.writer(salida)
    w.writerow(["Documento", "Registro", "Campo", "Valor actual", "Qué revisar"])
    w.writerows(pendientes)
    frappe.get_doc({"doctype": "File", "file_name": ARCHIVO, "is_private": 1,
                    "content": salida.getvalue().encode("utf-8-sig")}).insert(ignore_permissions=True)
    print(f"Datos maestros: {len(pendientes)} pendientes de revisar a mano en «{ARCHIVO}».")
