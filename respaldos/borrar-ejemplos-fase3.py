"""Fase 3: dejar los costeos en borrador, limpiar referencias colgadas y verificar.

Lo que SE CONSERVA (a proposito): los 6 Costeos, los 146 Item, sus Item Price y
el catalogo de UOM. Eso es justo lo que se va a editar despues.

Los 3 costeos validados se bajan a borrador escribiendo docstatus directo. No se
usa cancel(): cancelar deja el documento en estado 2 (cancelado), que no es lo
que se pidio, y ademas dispara los on_cancel de la app cuando ya no hay nada
abajo que revertir -- toda la cadena se borro en las fases 1 y 2.
"""
import frappe
from frappe.utils import flt

frappe.flags.in_migrate = True

VALIDADOS = frappe.get_all("Costeo", filters={"docstatus": 1}, pluck="name")

# 1. Soltar las tablas hijas que apuntan a documentos ya borrados. El Costeo hereda
#    las tablas del Production Plan (sales_orders, material_requests,
#    prod_plan_references), y sus renglones quedaron apuntando a OV y solicitudes que
#    ya no existen; tabla_lotes_costeo guarda los lotes de entrega de esa corrida.
HIJAS = ["Production Plan Sales Order", "Material Request Plan Item",
         "Production Plan Material Request", "Production Plan Item Reference", "Costeo Lote"]
for hijo in HIJAS:
    if not frappe.db.table_exists(hijo):
        continue
    n = frappe.db.sql("select count(*) from `tab%s` where parenttype='Costeo'" % hijo)[0][0]
    if n:
        frappe.db.sql("delete from `tab%s` where parenttype='Costeo'" % hijo)
        print("   %-34s %d renglones borrados" % (hijo, n))
frappe.db.commit()
print("tablas hijas de referencia limpiadas (lotes y enlaces a OV/MR/plan)")

# 2. Bajar a borrador
for name in VALIDADOS:
    frappe.db.set_value("Costeo", name, {"docstatus": 0, "costeo_status": "Borrador"},
                        update_modified=False)
frappe.db.commit()
print("costeos bajados a borrador:", VALIDADOS)

# 3. Verificacion
print()
print("=" * 72)
print("VERIFICACION")
print("=" * 72)
for dt in ("Quotation", "Sales Order", "Production Plan", "Material Request", "Purchase Order",
           "Subcontracting Order", "Subcontracting Receipt", "Purchase Receipt", "Purchase Invoice",
           "Stock Entry", "Delivery Note", "Sales Invoice", "BOM", "Orden Manufactura",
           "GL Entry", "Stock Ledger Entry", "Journal Entry"):
    try:
        print("   %-26s %d   (debe ser 0)" % (dt, frappe.db.count(dt)))
    except Exception:
        pass
print()
for dt in ("Costeo", "Item", "Item Price", "UOM"):
    print("   %-26s %d   (se conserva)" % (dt, frappe.db.count(dt)))

print()
print("EXISTENCIAS QUE QUEDAN (deberian ser todas 0):")
quedan = frappe.db.sql("""select item_code, warehouse, actual_qty, stock_value from `tabBin`
     where actual_qty != 0 or stock_value != 0""", as_dict=True)
if not quedan:
    print("   ninguna — inventario limpio")
for b in quedan:
    print("   %-52s %-26s %12s  $%s" % (b.item_code[:52], b.warehouse[:26], flt(b.actual_qty), flt(b.stock_value)))

print()
print("ESTADO DE LOS COSTEOS:")
for c in frappe.get_all("Costeo", fields=["name", "titulo", "docstatus", "costeo_status"], order_by="creation"):
    print("   %-36s ds=%s  %-16s %s" % (c.name, c.docstatus, c.costeo_status, (c.titulo or "")[:30]))

print()
print("UDM BASE DE LOS ARTICULOS QUE VAMOS A CORREGIR (ya deberia dejarse cambiar):")
for code in ("BOTON DE PASTA", "BOTON-DE-PASTA-18-L", "BOTON-DE-PASTA-30L",
             'CONTACTEL NEGRO 1" (ROLLO CON 25 METROS)'):
    if frappe.db.exists("Item", code):
        sle = frappe.db.count("Stock Ledger Entry", {"item_code": code})
        print("   %-46s base=%-18s movimientos=%d" % (
            code[:46], frappe.db.get_value("Item", code, "stock_uom"), sle))
