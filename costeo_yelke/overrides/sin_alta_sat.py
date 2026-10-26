import frappe

FLETE = "Flete / Envío"


def quitar_iva_sin_alta_sat(doc, method=None):
    """validate de Orden de compra, Recibo y Factura de compra: un proveedor sin alta
    en el SAT (Supplier.sin_alta_sat, patch v0_2_65) no emite CFDI ni cobra IVA.

    ERPNext vuelve a poner la plantilla de impuestos por defecto al guardar y, del
    recibo a la factura, la volvería a llenar con IVA; aquí se quita siempre (menos la
    fila de flete) y se recalculan los totales. Un documento ya validado no pasa por
    aquí."""
    if not doc.get("supplier") or not frappe.db.has_column("Supplier", "sin_alta_sat"):
        return
    if not frappe.db.get_value("Supplier", doc.supplier, "sin_alta_sat"):
        return
    otras = [r for r in (doc.get("taxes") or []) if r.description != FLETE]
    if not otras and not doc.get("taxes_and_charges"):
        return
    doc.set("taxes", [r for r in (doc.get("taxes") or []) if r.description == FLETE])
    doc.taxes_and_charges = None
    doc.calculate_taxes_and_totals()
