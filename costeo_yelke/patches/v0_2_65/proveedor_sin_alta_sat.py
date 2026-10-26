"""Proveedores (talleres) que no están dados de alta en el SAT: no pueden emitir CFDI,
así que no cobran IVA. Sus órdenes de compra y facturas internas van sin impuestos
(costeo._get_purchase_tax_template) y el pago se respalda con un recibo interno.

Se marca desde la orden a taller (Producción · Preparar · Órdenes a talleres) o en la
ficha del proveedor."""
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Supplier": [
            {"fieldname": "sin_alta_sat", "label": "Sin alta en el SAT (sin factura, sin IVA)", "fieldtype": "Check",
             "insert_after": "tax_id", "default": "0",
             "description": "No emite CFDI: sus órdenes y facturas internas van sin IVA. El pago se respalda con un recibo interno."},
        ],
    })
