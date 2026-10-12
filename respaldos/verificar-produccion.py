"""Solo lectura: foto del estado de produccion. No cambia nada.

Sirve para ver el antes y el despues de la limpieza.
"""
import frappe
from frappe.utils import flt

print("sitio:", frappe.local.site)
print()
print("DOCUMENTOS DEL FLUJO (deben quedar en 0 al terminar)")
print("-" * 60)
for dt in ("Quotation", "Sales Order", "Production Plan", "Material Request",
           "Request for Quotation", "Supplier Quotation", "Purchase Order",
           "Subcontracting Order", "Subcontracting Receipt", "Purchase Receipt",
           "Purchase Invoice", "Stock Entry", "Delivery Note", "Sales Invoice",
           "BOM", "Orden Manufactura", "Journal Entry", "Payment Entry",
           "GL Entry", "Stock Ledger Entry"):
    try:
        n = frappe.db.count(dt)
    except Exception:
        continue
    if n:
        print("   %-26s %d" % (dt, n))

print()
print("SE CONSERVA")
print("-" * 60)
for dt in ("Costeo", "Item", "Item Price", "UOM", "Supplier", "Customer"):
    print("   %-26s %d" % (dt, frappe.db.count(dt)))

print()
print("COSTEOS")
print("-" * 60)
for c in frappe.get_all("Costeo", fields=["name", "titulo", "docstatus", "costeo_status"],
                        order_by="creation"):
    print("   %-36s ds=%s  %-16s %s" % (c.name, c.docstatus, c.costeo_status, (c.titulo or "")[:30]))

print()
print("EXISTENCIAS CON SALDO")
print("-" * 60)
filas = frappe.db.sql("""select item_code, warehouse, actual_qty, stock_value from `tabBin`
     where actual_qty != 0 or stock_value != 0 order by item_code""", as_dict=True)
if not filas:
    print("   ninguna — inventario limpio")
for b in filas:
    print("   %-50s %-26s %12s  $%s" % (b.item_code[:50], b.warehouse[:26],
                                        flt(b.actual_qty), flt(b.stock_value)))

print()
print("ARTICULOS A CORREGIR -- se puede cambiar ya su UDM base?")
print("-" * 60)
for code in ("BOTON DE PASTA", "BOTON-DE-PASTA-18-L", "BOTON-DE-PASTA-30L",
             'CONTACTEL NEGRO 1" (ROLLO CON 25 METROS)'):
    if not frappe.db.exists("Item", code):
        continue
    sle = frappe.db.count("Stock Ledger Entry", {"item_code": code})
    boms = frappe.db.count("BOM Item", {"item_code": code})
    print("   %-46s base=%-18s kardex=%-3d BOM=%-3d  %s" % (
        code[:46], frappe.db.get_value("Item", code, "stock_uom"), sle, boms,
        "SE PUEDE" if (sle == 0 and boms == 0) else "todavia bloqueado"))
