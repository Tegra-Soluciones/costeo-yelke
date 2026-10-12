"""Fase 2: BOM y fichas de manufactura.

Va despues de la fase 1 (ya sin ordenes de compra, recibos ni planes).

Los BOM forman un arbol: un BOM de la prenda consume los BOM de sus piezas
(BOM Item.bom_no), y ERPNext no deja cancelar uno que otro BOM activo todavia
usa. Por eso no hay un orden fijo que sirva siempre: se dan pasadas repetidas
cancelando y borrando lo que se pueda, hasta que una pasada completa no logra
avanzar. Asi se desarma el arbol de afuera hacia adentro sin tener que
calcularlo.

Antes de eso hay que soltar dos amarres: Item.default_bom (apunta al BOM desde
el articulo) y las banderas is_active / is_default del propio BOM.
"""
import frappe

frappe.flags.in_migrate = True

# 1. Soltar el BOM predeterminado de cada articulo
sueltos = frappe.db.sql("""update `tabItem` set default_bom = NULL where ifnull(default_bom,'') != ''""")
frappe.db.commit()
print("Item.default_bom liberados")

# 2. Quitar banderas (en SQL: el documento esta validado y no admite save normal)
frappe.db.sql("""update `tabBOM` set is_active = 0, is_default = 0""")
frappe.db.commit()
print("BOM: is_active/is_default en 0")

# 3. Pasadas hasta que no se pueda avanzar mas
pasada, ultimo_error = 0, {}
while True:
    pasada += 1
    antes = frappe.db.count("BOM")
    if not antes:
        break
    for n in frappe.get_all("BOM", pluck="name"):
        try:
            if frappe.db.get_value("BOM", n, "docstatus") == 1:
                doc = frappe.get_doc("BOM", n)
                doc.flags.ignore_permissions = True
                doc.flags.ignore_links = True
                doc.cancel()
            frappe.delete_doc("BOM", n, force=True, ignore_permissions=True, delete_permanently=True)
        except Exception as e:
            ultimo_error[n] = str(e)[:130]
    frappe.db.commit()
    despues = frappe.db.count("BOM")
    print("   pasada %d: %d -> %d" % (pasada, antes, despues))
    if despues == antes:          # no se avanzo: no tiene caso seguir
        break
    if pasada > 12:
        break

print("BOM restantes:", frappe.db.count("BOM"))
for n, err in list(ultimo_error.items())[:6]:
    if frappe.db.exists("BOM", n):
        print("   ! %-26s %s" % (n, err))

# 4. Fichas de manufactura (estan en borrador, se borran directo)
for n in frappe.get_all("Orden Manufactura", pluck="name"):
    try:
        frappe.delete_doc("Orden Manufactura", n, force=True, ignore_permissions=True, delete_permanently=True)
    except Exception as e:
        print("   ! Orden Manufactura %-14s %s" % (n, str(e)[:120]))
frappe.db.commit()
print("Orden Manufactura restantes:", frappe.db.count("Orden Manufactura"))
