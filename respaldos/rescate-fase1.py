"""Rescate: termina la limpieza desde el estado a medias que dejo la fase 1 original.

Que salio mal en el primer intento y que corrige esto:

  1. El candado de folios de la propia app (contabilidad.bloquear_borrado_cancelado)
     impide borrar un documento CANCELADO para que su folio no se reutilice. Tiene
     una llave pensada justo para esto -- frappe.flags.permitir_borrar_cancelados --
     que el primer script no uso. Por eso todo quedo cancelado pero sin borrar.

  2. El orden era incorrecto: se cancelaron las ordenes de subcontratacion antes que
     el envio de material, y los recibos de compra antes de que su material volviera
     al almacen. Aqui ya no importa el orden original: lo unico que falta por cancelar
     son los recibos de compra, y se permite existencia negativa mientras tanto porque
     el material que trajeron ya no esta donde estaba.

Al final: cero documentos, cero asientos, cero kardex y los Bin en ceros.
"""
import frappe
from frappe.utils import flt

frappe.flags.in_migrate = True
# La llave del candado de folios (ver contabilidad.bloquear_borrado_cancelado).
frappe.flags.permitir_borrar_cancelados = True

# Existencia negativa permitida SOLO durante la limpieza: al cancelar un recibo cuyo
# material ya se movio o consumio, ERPNext se niega si la cuenta queda bajo cero.
neg_original = frappe.db.get_single_value("Stock Settings", "allow_negative_stock")
frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
frappe.db.commit()
print("existencia negativa permitida temporalmente (estaba en %s)" % neg_original)

ORDEN = ["Purchase Invoice", "Subcontracting Receipt", "Stock Entry", "Purchase Receipt",
         "Subcontracting Order", "Purchase Order", "Material Request", "Production Plan",
         "Sales Order", "Quotation", "Delivery Note", "Sales Invoice"]

print()
for dt in ORDEN:
    nombres = frappe.get_all(dt, pluck="name")
    if not nombres:
        continue
    fallos = []
    for n in nombres:                      # 1a pasada: cancelar lo que siga validado
        try:
            if frappe.db.get_value(dt, n, "docstatus") == 1:
                d = frappe.get_doc(dt, n)
                d.flags.ignore_permissions = True
                d.flags.ignore_links = True
                d.cancel()
        except Exception as e:
            fallos.append((n, "cancelar", str(e)[:120]))
    frappe.db.commit()
    for n in nombres:                      # 2a pasada: borrar
        try:
            frappe.delete_doc(dt, n, force=True, ignore_permissions=True, delete_permanently=True)
        except Exception as e:
            fallos.append((n, "borrar", str(e)[:120]))
    frappe.db.commit()
    print("%-26s %3d -> quedan %d" % (dt, len(nombres), frappe.db.count(dt)))
    for n, paso, err in fallos[:4]:
        print("      ! %-22s %-9s %s" % (n, paso, err))

# Asientos y kardex huerfanos: los que quedaron apuntando a un documento ya borrado.
for tabla, campo in (("GL Entry", "voucher_no"), ("Stock Ledger Entry", "voucher_no")):
    huerfanos = 0
    for r in frappe.get_all(tabla, fields=["name", "voucher_type", campo]):
        if not frappe.db.exists(r.voucher_type, r.get(campo)):
            frappe.db.sql("delete from `tab%s` where name=%%s" % tabla, r.name)
            huerfanos += 1
    frappe.db.commit()
    print("%-26s huerfanos borrados: %d   quedan %d" % (tabla, huerfanos, frappe.db.count(tabla)))

# Con el kardex en cero, cualquier saldo en Bin es una cache vieja: se pone en ceros.
if frappe.db.count("Stock Ledger Entry") == 0:
    frappe.db.sql("""update `tabBin` set actual_qty=0, stock_value=0, valuation_rate=0,
        reserved_qty=0, ordered_qty=0, indented_qty=0, planned_qty=0, projected_qty=0,
        reserved_qty_for_production=0, reserved_qty_for_sub_contract=0""")
    frappe.db.commit()
    print("Bin: saldos puestos en cero (ya no hay kardex que los respalde)")

frappe.db.set_single_value("Stock Settings", "allow_negative_stock", neg_original or 0)
frappe.db.commit()
print("existencia negativa devuelta a %s" % (neg_original or 0))

print()
print("=" * 72)
print("VERIFICACION")
print("=" * 72)
for dt in ORDEN + ["BOM", "Orden Manufactura", "GL Entry", "Stock Ledger Entry", "Journal Entry"]:
    print("   %-26s %d   (debe ser 0)" % (dt, frappe.db.count(dt)))
print()
for dt in ("Costeo", "Item", "Item Price", "UOM"):
    print("   %-26s %d   (se conserva)" % (dt, frappe.db.count(dt)))
print()
quedan = frappe.db.sql("""select item_code, warehouse, actual_qty, stock_value from `tabBin`
     where actual_qty != 0 or stock_value != 0""", as_dict=True)
print("EXISTENCIAS CON SALDO:", "ninguna — inventario limpio" if not quedan else "")
for b in quedan:
    print("   %-52s %-26s %12s  $%s" % (b.item_code[:52], b.warehouse[:26], flt(b.actual_qty), flt(b.stock_value)))
print()
print("ARTICULOS A CORREGIR -- ya se puede cambiar su UDM base?")
for code in ("BOTON DE PASTA", "BOTON-DE-PASTA-18-L", "BOTON-DE-PASTA-30L",
             'CONTACTEL NEGRO 1" (ROLLO CON 25 METROS)'):
    if not frappe.db.exists("Item", code):
        continue
    sle = frappe.db.count("Stock Ledger Entry", {"item_code": code})
    boms = frappe.db.count("BOM Item", {"item_code": code})
    print("   %-46s base=%-18s kardex=%-3d BOM=%-3d %s" % (
        code[:46], frappe.db.get_value("Item", code, "stock_uom"), sle, boms,
        "SE PUEDE" if (sle == 0 and boms == 0) else "bloqueado"))
