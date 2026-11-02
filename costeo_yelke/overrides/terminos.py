"""Términos y condiciones exclusivos de un cliente o proveedor.

ERPNext no liga términos a un cliente: solo trae uno por defecto para toda la compañía.
Aquí un término puede marcarse «Exclusivo de» un cliente (venta) o un proveedor (compra)
(campos del patch v0_2_75). En los documentos solo se ofrecen los generales del tipo más
los exclusivos de esa parte; uno exclusivo de otra parte no se acepta. Si el documento
nuevo llega sin términos, se le pone el exclusivo de su parte o, si no hay, el de la
compañía.
"""
import frappe
from frappe import _

from costeo_yelke.utils import resolver_terminos

# doctype -> (campo de la parte, es de venta)
DOCUMENTOS = {
    "Quotation": ("party_name", True),
    "Sales Order": ("customer", True),
    "Sales Invoice": ("customer", True),
    "Purchase Order": ("supplier", False),
}


def _campo_exclusivo(venta):
    return "exclusivo_cliente" if venta else "exclusivo_proveedor"


def _parte(doc):
    campo, _venta = DOCUMENTOS[doc.doctype]
    if doc.doctype == "Quotation" and doc.get("quotation_to") != "Customer":
        return None
    return doc.get(campo)


def opciones(venta=None):
    """Términos para las listas de la app, con lo necesario para filtrarlos allá
    (frontend utils/terminos.js): de venta, de compra y de quién son exclusivos."""
    filtros = {} if venta is None else {"selling" if venta else "buying": 1}
    campos = ["name", "selling", "buying"]
    if frappe.get_meta("Terms and Conditions").has_field("exclusivo_cliente"):
        campos += ["exclusivo_cliente", "exclusivo_proveedor"]
    return frappe.get_all("Terms and Conditions", filters={**filtros, "disabled": 0},
                          fields=campos, order_by="name asc")


def por_defecto(venta, parte, company=None):
    """El exclusivo de la parte; si no tiene, el de la compañía."""
    if parte and frappe.get_meta("Terms and Conditions").has_field(_campo_exclusivo(venta)):
        propio = frappe.db.get_value("Terms and Conditions", {
            _campo_exclusivo(venta): parte, "disabled": 0, "selling" if venta else "buying": 1}, "name")
        if propio:
            return propio
    if company:
        return frappe.db.get_value("Company", company, "default_selling_terms" if venta else "default_buying_terms")
    return None


@frappe.whitelist()
def termino_por_defecto(tipo, parte=None, company=None):
    return por_defecto(tipo == "venta", parte, company)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def buscar_terminos(doctype, txt, searchfield, start, page_len, filters):
    """Búsqueda del campo tc_name en el Escritorio: generales + exclusivos de la parte."""
    venta = (filters or {}).get("tipo") != "compra"
    parte = (filters or {}).get("parte") or ""
    exclusivo = _campo_exclusivo(venta)
    return frappe.db.sql(f"""
        select name from `tabTerms and Conditions`
        where disabled = 0 and `{"selling" if venta else "buying"}` = 1
          and (ifnull(`{exclusivo}`, '') = '' or `{exclusivo}` = %(parte)s)
          and name like %(txt)s
        order by name limit %(start)s, %(page_len)s""",
        {"parte": parte, "txt": f"%{txt}%", "start": start, "page_len": page_len})


def terminos_del_documento(doc, method=None):
    """before_validate de Cotización, Orden de venta, Factura de venta y Orden de compra."""
    if not frappe.get_meta("Terms and Conditions").has_field("exclusivo_cliente"):
        return
    campo, venta = DOCUMENTOS[doc.doctype]
    parte = _parte(doc)
    if not doc.get("tc_name"):
        if doc.is_new():
            tc = por_defecto(venta, parte, doc.get("company"))
            if tc:
                doc.tc_name = tc
                if not doc.get("terms"):
                    doc.terms = resolver_terminos(tc)
        return
    if not (doc.is_new() or doc.has_value_changed("tc_name") or doc.has_value_changed(campo)):
        return
    duenio = frappe.db.get_value("Terms and Conditions", doc.tc_name, _campo_exclusivo(venta))
    if duenio and duenio != parte:
        quien = _("del cliente") if venta else _("del proveedor")
        frappe.throw(_("Los términos «{0}» son exclusivos {1} {2}. Elige unos generales o los de este documento.")
                     .format(doc.tc_name, quien, duenio), title=_("Términos exclusivos"))
