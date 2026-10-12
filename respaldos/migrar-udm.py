"""Migracion de UDM: quitar las que traen una medida, poner las bases que de verdad
son, marcar los paquetes como no divisibles y reexpresar los costeos.

Corre en seco por omision. Para aplicar:  APLICAR = True  (abajo).

Que hace, en orden:

 1. UDM con MEDIDA en el nombre ("Rollo de 100 mts", "Rollo 25 metros"). La unidad
    es generica -- un rollo es un rollo --; cuantos metros trae es el FACTOR de
    conversion de cada articulo, no parte del nombre. Los articulos que las usaban
    pasan a su unidad real (Metro) con "Rollo" como multiplo y el factor correcto.

 2. UDM BASE = lo que de verdad es. Un boton se compra, se cuenta y se consume por
    PIEZA; el mazo es la presentacion de compra. Con la base en Mazo, capturar "3
    botones por prenda" obligaba a poner un consumo de 0.0017 mazos.

 3. Lo que se compra por paquete no se parte: Rollo, Mazo, Gruesa, MILLAR y Paquete
    quedan marcados (ver costeo_api._es_compra_por_paquete), para que la orden de
    compra redondee y nunca le pida 19.56 rollos a un proveedor.

 4. Los renglones de costeo que estaban en una UDM de paquete se reexpresan en la
    base SIN cambiar el costo: el consumo se multiplica por el factor y el precio se
    divide entre el mismo factor. El precio original se conserva en `precio_compra`
    con su `supplier_uom`, que es justo como lo cotiza el proveedor.

 5. Se apaga `must_be_whole_number` nativo de ERPNext en las UDM que lo traian: lo
    valida en TODO documento, incluida la Solicitud de Material, que guarda
    cantidades fraccionarias por lote a proposito.

Requisito: el sitio no debe tener kardex ni BOM de esos articulos (ERPNext no deja
cambiar la stock_uom si los hay). Se verifica antes de tocar nada.
"""
import frappe
from frappe.utils import flt

APLICAR = False          # <<< ponlo en True para que escriba

PIEZA = "H87 - Pieza"
METRO = "MTR - Metro"

# base nueva por UDM base vieja, y el multiplo que queda en su lugar
REGLAS = {
    "Mazo":             (PIEZA, [("Mazo", 1728), ("Gruesa", 144)]),
    "Rollo de 100 mts": (METRO, [("Rollo", 100)]),
    "Rollo 25 metros":  (METRO, [("Rollo", 25)]),
    "MILLAR":           (PIEZA, [("MILLAR", 1000)]),
}
# UDM que son presentacion de compra: no se pueden pedir en fracciones
PAQUETE = {"Rollo", "Mazo", "Gruesa", "MILLAR", "Paquete", "Caja", "Bulto"}
# UDM con medida en el nombre que desaparecen del catalogo al terminar
A_BORRAR = ["Rollo de 100 mts", "Rollo 25 metros"]

log = []
def di(txt): log.append(txt); print(txt)


# El reexpresado de los costeos escribe `precio_compra`, que es un campo NUEVO: si el
# sitio todavia no corrio el migrate del deploy, la columna no existe y el script se
# caeria a la mitad -- dejando las bases cambiadas y los costeos sin reexpresar, que
# es el peor estado posible. Mejor no empezar.
if not frappe.db.has_column("Costeo Producto Detalle", "precio_compra"):
    frappe.throw("Falta la columna Costeo Producto Detalle.precio_compra: "
                 "corre `bench --site <sitio> migrate` (el deploy) ANTES de esta migracion.")


def redondea_consumo(x):
    """El consumo guardado venia redondeado a 8 decimales, asi que al multiplicarlo
    por 1728 sale 2.999998 en vez de 3. Cuando el resultado esta a menos de una
    milesima de un entero es que ese entero era el numero real -- 3 botones por
    prenda --, y se devuelve limpio. Un consumo de verdad fraccionario (1.23 metros)
    no se toca."""
    r = round(x)
    return float(r) if abs(x - r) < 0.001 else round(x, 6)


def bloqueado(item):
    """ERPNext no deja cambiar la stock_uom si el articulo tiene kardex o BOM."""
    razones = []
    if frappe.db.count("Stock Ledger Entry", {"item_code": item}):
        razones.append("kardex")
    if frappe.db.count("BOM Item", {"item_code": item}):
        razones.append("BOM")
    if frappe.db.count("BOM", {"item": item}):
        razones.append("BOM propio")
    return razones


# ── 1 y 2. Bases ────────────────────────────────────────────────────────────
di("=" * 94)
di("1) ARTICULOS QUE CAMBIAN DE UDM BASE")
di("=" * 94)
cambios = []
for vieja, (nueva, multiplos) in REGLAS.items():
    for it in frappe.get_all("Item", filters={"stock_uom": vieja}, fields=["name", "item_name"]):
        razones = bloqueado(it.name)
        if razones:
            di("   BLOQUEADO  %-50s %s -> %s   (%s)" % (it.name[:50], vieja, nueva, ", ".join(razones)))
            continue
        cambios.append((it.name, vieja, nueva, multiplos))
        di("   %-52s %-18s -> %-14s  multiplos: %s" % (
            it.name[:52], vieja, nueva, ", ".join("1 %s = %s" % (u, f) for u, f in multiplos)))
di("   total: %d" % len(cambios))

if APLICAR:
    for name, vieja, nueva, multiplos in cambios:
        # DOS guardados, no uno. ERPNext vacia la tabla de conversiones a proposito
        # cuando cambia la stock_uom (Item.add_default_uom_in_conversion_factor_table:
        # "please redefine conversion factors for new UOM"), porque los factores
        # viejos se referian a la base vieja. Si se hace todo en un solo save, los
        # multiplos que acabamos de poner se los lleva ese mismo borrado.
        doc = frappe.get_doc("Item", name)
        doc.stock_uom = nueva
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.save()

        doc = frappe.get_doc("Item", name)          # ya con la tabla vaciada por ERPNext
        doc.set("uoms", [])
        for u, f in multiplos:
            doc.append("uoms", {"uom": u, "conversion_factor": f,
                                "compra_por_paquete_completo": 1 if u in PAQUETE else 0})
        # La base de estos articulos SI es divisible (pieza suelta, metro): el candado
        # de "no se parte" vive en la presentacion de compra, no en la base.
        doc.compra_por_paquete_completo = 0
        if flt(doc.get("over_delivery_receipt_allowance")) < 100:
            doc.over_delivery_receipt_allowance = 100
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.save()
    frappe.db.commit()
    di("   APLICADO")

# ── 3. Paquetes no divisibles en TODOS los articulos ────────────────────────
di("")
di("=" * 94)
di("2) MULTIPLOS DE PAQUETE QUE SE MARCAN COMO NO DIVISIBLES")
di("=" * 94)
pendientes = frappe.get_all(
    "UOM Conversion Detail",
    filters={"parenttype": "Item", "uom": ["in", sorted(PAQUETE)], "compra_por_paquete_completo": 0},
    fields=["name", "parent", "uom", "conversion_factor"])
for r in pendientes:
    di("   %-52s %-10s x%s" % (r.parent[:52], r.uom, flt(r.conversion_factor)))
di("   total: %d" % len(pendientes))
if APLICAR and pendientes:
    for r in pendientes:
        frappe.db.set_value("UOM Conversion Detail", r.name, "compra_por_paquete_completo", 1,
                            update_modified=False)
    # El margen nativo evita que el redondeo del paquete bloquee la OC despues.
    for parent in {r.parent for r in pendientes}:
        if flt(frappe.db.get_value("Item", parent, "over_delivery_receipt_allowance")) < 100:
            frappe.db.set_value("Item", parent, "over_delivery_receipt_allowance", 100,
                                update_modified=False)
    frappe.db.commit()
    di("   APLICADO")

# ── 4. Renglones de costeo ──────────────────────────────────────────────────
di("")
di("=" * 94)
di("3) RENGLONES DE COSTEO QUE SE REEXPRESAN EN LA UDM BASE")
di("=" * 94)
di("   (el costo por prenda NO cambia: el consumo se multiplica y el precio se divide)")
filas = frappe.db.sql("""select d.name, d.parent, d.item, d.internal_uom, d.rendimiento,
       d.internal_qty, d.unit_price, d.total
   from `tabCosteo Producto Detalle` d
   where d.internal_uom in %(uoms)s""", {"uoms": tuple(REGLAS)}, as_dict=True)
for r in filas:
    nueva, multiplos = REGLAS[r.internal_uom]
    factor = dict(multiplos).get(r.internal_uom)
    if not factor:
        di("   ! %-30s %s sin factor conocido, se omite" % (r.item, r.internal_uom))
        continue
    consumo = redondea_consumo(flt(r.internal_qty) * factor)
    precio = flt(r.unit_price) / factor
    di("   %-22s %-22s %-8s consumo %-12s -> %-8s %s   precio %-9s -> %-9s   total %s -> %s" % (
        r.parent[-22:], (r.item or "")[:22], r.internal_uom, round(flt(r.internal_qty), 8),
        round(consumo, 6), nueva, flt(r.unit_price), round(precio, 6),
        flt(r.total), round(consumo * precio, 2)))
    if APLICAR:
        frappe.db.set_value("Costeo Producto Detalle", r.name, {
            "internal_uom": nueva,
            "internal_qty": consumo,
            "rendimiento": (1.0 / consumo) if consumo else 0,
            "supplier_uom": r.internal_uom,      # el proveedor sigue cotizando por Mazo
            "conversion_factor": factor,
            "precio_compra": flt(r.unit_price),  # lo que de verdad cotizo
            "unit_price": precio,                # el derivado por UDM base
        }, update_modified=False)
        # La cantidad que el material tiene asignada a su etapa es el mismo consumo.
        frappe.db.sql("""update `tabCosteo Material Etapa` me
            join `tabCosteo Producto Detalle` d on d.material_id = me.material_id
            set me.qty = %s where d.name = %s""", (consumo, r.name))
di("   total: %d" % len(filas))
if APLICAR and filas:
    frappe.db.commit()
    di("   APLICADO")

# ── 5. Check nativo de ERPNext ──────────────────────────────────────────────
di("")
di("=" * 94)
di("4) SE APAGA must_be_whole_number (lo valida en TODO documento, incluida la solicitud)")
di("=" * 94)
nativas = frappe.get_all("UOM", filters={"must_be_whole_number": 1}, pluck="name")
di("   " + (", ".join(nativas) if nativas else "ninguna"))
if APLICAR and nativas:
    for u in nativas:
        frappe.db.set_value("UOM", u, "must_be_whole_number", 0, update_modified=False)
    frappe.db.commit()
    di("   APLICADO")

# ── 6. Borrar las UDM con medida ────────────────────────────────────────────
di("")
di("=" * 94)
di("5) UDM CON MEDIDA EN EL NOMBRE QUE SE BORRAN DEL CATALOGO")
di("=" * 94)
for u in A_BORRAR:
    if not frappe.db.exists("UOM", u):
        di("   %-20s ya no existe" % u)
        continue
    usos = frappe.db.count("Item", {"stock_uom": u}) + frappe.db.count(
        "UOM Conversion Detail", {"uom": u})
    di("   %-20s usos restantes: %d %s" % (u, usos, "-> se borra" if usos == 0 else "-> NO se borra"))
    if APLICAR and usos == 0:
        frappe.delete_doc("UOM", u, force=True, ignore_permissions=True)
if APLICAR:
    frappe.db.commit()

# ── Verificacion ────────────────────────────────────────────────────────────
di("")
di("=" * 94)
di("ESTADO FINAL")
di("=" * 94)
for u in sorted(set(list(REGLAS) + list(PAQUETE) + [PIEZA, METRO])):
    if not frappe.db.exists("UOM", u):
        continue
    base = frappe.db.count("Item", {"stock_uom": u})
    conv = frappe.get_all("UOM Conversion Detail", filters={"uom": u, "parenttype": "Item"},
                          fields=["compra_por_paquete_completo"])
    if base or conv:
        di("   %-20s base en %-3d articulos | multiplo en %-3d (%d marcados no divisibles)" % (
            u, base, len(conv), sum(1 for c in conv if c.compra_por_paquete_completo)))
di("")
di("Articulos que siguen con una UDM de paquete como base (revisar a mano):")
hay = False
for u in sorted(PAQUETE):
    for it in frappe.get_all("Item", filters={"stock_uom": u}, pluck="name"):
        di("   %-52s base=%s" % (it[:52], u)); hay = True
if not hay:
    di("   ninguno")

if not APLICAR:
    di("")
    di(">>> CORRIDA EN SECO: no se escribio nada. Pon APLICAR = True para aplicar.")
