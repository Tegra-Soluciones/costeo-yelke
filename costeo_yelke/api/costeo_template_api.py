# -*- coding: utf-8 -*-
"""API de Plantillas de Costeo y refresco de precios.

Una "Plantilla de Costeo" es un Costeo marcado con ``es_plantilla = 1`` que guarda
la estructura reutilizable de UN SOLO producto (materiales y etapas), SIN cliente y
SIN precios envejecidos. Es deliberadamente "un producto por plantilla" -- no "un
costeo completo por plantilla" -- para poder combinar plantillas de distintos
productos al armar un costeo nuevo (ver create_costeo_from_templates): un costeo con
3 artículos guarda 3 plantillas independientes, cada una reutilizable por separado
o junto con cualquier otra, como si se agregaran al carrito.

Al crear un costeo nuevo se seleccionan una o más plantillas, se combinan sus
productos/materiales/etapas en un solo Costeo nuevo, y se refrescan los precios
desde las listas de compra vigentes.

El refresco replica la agregación del formulario (modules/90_calculations.js):
  - Total de fila T2 = (consumo / factor_conversion) * precio_unitario
  - material_cost  = suma de totales T2 con concept_type "Materia Prima"
  - services_cost  = suma de totales T2 "Servicio" + suma de precio_servicio de etapas (T3)
  - shipping_cost  = se conserva (captura manual)
  - base = material + servicios + envio; overhead = base * overhead_pct/100
  - total_unit_cost = base + overhead; precio_venta = total / (1 - margen)
"""

import json
import math

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

# ---------------------------------------------------------------------------
# Precios
# ---------------------------------------------------------------------------
def _get_buying_rate(item_code, supplier=None):
    """Mejor precio de compra conocido para un item.

    Prioridad: Item Price (buying) del proveedor -> Item Price (buying) cualquiera
    -> ultima tarifa de compra del Item.
    """
    if not item_code:
        return None

    if supplier:
        rows = frappe.get_all(
            "Item Price",
            filters={"item_code": item_code, "buying": 1, "supplier": supplier},
            fields=["price_list_rate"],
            order_by="valid_from desc, modified desc",
            limit=1,
        )
        if rows and rows[0].price_list_rate:
            return flt(rows[0].price_list_rate)

    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "buying": 1},
        fields=["price_list_rate"],
        order_by="valid_from desc, modified desc",
        limit=1,
    )
    if rows and rows[0].price_list_rate:
        return flt(rows[0].price_list_rate)

    last_rate = frappe.db.get_value("Item", item_code, "last_purchase_rate")
    return flt(last_rate) if last_rate else None


def _recompute_t2_row(row):
    qty = flt(row.internal_qty)
    factor = flt(row.conversion_factor) or 1
    price = flt(row.unit_price)

    supplier_qty = qty / factor if factor else 0
    row.supplier_qty = supplier_qty
    row.min_supplier_qty = math.ceil(supplier_qty) if supplier_qty else 0
    row.total = supplier_qty * price


def _recompute_aggregates(doc):
    detalles = doc.get("costeo_producto_detalle") or []
    etapas = doc.get("tabla_etapas_costeo") or []

    for prod in doc.get("costeo_producto") or []:
        finished = prod.finished_item
        material = 0.0
        services = 0.0

        for det in detalles:
            if det.finished_item != finished:
                continue
            concept = (det.concept_type or "").strip()
            if concept in ("Materia Prima", ""):
                material += flt(det.total)
            elif concept == "Servicio":
                services += flt(det.total)
            # "Envío" no se agrega: shipping_cost es captura manual.

        for etapa in etapas:
            if etapa.producto_terminado == finished and etapa.servicio and etapa.precio_servicio:
                # precio_servicio es el precio del LOTE completo si el proveedor cobra
                # por lote (ej. $19 por 25 confecciones, lote_qty=25) -- con lote_qty=1
                # (default) el precio ya es por pieza, igual que antes de este campo.
                services += flt(etapa.precio_servicio) / (flt(etapa.lote_qty) or 1)

        prod.material_cost = material
        prod.services_cost = services

        base = material + services + flt(prod.shipping_cost)
        prod.overhead_amt = base * (flt(prod.overhead_pct) / 100.0)
        prod.total_unit_cost = base + flt(prod.overhead_amt)

        margin = flt(prod.margin_pct) / 100.0
        if 0 <= margin < 1 and prod.total_unit_cost:
            prod.unit_sales_price = prod.total_unit_cost / (1 - margin)
        prod.total_sales_price = flt(prod.unit_sales_price) * flt(prod.qty)


def _refresh_costeo_prices(doc, only_missing=False):
    """Actualiza precios de materia prima (T2) y de maquila (T3) y recomputa agregados.

    ``only_missing`` = solo rellena precios en 0 (no pisa lo capturado a mano).
    Devuelve cuantos precios se actualizaron.
    """
    updated = 0

    for row in doc.get("costeo_producto_detalle") or []:
        if row.item:
            rate = _get_buying_rate(row.item, row.get("supplier"))
            if rate is not None and (not only_missing or not flt(row.unit_price)):
                row.unit_price = rate
                updated += 1
        _recompute_t2_row(row)

    for row in doc.get("tabla_etapas_costeo") or []:
        if row.servicio:
            rate = _get_buying_rate(row.servicio, row.get("proveedor"))
            if rate is not None and (not only_missing or not flt(row.precio_servicio)):
                row.precio_servicio = rate
                updated += 1

    _recompute_aggregates(doc)
    return updated


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_costeo_templates(company=None):
    """Lista de plantillas de costeo -- cada una es UN producto (ver docstring del
    módulo), así que se trae de una vez el renglón de costeo_producto para mostrar
    directo el artículo, su imagen y su costo unitario -- sin esto el SPA tendría
    que pedir cada plantilla completa solo para saber qué producto es. También trae
    el proyecto/cliente de origen (capturados una vez al crear la plantilla, ver
    save_as_template) para que 'Mis Plantillas' pueda mostrarlos y filtrar por ellos."""
    filters = {"es_plantilla": 1}
    if company:
        filters["compañia"] = company
    templates = frappe.get_all(
        "Costeo",
        filters=filters,
        fields=[
            "name", "nombre_plantilla", "familia_prenda", "compañia", "modified",
            "plantilla_origen_costeo", "plantilla_origen_titulo", "plantilla_origen_cliente",
        ],
        order_by="modified desc",
    )
    if not templates:
        return templates

    names = [t["name"] for t in templates]
    productos = frappe.get_all(
        "Costeo Producto",
        filters={"parent": ["in", names]},
        fields=["parent", "finished_item", "image", "description", "total_unit_cost"],
    )
    producto_por_costeo = {}
    for p in productos:
        producto_por_costeo.setdefault(p.parent, p)  # una plantilla = un producto; el primero basta

    clientes = {c for c in (t["plantilla_origen_cliente"] for t in templates) if c}
    nombre_por_cliente = {}
    if clientes:
        filas = frappe.get_all(
            "Customer", filters={"name": ["in", list(clientes)]},
            fields=["name", "customer_name", "nombre_comercial"],
        )
        nombre_por_cliente = {f.name: (f.nombre_comercial or f.customer_name) for f in filas}

    for tpl in templates:
        p = producto_por_costeo.get(tpl["name"])
        tpl["finished_item"] = p.finished_item if p else None
        tpl["image"] = p.image if p else None
        tpl["description"] = p.description if p else None
        tpl["total_unit_cost"] = p.total_unit_cost if p else 0
        cliente = tpl.get("plantilla_origen_cliente")
        tpl["origen_cliente_nombre"] = nombre_por_cliente.get(cliente, cliente) if cliente else None
    return templates


@frappe.whitelist()
def delete_template(name):
    """Elimina una plantilla."""
    if not frappe.db.get_value("Costeo", name, "es_plantilla"):
        frappe.throw(_("El documento {0} no es una plantilla.").format(name))
    frappe.delete_doc("Costeo", name, force=True, ignore_permissions=True)
    return {"ok": True}


def _child_row_dict(row):
    """Copia los datos de una fila hija (frappe._dict/Document) para pegarla en OTRO
    documento -- quita identidad (name/parent/parentfield/parenttype/idx/docstatus/
    creation/modified/owner/modified_by) para que Frappe la trate como una fila
    nueva propia, no como si todavía perteneciera al documento de origen."""
    IDENTITY = {"name", "parent", "parentfield", "parenttype", "idx", "docstatus",
                "creation", "modified", "owner", "modified_by", "doctype"}
    as_dict_fn = getattr(row, "as_dict", None)
    data = dict(as_dict_fn()) if callable(as_dict_fn) else dict(row)
    return {k: v for k, v in data.items() if k not in IDENTITY}


@frappe.whitelist()
def create_costeo_from_templates(templates, cliente, compania=None, fecha=None):
    """Crea UN Costeo nuevo combinando una o más plantillas (cada una es un solo
    producto, ver docstring del módulo) -- como armar un carrito: cada plantilla
    seleccionada aporta su propio producto, sus materiales y sus etapas al costeo
    nuevo, sin pisar lo que aportan las demás. Los precios se refrescan al final
    contra las listas de compra vigentes."""
    if isinstance(templates, str):
        templates = json.loads(templates)
    if not templates:
        frappe.throw(_("Selecciona al menos una plantilla."))

    new_doc = frappe.new_doc("Costeo")
    new_doc.es_plantilla = 0
    new_doc.cliente = cliente
    new_doc.compañia = compania or ""
    new_doc.fecha = fecha or nowdate()
    new_doc.costeo_status = "Borrador"

    for name in templates:
        tpl = frappe.get_doc("Costeo", name)
        if not cint(tpl.get("es_plantilla")):
            frappe.throw(_("El documento {0} no es una plantilla.").format(name))
        if not compania and tpl.get("compañia"):
            new_doc.compañia = tpl.get("compañia")

        for p in tpl.get("costeo_producto") or []:
            row = _child_row_dict(p)
            row["qty"] = row.get("qty") or 1  # la plantilla guarda 0; se arranca en 1
            new_doc.append("costeo_producto", row)
        for d in tpl.get("costeo_producto_detalle") or []:
            new_doc.append("costeo_producto_detalle", _child_row_dict(d))
        for e in tpl.get("tabla_etapas_costeo") or []:
            new_doc.append("tabla_etapas_costeo", _child_row_dict(e))
        for m in tpl.get("tabla_materiales_etapa") or []:
            new_doc.append("tabla_materiales_etapa", _child_row_dict(m))
        for t in tpl.get("tabla_tallas_costeo") or []:
            new_doc.append("tabla_tallas_costeo", _child_row_dict(t))

    _refresh_costeo_prices(new_doc)

    new_doc.flags.ignore_permissions = True
    new_doc.flags.ignore_mandatory = True
    new_doc.insert()
    return {"name": new_doc.name, "cliente": cliente}


def _sync_templates_from_costeo(doc):
    """Crea o ACTUALIZA (upsert) una plantilla por cada producto de `doc` -- si ya
    existe una plantilla de un producto para este mismo costeo de origen, se
    actualiza en su lugar en vez de duplicarla. Esto es lo que permite que el
    guardado automático (ver Costeo.on_update, casilla 'guardar_como_plantilla')
    corra en CADA guardado del Costeo sin ir generando plantillas repetidas; el
    botón manual 'Guardar como Plantilla' (save_as_template) usa el mismo mecanismo."""
    productos = doc.get("costeo_producto") or []
    if not productos:
        return []

    etapas_por_producto = {}
    for e in doc.get("tabla_etapas_costeo") or []:
        etapas_por_producto.setdefault(e.producto_terminado, []).append(e)

    # Plantillas que YA existen para este mismo costeo de origen -- se actualizan
    # en vez de duplicarse. Indexadas por el producto que contienen (una plantilla
    # = un producto, así que un solo Costeo Producto por plantilla basta).
    existentes = frappe.get_all(
        "Costeo", filters={"es_plantilla": 1, "plantilla_origen_costeo": doc.name}, pluck="name",
    )
    tpl_por_producto = {}
    if existentes:
        filas = frappe.get_all(
            "Costeo Producto", filters={"parent": ["in", existentes]}, fields=["parent", "finished_item"],
        )
        tpl_por_producto = {f.finished_item: f.parent for f in filas}

    resultado = []
    for prod in productos:
        finished = prod.finished_item
        if not finished:
            continue

        etapas = etapas_por_producto.get(finished, [])
        stage_keys = {e.get("stage_id") for e in etapas if e.get("stage_id")}

        existing_name = tpl_por_producto.get(finished)
        tpl = frappe.get_doc("Costeo", existing_name) if existing_name else frappe.new_doc("Costeo")
        tpl.es_plantilla = 1
        tpl.nombre_plantilla = finished
        tpl.cliente = None
        tpl.compañia = doc.get("compañia")
        tpl.costeo_status = "Borrador"
        # De dónde salió -- se captura/refresca aquí para que "Mis Plantillas"
        # pueda mostrar en qué proyecto se usó y filtrar por cliente/proyecto.
        tpl.plantilla_origen_costeo = doc.name
        tpl.plantilla_origen_titulo = doc.get("titulo") or doc.name
        tpl.plantilla_origen_cliente = doc.get("cliente")

        tpl.set("costeo_producto", [])
        prod_row = _child_row_dict(prod)
        prod_row["qty"] = 0  # la cantidad es de cada pedido, no de la plantilla
        tpl.append("costeo_producto", prod_row)

        tpl.set("costeo_producto_detalle", [])
        for d in doc.get("costeo_producto_detalle") or []:
            if d.finished_item == finished:
                tpl.append("costeo_producto_detalle", _child_row_dict(d))

        tpl.set("tabla_etapas_costeo", [])
        for e in etapas:
            tpl.append("tabla_etapas_costeo", _child_row_dict(e))

        tpl.set("tabla_materiales_etapa", [])
        for m in doc.get("tabla_materiales_etapa") or []:
            if m.get("stage_id") in stage_keys:
                tpl.append("tabla_materiales_etapa", _child_row_dict(m))

        tpl.set("tabla_tallas_costeo", [])
        for t in doc.get("tabla_tallas_costeo") or []:
            if t.finished_item == finished:
                tpl.append("tabla_tallas_costeo", _child_row_dict(t))

        tpl.flags.ignore_permissions = True
        tpl.flags.ignore_mandatory = True
        tpl.save() if existing_name else tpl.insert()
        resultado.append({"name": tpl.name, "nombre": tpl.nombre_plantilla})

    return resultado


@frappe.whitelist()
def save_as_template(costeo):
    """Guarda (o actualiza) cada producto del Costeo como su PROPIA plantilla
    independiente (ver docstring del módulo) -- un costeo con 3 artículos genera 3
    plantillas, cada una reutilizable sola o combinada con cualquier otra. El
    nombre de cada plantilla es el propio artículo; no hace falta capturar nada
    aparte. Es el botón manual del mismo mecanismo que corre solo al guardar un
    Costeo con la casilla 'guardar_como_plantilla' marcada (ver Costeo.on_update)."""
    src = frappe.get_doc("Costeo", costeo)
    if not src.get("costeo_producto"):
        frappe.throw(_("Este costeo no tiene productos que guardar como plantilla."))
    return {"creadas": _sync_templates_from_costeo(src)}


@frappe.whitelist()
def refresh_costeo_prices(costeo, only_missing=0):
    """Refresca precios de un Costeo existente contra las listas de compra vigentes."""
    doc = frappe.get_doc("Costeo", costeo)
    updated = _refresh_costeo_prices(doc, only_missing=cint(only_missing))
    doc.flags.ignore_permissions = True
    doc.save()
    return {"ok": True, "updated": updated, "costeo": doc.name}
