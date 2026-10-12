"""Fase 1 de la limpieza de los ejemplos de capacitacion en produccion.

Cancela y borra los documentos transaccionales en orden de dependencia. No toca
Costeo, Item, Item Price ni el catalogo de UOM -- eso es lo que se conserva.

Respaldo previo: 20261012_140847 (bench backup --with-files) y los archivos
respaldos/capacitacion-2026-10-12.{json,txt}.

Se corre asi:
    docker exec -i cimix-yelke-backend-1 bash -lc \
        "cd /home/frappe/frappe-bench && bench --site erp.yelke.com.mx console" \
        <<< "exec(open('/tmp/borrar-ejemplos-fase1.py').read(), {})"
"""
import frappe

frappe.flags.in_migrate = True

ORDEN = [
    "Purchase Invoice",        # facturas de compra (revierten la contabilidad)
    "Subcontracting Receipt",  # recibo del taller
    "Purchase Receipt",        # recibos de compra (revierten el kardex)
    "Subcontracting Order",    # encargos a taller
    "Stock Entry",             # envio de material al taller
    "Purchase Order",          # OC de material y de subcontratacion
    "Material Request",        # solicitudes de material
    "Production Plan",         # planes de produccion
    "Sales Order",             # ordenes de venta
    "Quotation",               # cotizaciones
]


def procesa(dt):
    """Cancela todo lo validado del doctype y despues lo borra.

    En dos pasadas a proposito: un documento no se puede borrar mientras otro del
    mismo doctype lo referencie todavia sin cancelar."""
    nombres = frappe.get_all(dt, pluck="name")
    ok, fallos = 0, []
    for n in nombres:
        try:
            if frappe.db.get_value(dt, n, "docstatus") == 1:
                doc = frappe.get_doc(dt, n)
                doc.flags.ignore_permissions = True
                doc.flags.ignore_links = True
                doc.cancel()
        except Exception as e:
            fallos.append((n, "cancelar", str(e)[:130]))
    frappe.db.commit()
    for n in nombres:
        try:
            frappe.delete_doc(dt, n, force=True, ignore_permissions=True, delete_permanently=True)
            ok += 1
        except Exception as e:
            fallos.append((n, "borrar", str(e)[:130]))
    frappe.db.commit()
    return len(nombres), ok, fallos


for dt in ORDEN:
    tot, ok, fallos = procesa(dt)
    print("%-26s %3d -> borrados %3d   quedan %d" % (dt, tot, ok, frappe.db.count(dt)))
    for n, paso, err in fallos[:4]:
        print("      ! %-22s %-9s %s" % (n, paso, err))

print()
print("RESTANTES:")
for dt in ORDEN + ["BOM", "Orden Manufactura", "Costeo", "GL Entry", "Stock Ledger Entry"]:
    print("   %-26s %d" % (dt, frappe.db.count(dt)))
