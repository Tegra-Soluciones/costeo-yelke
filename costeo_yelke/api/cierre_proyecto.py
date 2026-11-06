"""Cierre del proyecto: un costeo queda «Completado» cuando ya se entregó y se COBRÓ
todo -- sus órdenes de venta entregadas y facturadas al 100 % y cada factura de venta
validada con saldo cero (un anticipo que cubre todo no cierra un pedido sin entregar).
Antes se marcaba al generar la factura; un proyecto facturado pero sin cobrar se
perdía de la lista de activos.

Se revisa en cada movimiento que cambia el saldo de una factura de venta (validar o
cancelar la factura, un pago o una póliza que la cobra) o lo entregado (remisión) y, como red, una vez al día
(la conciliación de pagos de ERPNext no dispara eventos)."""
import frappe
from frappe.utils import flt

# Solo estos estados los mueve el cobro; los anteriores los manejan sus propios pasos
# y un costeo cancelado no se toca.
_ESTADOS_DE_CIERRE = ("En Producción", "Entregado", "Completado")


def _ordenes(costeo):
    return frappe.get_all("Sales Order", filters={"costeo": costeo, "docstatus": 1, "status": ["!=", "Closed"]},
                          fields=["name", "per_billed", "per_delivered"])


def _facturas(costeo, ordenes):
    nombres = set()
    if frappe.db.has_column("Sales Invoice", "costeo"):
        nombres |= set(frappe.get_all("Sales Invoice", filters={"costeo": costeo, "docstatus": 1}, pluck="name"))
    if ordenes:
        nombres |= set(frappe.get_all("Sales Invoice Item", filters={"sales_order": ["in", [o.name for o in ordenes]],
                                                                    "docstatus": 1}, pluck="parent"))
    if not nombres:
        return []
    return frappe.get_all("Sales Invoice", filters={"name": ["in", list(nombres)], "is_return": 0},
                          fields=["name", "outstanding_amount"])


def esta_cobrado(costeo):
    ordenes = _ordenes(costeo)
    if not ordenes or any(flt(o.per_billed) < 99.99 or flt(o.per_delivered) < 99.99 for o in ordenes):
        return False
    facturas = _facturas(costeo, ordenes)
    return bool(facturas) and all(flt(f.outstanding_amount) <= 0.005 for f in facturas)


def revisar(costeo):
    """Pone o quita «Completado» según el cobro. Devuelve el estado que quedó."""
    if not costeo or not frappe.db.exists("Costeo", costeo):
        return None
    estado = frappe.db.get_value("Costeo", costeo, "costeo_status")
    if estado not in _ESTADOS_DE_CIERRE:
        return estado
    if esta_cobrado(costeo):
        nuevo = "Completado"
    elif estado == "Completado":
        ordenes = _ordenes(costeo)
        entregado = bool(ordenes) and all(flt(o.per_delivered) >= 99.99 for o in ordenes)
        nuevo = "Entregado" if entregado else "En Producción"
    else:
        nuevo = estado
    if nuevo != estado:
        frappe.db.set_value("Costeo", costeo, "costeo_status", nuevo, update_modified=False)
    return nuevo


def _costeos_de_facturas(facturas):
    out = set()
    for si in set(facturas):
        if not si:
            continue
        c = frappe.db.get_value("Sales Invoice", si, "costeo") if frappe.db.has_column("Sales Invoice", "costeo") else None
        if not c:
            so = frappe.db.get_value("Sales Invoice Item", {"parent": si, "sales_order": ["is", "set"]}, "sales_order")
            c = frappe.db.get_value("Sales Order", so, "costeo") if so else None
        if c:
            out.add(c)
    return out


def al_mover_cobro(doc, method=None):
    """on_submit / on_cancel de Sales Invoice, Payment Entry, Journal Entry y Delivery
    Note (si se cobró por adelantado, se completa al entregar)."""
    if doc.doctype == "Delivery Note":
        ordenes = {i.against_sales_order for i in doc.get("items") or [] if i.against_sales_order}
        costeos = {doc.get("costeo")} | {frappe.db.get_value("Sales Order", so, "costeo") for so in ordenes}
        for costeo in filter(None, costeos):
            revisar(costeo)
        return
    if doc.doctype == "Sales Invoice":
        facturas = [doc.name, doc.get("return_against")]
    elif doc.doctype == "Payment Entry":
        facturas = [r.reference_name for r in doc.get("references") or [] if r.reference_doctype == "Sales Invoice"]
    else:
        facturas = [a.reference_name for a in doc.get("accounts") or [] if a.reference_type == "Sales Invoice"]
    for costeo in _costeos_de_facturas(facturas):
        revisar(costeo)


def revisar_todos():
    """Diario: los cobros conciliados con la herramienta de conciliación no disparan eventos."""
    for costeo in frappe.get_all("Costeo", filters={"docstatus": 1, "costeo_status": ["in", list(_ESTADOS_DE_CIERRE)]},
                                 pluck="name"):
        revisar(costeo)
