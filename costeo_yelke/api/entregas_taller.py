"""A dónde entrega un taller lo que termina ("Al terminar, entregar a").

En el sistema todo lo que un taller devuelve entra al almacén de trabajos en proceso y
de ahí se transfiere al siguiente taller. En la vida real Yelke le indica al taller que
lo mande DIRECTO a quien sigue en el flujo: unas piezas a un taller, otras a otro, cada
uno con su dirección. Esto no mueve inventario; es la instrucción que viaja en la orden
de maquila.

El destino se deduce del flujo de producción: cada estado de pieza que produce el
taller lo consume la siguiente operación (``insumos`` de _resolve_piece_states), y lo
que consume el producto terminado va a la operación final. Lo que sale de la operación
final (la prenda terminada) va con Yelke.

Se guarda en la propia OC (``om_indicar_entrega`` + tabla ``om_entregas``, ambos
allow_on_submit y con prefijo om_ para que no cuenten como cambio comercial, ver
aprobaciones._cambio_comercial). Mientras nadie edite la tabla, se muestra e imprime lo
calculado, así que siempre sigue al flujo; al editarla manda lo capturado.
"""
import json

import frappe
from frappe import _

from costeo_yelke.roles import requiere_vista


def _direccion_texto(nombre):
    from costeo_yelke.api.impresion import direccion_lineas
    return "\n".join(l.strip() for l in direccion_lineas(nombre))


def _direccion_proveedor(supplier):
    from frappe.contacts.doctype.address.address import get_default_address
    return _direccion_texto(get_default_address("Supplier", supplier))


def _direccion_compania(company):
    from frappe.contacts.doctype.address.address import get_company_address
    return _direccion_texto(get_company_address(company).get("company_address") if company else None)


def _destinos_de_producto(doc, producto):
    """{item_que_sale: [op_key que lo recibe | None = Yelke]} y {op_key: op} de un
    producto del costeo, más {item: nombre de pieza}."""
    from costeo_yelke.api.costeo_api import _piece_states_de
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _resolve_production_operations

    etapas = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == producto]
    ops = _resolve_production_operations(etapas, producto)
    ps = _piece_states_de(doc, producto, ops)
    por_key = {op.op_key: op for op in ops}
    terminal = next((op for op in ops if op.is_terminal), None)

    destinos, pieza_de = {}, {}
    for e in ps.estados:
        pieza_de[e.item] = e.pieza
        for item, _qty in e.insumos:
            destinos.setdefault(item, []).append(e.op_key)
    if terminal:
        for item, _qty in ps.terminal_insumos:
            destinos.setdefault(item, []).append(terminal.op_key)
        destinos[terminal.output_item] = [None]
    destinos[producto] = [None]
    return destinos, por_key, pieza_de


def calcular_entregas(po_doc):
    """Filas sugeridas: una por destino, con las piezas que van ahí."""
    costeo = po_doc.get("costeo")
    if not costeo or not frappe.db.exists("Costeo", costeo):
        return []
    doc = frappe.get_doc("Costeo", costeo)
    from costeo_yelke.api.om_general import _base_de

    cache, filas, indice = {}, [], {}
    for it in po_doc.items:
        fg = it.get("fg_item") or ""
        prod = it.get("producto_terminado") or fg.split(" · ")[0]
        if not fg or not prod:
            continue
        if prod not in cache:
            try:
                cache[prod] = _destinos_de_producto(doc, prod)
            except Exception:
                frappe.log_error(title=f"Entregas de taller: {po_doc.name} / {prod}")
                cache[prod] = ({}, {}, {})
        destinos, por_key, pieza_de = cache[prod]
        if fg not in destinos:
            continue
        base = _base_de(doc, prod)
        if fg == prod:
            pieza = _("Prenda terminada")
        else:
            pieza = pieza_de.get(fg) or (_("Prenda armada") if " · ARMADA-" in fg else fg.split(" · ")[-1])
        for op_key in destinos[fg]:
            supplier = por_key[op_key].supplier if op_key else None
            clave = (base, supplier or "")
            if clave not in indice:
                indice[clave] = len(filas)
                if supplier:
                    nombre = frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier
                    direccion = _direccion_proveedor(supplier)
                else:
                    nombre = _("{0} · almacén de producto terminado").format(po_doc.company)
                    direccion = _direccion_compania(po_doc.company)
                filas.append(frappe._dict(
                    producto=base, piezas=[], entregar_a=supplier, destino=nombre,
                    direccion=direccion, mismo_taller=supplier == po_doc.supplier))
            f = filas[indice[clave]]
            if pieza not in f.piezas:
                f.piezas.append(pieza)
    for f in filas:
        f.piezas = ", ".join(f.piezas)
    return filas


def entregas_de_oc(po_doc):
    """Lo que se muestra e imprime: la tabla capturada si hay, si no lo calculado.
    Vacío si la orden no indica entrega."""
    if not po_doc.get("is_subcontracted") or not frappe.get_meta("Purchase Order").has_field("om_entregas"):
        return []
    if not po_doc.get("om_indicar_entrega"):
        return []
    if po_doc.get("om_entregas"):
        return [frappe._dict(producto=r.producto, piezas=r.piezas, entregar_a=r.entregar_a,
                             destino=r.destino, direccion=r.direccion,
                             mismo_taller=bool(r.entregar_a) and r.entregar_a == po_doc.supplier)
                for r in po_doc.om_entregas]
    return calcular_entregas(po_doc)


def entregas_impresion(doc):
    """Método jinja para la Orden de Maquila."""
    try:
        return entregas_de_oc(doc)
    except Exception:
        frappe.log_error(title=f"Entregas de taller (impresión): {doc.name}")
        return []


@frappe.whitelist()
def get_entregas(po: str) -> dict:
    po_doc = frappe.get_doc("Purchase Order", po)
    tiene = frappe.get_meta("Purchase Order").has_field("om_entregas")
    capturadas = bool(tiene and po_doc.get("om_entregas"))
    filas = ([frappe._dict(producto=r.producto, piezas=r.piezas, entregar_a=r.entregar_a,
                           destino=r.destino, direccion=r.direccion)
              for r in po_doc.om_entregas] if capturadas else calcular_entregas(po_doc))
    return {
        "indicar": bool(tiene and po_doc.get("om_indicar_entrega")),
        "editadas": capturadas,
        "filas": filas,
        "supplier": po_doc.supplier,
        "nombres": {p: frappe.db.get_value("Item", p, "item_name") or p
                    for p in {f.producto for f in filas if f.producto}},
    }


@frappe.whitelist()
def guardar_entregas(po: str, indicar=1, filas=None) -> dict:
    """Guarda la instrucción de entrega. ``filas`` None = volver a lo calculado del
    flujo (borra lo capturado). Se puede cambiar con la orden ya validada: es solo la
    indicación al taller, no toca importes ni inventario."""
    requiere_vista("preparacion", "talleres")
    po_doc = frappe.get_doc("Purchase Order", po)
    if po_doc.docstatus == 2:
        frappe.throw(_("La orden está cancelada."))
    if isinstance(filas, str):
        filas = json.loads(filas)
    po_doc.om_indicar_entrega = 1 if frappe.utils.cint(indicar) else 0
    po_doc.set("om_entregas", [])
    for f in filas or []:
        if not (f.get("destino") or f.get("entregar_a")):
            continue
        destino = f.get("destino") or frappe.db.get_value("Supplier", f.get("entregar_a"), "supplier_name")
        po_doc.append("om_entregas", {
            "producto": f.get("producto"), "piezas": f.get("piezas"),
            "entregar_a": f.get("entregar_a") or None, "destino": destino,
            "direccion": f.get("direccion"),
        })
    po_doc.flags.ignore_permissions = True
    po_doc.save()
    return get_entregas(po)


@frappe.whitelist()
def direccion_de_proveedor(supplier: str) -> dict:
    """Para la captura a mano: al cambiar el destino se propone su dirección."""
    return {
        "destino": frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier,
        "direccion": _direccion_proveedor(supplier),
    }


@frappe.whitelist()
def direcciones_destino(po: str, entregar_a: str = None) -> list:
    """Direcciones entre las que se puede elegir para un destino de la entrega: las del
    taller que recibe o, si va al almacén de Yelke, las de la compañía de la orden. Las
    que dicen exactamente lo mismo (envío y facturación con el mismo domicilio) salen
    una sola vez; la de envío primero."""
    if entregar_a:
        link_doctype, link_name = "Supplier", entregar_a
    else:
        link_doctype, link_name = "Company", frappe.db.get_value("Purchase Order", po, "company")
    filas = frappe.db.sql("""
        select a.name, a.address_type from tabAddress a
        join `tabDynamic Link` d on d.parent = a.name and d.parenttype = 'Address'
        where d.link_doctype = %s and d.link_name = %s and ifnull(a.disabled, 0) = 0
        order by a.is_shipping_address desc, a.address_type = 'Shipping' desc, a.is_primary_address desc, a.creation""",
        (link_doctype, link_name), as_dict=True)
    out, vistos = [], set()
    for f in filas:
        texto = _direccion_texto(f.name)
        if texto and texto not in vistos:
            vistos.add(texto)
            out.append({"name": f.name, "texto": texto})
    return out

