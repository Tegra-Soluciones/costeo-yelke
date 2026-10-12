"""La orden de compra del CLIENTE deja de ser un número escrito a mano y pasa a ser el
archivo que mandó el cliente, adjunto a la Orden de Venta.

El campo NO se marca `reqd`: la OV nace en BORRADOR y un archivo solo se puede colgar
de un documento que ya existe, así que con `reqd` no se podría ni crear el borrador.
La obligatoriedad vive en el `before_submit` del doctype
(costeo_yelke.api.costeo_api.validar_oc_cliente_adjunta), que tampoco se puede saltar
desde el escritorio de ERPNext.

El campo nativo `po_no` (número de OC) se conserva: sigue sirviendo para buscar y se
arrastra a la factura.
"""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({"Sales Order": [{
        "fieldname": "oc_cliente_archivo",
        "label": "OC del Cliente (archivo)",
        "fieldtype": "Attach",
        "insert_after": "po_no",
        "description": (
            "Orden de compra del cliente, el archivo tal cual lo mandó. "
            "Obligatoria para validar la orden de venta."
        ),
    }]}, update=True)
