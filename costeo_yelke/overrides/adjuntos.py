"""Adjuntos de los campos de archivo: en la lista de adjuntos solo queda el vigente.

Dos fuentes de repetidos:
- el archivo se subía sin decir su campo; al guardar la ruta en el campo, ERPNext no
  reconocía ese adjunto y creaba otra copia (la app ya manda el campo, ver
  frontend utils/frappe.js uploadFile);
- al cambiar o quitar el archivo, el anterior se quedaba adjunto.
Al guardar el documento se quitan las copias repetidas del archivo vigente y el que
se reemplazó. El archivo físico solo se borra si ningún otro registro lo usa (File).
"""
import frappe

CAMPOS = {
    "Sales Order": ("oc_cliente_archivo",),
    "Sales Invoice": ("factura_pdf", "factura_xml"),
    "Purchase Invoice": ("factura_pdf", "factura_xml"),
}


def _adjuntos(doc, file_url):
    return frappe.get_all("File", filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name,
                                           "file_url": file_url},
                          fields=["name", "attached_to_field"], order_by="creation asc")


def _borrar(nombre):
    frappe.delete_doc("File", nombre, ignore_permissions=True)


def limpiar_adjuntos(doc, method=None):
    """on_update / on_update_after_submit."""
    antes = doc.get_doc_before_save()
    for campo in CAMPOS.get(doc.doctype, ()):
        if not frappe.get_meta(doc.doctype).has_field(campo):
            continue
        vigente = doc.get(campo)
        anterior = antes.get(campo) if antes else None
        if anterior and anterior != vigente:
            for f in _adjuntos(doc, anterior):
                _borrar(f.name)
        if vigente:
            copias = _adjuntos(doc, vigente)
            # Se queda uno: el que ya es del campo, si lo hay.
            conservar = next((f for f in copias if f.attached_to_field == campo), copias[0] if copias else None)
            for f in copias:
                if f is not conservar:
                    _borrar(f.name)
