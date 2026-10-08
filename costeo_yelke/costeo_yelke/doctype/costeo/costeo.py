# -*- coding: utf-8 -*-
# Copyright (c) 2025, Tu Empresa and contributors
# For license information, please see license.txt

import json
import math
import re
import unicodedata

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, nowdate

PP_SIMPLE_FIELDS = [
    "naming_series",
    "company",
    "get_items_from",
    "posting_date",
    "item_code",
    "customer",
    "warehouse",
    "project",
    "sales_order_status",
    "from_date",
    "to_date",
    "from_delivery_date",
    "to_delivery_date",
    "combine_items",
    "combine_sub_items",
    "sub_assembly_warehouse",
    "skip_available_sub_assembly_item",
    "include_non_stock_items",
    "include_subcontracted_items",
    "consider_minimum_order_qty",
    "include_safety_stock",
    "ignore_existing_ordered_qty",
    "for_warehouse",
    "status",
    "amended_from",
]

PP_TABLE_DOCTYPES = {
    "sales_orders": "Production Plan Sales Order",
    "material_requests": "Production Plan Material Request",
    "po_items": "Production Plan Item",
    "prod_plan_references": "Production Plan Item Reference",
    "sub_assembly_items": "Production Plan Sub Assembly Item",
    "mr_items": "Material Request Plan Item",
    "warehouses": "Production Plan Material Request Warehouse",
}


def _build_costeo_customer_token(customer):
    if not customer:
        return "SINCLIENTE"

    customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
    normalized_name = "".join(
        ch for ch in unicodedata.normalize("NFD", (customer_name or "").upper()) if unicodedata.category(ch) != "Mn"
    )
    token = re.sub(r"[^A-Za-z0-9]+", "-", normalized_name).strip("-")

    if not token:
        token = re.sub(r"[^A-Za-z0-9]+", "-", (customer or "").upper()).strip("-")

    return (token or "SINCLIENTE")[:16]


class Costeo(Document):
    def autoname(self):
        if cint(self.get("es_plantilla")):
            # Cada plantilla es UN producto (ver costeo_template_api.py) -- se nombra
            # por su propio artículo (nombre_plantilla); familia_prenda queda solo
            # como respaldo por si alguna plantilla vieja no tuviera nombre_plantilla.
            base = self.get("nombre_plantilla") or self.get("familia_prenda") or ""
            token = "".join(
                ch for ch in unicodedata.normalize("NFD", base.upper()) if unicodedata.category(ch) != "Mn"
            )
            token = re.sub(r"[^A-Za-z0-9]+", "-", token).strip("-") or "GENERAL"
            self.name = make_autoname(f"PLANTILLA-{token[:16]}-.####", doc=self)
            return

        customer_token = _build_costeo_customer_token(self.cliente)
        self.name = make_autoname(f"CST-{customer_token}-.YYYY.-.#####", doc=self)

    def validate(self):
        # Ningún campo obligatorio se checa aquí -- validate() corre en CADA guardado
        # (borrador incluido) y un Costeo a medio capturar debe poderse guardar tal
        # cual. Lo obligatorio se exige solo al validar (enviar), ver before_submit.
        self.cleanup_orphan_children()

    def before_submit(self):
        """Aquí sí se exige todo lo obligatorio -- 'antes solo lo checaba el SPA
        (CosteoDetailPage.vue validate()), así que Validar desde Desk o por API
        directa no pedía nada. Guardar un borrador incompleto sigue permitido
        (validate() ya no lo bloquea); solo pasar a Validado lo exige."""
        faltantes = []
        if not self.get("cliente"):
            faltantes.append(_("Cliente"))
        if not self.get("fecha"):
            faltantes.append(_("Fecha"))
        if not self.get("compañia"):
            faltantes.append(_("Compañía"))
        if not self.get("centro_de_costos"):
            faltantes.append(_("Centro de costos"))
        if not self.get("almacen_materias_primas"):
            faltantes.append(_("Almacén de materias primas"))
        if not self.get("almacen_trabajo_en_proceso"):
            faltantes.append(_("Almacén de trabajo en proceso"))
        if faltantes:
            frappe.throw(
                _("Faltan datos obligatorios para validar el Costeo: {0}.").format(", ".join(faltantes))
            )
        self.validate_at_least_one_product_to_produce()

    def on_submit(self):
        # Al validar (docstatus 0 -> 1) es cuando se decide si este Costeo deja o
        # no una plantilla -- ver sync_templates_if_enabled.
        self.sync_templates_if_enabled()

    def on_update_after_submit(self):
        # Costeo ya validado (docstatus 1): un guardado posterior ahí no dispara
        # on_update sino este método -- sin este segundo gancho, editar un Costeo
        # ya validado nunca actualizaría sus plantillas.
        self.sync_templates_if_enabled()

    def sync_templates_if_enabled(self):
        """Deliberadamente NO corre en cada guardado de borrador (on_update) -- solo
        al Validar (on_submit) y en guardados posteriores a la Validación
        (on_update_after_submit). Mientras el Costeo sigue en borrador, marcar y
        desmarcar la casilla 'guardar_como_plantilla' y guardar no hace nada: ni
        crea ni borra plantillas -- para eso hay que Validar. Esto evita que un
        guardado de borrador a medio capturar (o repetido, mientras se sigue
        editando) genere/borre plantillas de más.

        Si esto es un Costeo real (no una plantilla) y trae marcada la casilla,
        cada uno de sus productos se guarda/actualiza como su propia plantilla
        (ver costeo_template_api._sync_templates_from_costeo -- upsert por
        producto, así que validar/guardar varias veces no genera duplicados). Si
        la casilla está desmarcada, se borran las plantillas que este Costeo haya
        generado antes (si las hay), para que "desmarcar y guardar" signifique de
        verdad "esto ya no es una plantilla"."""
        if self.get("es_plantilla"):
            return
        if not cint(self.get("guardar_como_plantilla")):
            self._eliminar_plantillas_generadas()
            return
        from costeo_yelke.api.costeo_template_api import _sync_templates_from_costeo

        _sync_templates_from_costeo(self)

    def _eliminar_plantillas_generadas(self):
        huerfanas = frappe.get_all(
            "Costeo", filters={"es_plantilla": 1, "plantilla_origen_costeo": self.name}, pluck="name",
        )
        for nombre in huerfanas:
            frappe.delete_doc("Costeo", nombre, force=True, ignore_permissions=True)

    def validate_at_least_one_product_to_produce(self):
        # Las plantillas no llevan cantidad (es específica de cada pedido).
        if self.get("es_plantilla"):
            return
        has_products = any(
            row.finished_item and flt(row.qty) > 0 for row in (self.get("costeo_producto") or [])
        )

        if not has_products:
            frappe.throw(
                _(
                    "Debes capturar al menos un producto terminado con cantidad a producir mayor a 0 para guardar el Costeo."
                )
            )

    def cleanup_orphan_children(self):
        """Eliminar filas huerfanas cuando se elimina un producto terminado."""
        valid_items = {row.finished_item for row in (self.get("costeo_producto") or []) if row.finished_item}

        if self.get("costeo_producto_detalle"):
            self.set(
                "costeo_producto_detalle",
                [d for d in self.get("costeo_producto_detalle") if d.finished_item in valid_items],
            )

        if self.get("tabla_etapas_costeo"):
            self.set(
                "tabla_etapas_costeo",
                [e for e in self.get("tabla_etapas_costeo") if e.producto_terminado in valid_items],
            )

        if self.get("tabla_tallas_costeo"):
            self.set(
                "tabla_tallas_costeo",
                [t for t in self.get("tabla_tallas_costeo") if t.finished_item in valid_items],
            )

        # Reparto de materiales por etapa: se liga por material_id/stage_id, no por
        # producto, así que al borrar un producto (o una variante de talla) sus filas
        # quedaban apuntando a materiales/etapas que ya no existen.
        if self.get("tabla_materiales_etapa"):
            mats = {d.material_id for d in (self.get("costeo_producto_detalle") or []) if d.material_id}
            etapas = {e.stage_id for e in (self.get("tabla_etapas_costeo") or []) if e.stage_id}
            self.set(
                "tabla_materiales_etapa",
                [r for r in self.get("tabla_materiales_etapa") if r.material_id in mats and r.stage_id in etapas],
            )


def _as_dict(doc):
    if isinstance(doc, str):
        doc = json.loads(doc)
    elif isinstance(doc, Document):
        doc = doc.as_dict()
    return frappe._dict(doc or {})


def _clean_outbound_row(row):
    data = row.as_dict() if hasattr(row, "as_dict") else frappe._dict(row)
    return {
        k: v
        for k, v in data.items()
        if not str(k).startswith("__")
        and k
        not in {
            "name",
            "idx",
            "doctype",
            "parent",
            "parenttype",
            "parentfield",
            "docstatus",
            "creation",
            "modified",
            "modified_by",
            "owner",
        }
    }


def _serialize_table(rows):
    return [_clean_outbound_row(row) for row in (rows or [])]


def _clean_inbound_row(row, child_doctype):
    data = frappe._dict(row or {})
    valid_columns = set(frappe.get_meta(child_doctype).get_valid_columns()) | {"name", "idx", "doctype"}
    cleaned = {}

    for key, value in data.items():
        if str(key).startswith("__"):
            continue
        if key in {"parent", "parenttype", "parentfield", "docstatus"}:
            continue
        if key in valid_columns:
            cleaned[key] = value

    cleaned["doctype"] = child_doctype
    return cleaned


def _build_production_plan_from_costeo(doc):
    source = _as_dict(doc)
    pp = frappe.new_doc("Production Plan")

    for fieldname in PP_SIMPLE_FIELDS:
        if source.get(fieldname) is not None:
            pp.set(fieldname, source.get(fieldname))

    # Mirror main Costeo headers when the PP section is empty.
    if not pp.get("company") and source.get("compañia"):
        pp.company = source.get("compañia")

    if not pp.get("posting_date"):
        pp.posting_date = source.get("fecha") or nowdate()

    if not pp.get("customer") and source.get("cliente"):
        pp.customer = source.get("cliente")

    if not pp.get("project") and source.get("proyecto"):
        pp.project = source.get("proyecto")

    if not pp.get("get_items_from"):
        pp.get_items_from = "Sales Order"

    if source.get("include_non_stock_items") is None:
        pp.include_non_stock_items = 1

    if source.get("include_subcontracted_items") is None:
        pp.include_subcontracted_items = 1

    for table_field, child_doctype in PP_TABLE_DOCTYPES.items():
        pp.set(table_field, [])
        for row in source.get(table_field) or []:
            pp.append(table_field, _clean_inbound_row(row, child_doctype))

    return pp


@frappe.whitelist()
def pp_get_open_sales_orders(doc):
    pp = _build_production_plan_from_costeo(doc)
    pp.get_open_sales_orders()
    return {"sales_orders": _serialize_table(pp.get("sales_orders"))}


@frappe.whitelist()
def pp_get_pending_material_requests(doc):
    pp = _build_production_plan_from_costeo(doc)
    pp.get_pending_material_requests()
    return {"material_requests": _serialize_table(pp.get("material_requests"))}


@frappe.whitelist()
def pp_get_items(doc):
    pp = _build_production_plan_from_costeo(doc)
    pp.get_items()
    return {
        "po_items": _serialize_table(pp.get("po_items")),
        "prod_plan_references": _serialize_table(pp.get("prod_plan_references")),
    }


@frappe.whitelist()
def pp_combine_so_items(doc):
    pp = _build_production_plan_from_costeo(doc)
    pp.combine_so_items()
    return {
        "po_items": _serialize_table(pp.get("po_items")),
        "prod_plan_references": _serialize_table(pp.get("prod_plan_references")),
    }


@frappe.whitelist()
def pp_get_sub_assembly_items(doc, manufacturing_type=None):
    pp = _build_production_plan_from_costeo(doc)
    pp.get_sub_assembly_items(manufacturing_type=manufacturing_type)
    return {"sub_assembly_items": _serialize_table(pp.get("sub_assembly_items"))}


@frappe.whitelist()
def pp_validate_sales_order(doc, sales_order):
    pp = _build_production_plan_from_costeo(doc)
    pp.validate_sales_orders(sales_order=sales_order)
    return {"ok": True}


@frappe.whitelist()
def pp_make_material_request(doc, submit=0):
    source = _as_dict(doc)
    pp = _build_production_plan_from_costeo(source)
    pp.submit_material_request = cint(submit)
    _set_suppliers_on_pp_mr_items(pp, source)
    _make_material_request_with_suppliers(pp)
    return {"ok": True}


@frappe.whitelist()
def pp_make_work_orders(doc):
    from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse

    pp = _build_production_plan_from_costeo(doc)
    work_orders = []
    subcontract_candidates = {}
    default_warehouses = get_default_warehouse()

    pp.make_work_order_for_finished_goods(work_orders, default_warehouses)
    pp.make_work_order_for_subassembly_items(work_orders, subcontract_candidates, default_warehouses)
    pp.show_list_created_message("Work Order", work_orders)

    if not work_orders:
        frappe.msgprint(_("No Work Orders were created"))

    return {"work_orders": work_orders}


def _get_company_name(source):
    """"compañia" es el campo real que se captura en el Costeo -- "company" es un
    campo heredado (arrastrado de cuando el Costeo embebía directo los campos de
    Production Plan) que Frappe autorellena solo con la compañía default global en
    cuanto se crea el documento, sin que nadie lo haya elegido. En cualquier costeo
    de una compañía DISTINTA a esa default, "company" queda con el valor equivocado
    mientras "compañia" (y los almacenes que de ahí se derivan) sí tienen el
    correcto -- eso hacía que crear_pos_subcontratacion armara la OC de
    subcontratación bajo la compañía equivocada y reventara con
    'Warehouse ... does not belong to company ...' en cuanto el almacén de destino
    era de la compañía real."""
    return source.get("compañia") or source.get("company")


def _normalize_label(value):
    text = (value or "").strip().lower()
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def _is_raw_material_concept(value):
    normalized = _normalize_label(value)
    return normalized in {"materia prima", "materiaprima"}


def _build_raw_material_supplier_map(source):
    supplier_map = {}
    for row in source.get("costeo_producto_detalle") or []:
        item_code = row.get("item")
        supplier = row.get("supplier")
        concept_type = row.get("concept_type")

        if not item_code or not supplier:
            continue
        if not _is_raw_material_concept(concept_type):
            continue
        if item_code not in supplier_map:
            supplier_map[item_code] = supplier

    return supplier_map


def _set_suppliers_on_pp_mr_items(pp, source):
    if not frappe.db.has_column("Material Request Plan Item", "supplier"):
        return

    supplier_map = _build_raw_material_supplier_map(source)
    if not supplier_map:
        return

    for row in pp.get("mr_items") or []:
        supplier = supplier_map.get(row.get("item_code"))
        if supplier:
            row.supplier = supplier


def _make_material_request_with_suppliers(pp):
    """Replica ProductionPlan.make_material_request, incluyendo proveedor por fila cuando existe custom field."""
    material_request_list = []
    material_request_map = {}
    has_mr_item_supplier = frappe.db.has_column("Material Request Item", "supplier")

    for item in pp.get("mr_items") or []:
        if not item.item_code:
            continue

        item_doc = frappe.get_cached_doc("Item", item.item_code)
        material_request_type = item.material_request_type or item_doc.default_material_request_type

        key = "{}:{}:{}".format(item.sales_order, material_request_type, item_doc.customer or "")
        schedule_date = item.schedule_date or add_days(nowdate(), cint(item_doc.lead_time_days))

        if key not in material_request_map:
            material_request_map[key] = frappe.new_doc("Material Request")
            material_request = material_request_map[key]
            material_request.update(
                {
                    "transaction_date": nowdate(),
                    "status": "Draft",
                    "company": pp.company,
                    "material_request_type": material_request_type,
                    "customer": item_doc.customer or "",
                }
            )
            material_request_list.append(material_request)
        else:
            material_request = material_request_map[key]

        mr_item = {
            "item_code": item.item_code,
            "from_warehouse": item.from_warehouse if material_request_type == "Material Transfer" else None,
            "qty": item.quantity,
            "schedule_date": schedule_date,
            "warehouse": item.warehouse,
            "sales_order": item.sales_order,
            "production_plan": pp.name,
            "material_request_plan_item": item.name,
            "project": frappe.db.get_value("Sales Order", item.sales_order, "project") if item.sales_order else None,
        }

        if has_mr_item_supplier and item.get("supplier"):
            mr_item["supplier"] = item.get("supplier")

        material_request.append("items", mr_item)

    for material_request in material_request_list:
        material_request.flags.ignore_permissions = 1
        material_request.run_method("set_missing_values")
        material_request.save()

        if pp.get("submit_material_request"):
            material_request.submit()

    frappe.flags.mute_messages = False
    if material_request_list:
        links = [frappe.utils.get_link_to_form("Material Request", m.name) for m in material_request_list]
        frappe.msgprint(_("{0} created").format(", ".join(links)))
    else:
        frappe.msgprint(_("No material request created"))


def _stage_sort_key(row):
    value = row.get("etapa")
    try:
        return (0, int(value))
    except Exception:
        return (1, str(value or ""))


def _explode_stage_nodes(etapas):
    """Envuelve cada fila de etapa en un 'nodo' del grafo -- un frappe._dict con
    TODOS los campos de la etapa, más:
    - node_key: identifica a este nodo en el grafo (upstream/is_terminal/bom_item).
      Es el stage_id de la etapa.
    - parent_stage_key: igual al node_key -- se conserva como campo separado porque
      el resto del motor (member_stage_keys, atribución de materia prima) lo
      referencia por su propio nombre, no porque hoy pueda diferir de node_key.

    (Este módulo tuvo, hasta 2026-09, un concepto de "salidas múltiples" -- una
    etapa podía declarar varios resultados nombrados con reparto de costo/material
    por porcentaje. Se retiró: nunca tuvo UI de captura y no representaba bien el
    caso real -- una operación que reparte piezas a varios talleres en paralelo no
    es "un resultado dividido en fracciones", sino "el mismo resultado, entero,
    alimentando más de un camino siguiente". Ver _resolve_production_operations.)"""
    def as_plain_dict(row):
        # doc.tabla_etapas_costeo trae instancias reales de Document (no iterables
        # con dict(...)) cuando viene de frappe.get_doc; los callers que arman la
        # lista a mano (ej. _build_stage_subcontracting_rows) ya mandan frappe._dict.
        # as_dict() normaliza ambos casos sin perder ningún campo. OJO: no usar
        # hasattr() aquí -- frappe._dict.__getattr__ regresa None en vez de lanzar
        # AttributeError, así que hasattr(dict_de_frappe, "as_dict") da True igual.
        as_dict_fn = getattr(row, "as_dict", None)
        return dict(as_dict_fn()) if callable(as_dict_fn) else dict(row)

    nodes = []
    for e in etapas:
        parent_key = e.get("stage_id") or e.get("name") or e.get("etapa")
        node = as_plain_dict(e)
        node["node_key"] = parent_key
        node["parent_stage_key"] = parent_key
        nodes.append(frappe._dict(node))
    return nodes


def _resolve_stage_graph(etapas):
    """Resuelve las dependencias entre etapas de UN producto (lista de dicts/
    frappe._dict de Etapas Costeo). Regresa (info, ordered):

    - info: {node_key: {"row": node, "upstream": [nodes], "is_terminal": bool}}
      upstream = nodos de los que ESTE recibe material (vía 'recibe_de'). Se
      respeta EXACTAMENTE lo que 'recibe_de' traiga capturado -- sin reducción
      transitiva: si un paso marca que recibe de A y de B, y B a su vez recibe de
      A, las DOS referencias se conservan. No es una duplicación del mismo
      material -- es el caso real de un taller que reparte piezas de UNA misma
      pieza cortada a varios caminos en paralelo (una va a bordado, otra a
      colocación de cinta, otra se une directo), y el paso final necesita las
      piezas de AMBOS caminos MÁS la que le llega directo, cada una en la
      cantidad plena de la prenda -- no una fracción repartida entre ellas (ver
      _resolve_production_operations, "sin reducción transitiva").
      is_terminal = True si ningún otro nodo lo referencia como entrada -- ese es
      el que produce el PRODUCTO TERMINADO (puede haber procesos en paralelo que
      convergen en él, no solo una cadena de uno).
    - ordered: los mismos nodos en orden topológico (primero los que no dependen
      de nada), para que crear_boms_spa arme primero los BOM que otros van a
      referenciar.

    Modo lineal (fallback): si NINGUNA etapa del producto tiene 'recibe_de'
    capturado, se comporta EXACTAMENTE como antes de que existiera esta función --
    cadena estricta por número de etapa/nodo, cada uno recibe solo del inmediato
    anterior, el último es el terminal. Así los costeos ya existentes (todos,
    hasta que alguien empiece a usar ramas paralelas) no cambian de
    comportamiento."""
    etapas = list(etapas)
    nodes = _explode_stage_nodes(etapas)

    any_wired = any(str(e.get("recibe_de") or "").strip() for e in etapas)

    if not any_wired:
        ordered = sorted(nodes, key=_stage_sort_key)
        info = {}
        for i, n in enumerate(ordered):
            info[n["node_key"]] = {
                "row": n,
                "upstream": [ordered[i - 1]] if i > 0 else [],
                "is_terminal": i == len(ordered) - 1,
            }
        return info, ordered

    by_node_key = {n["node_key"]: n for n in nodes}
    by_parent_key = {}
    for n in nodes:
        by_parent_key.setdefault(n["parent_stage_key"], []).append(n)

    def resolve_token(token):
        if token in by_node_key:
            return by_node_key[token]
        siblings = by_parent_key.get(token)
        return siblings[0] if siblings else None

    upstream_map = {}
    consumed_keys = set()
    for n in nodes:
        deps = [d.strip() for d in str(n.get("recibe_de") or "").split(",") if d.strip()]
        rows = []
        for d in deps:
            resolved = resolve_token(d)
            if resolved is not None:
                rows.append(resolved)
                consumed_keys.add(resolved["node_key"])
        upstream_map[n["node_key"]] = rows

    info = {}
    for n in nodes:
        info[n["node_key"]] = {
            "row": n,
            "upstream": upstream_map[n["node_key"]],
            "is_terminal": n["node_key"] not in consumed_keys,
        }

    # Orden topológico (Kahn) -- si hay un ciclo o una referencia rota (dato mal
    # capturado), se agrega lo que quede al final en vez de tronar la generación.
    ordered, seen, remaining, guard = [], set(), list(nodes), 0
    while remaining and guard < 1000:
        guard += 1
        still_remaining, progressed = [], False
        for n in remaining:
            ups = info[n["node_key"]]["upstream"]
            if all(u["node_key"] in seen for u in ups):
                ordered.append(n)
                seen.add(n["node_key"])
                progressed = True
            else:
                still_remaining.append(n)
        remaining = still_remaining
        if not progressed:
            ordered.extend(remaining)
            break
    return info, ordered


_SLUG_STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "para", "con", "servicio", "servico"}


def _op_slug(servicios, supplier):
    """Etiqueta corta y legible para una operación con varios servicios:
    - prefijo común de los códigos (BORDADO-MANGA-* -> "bordado"), o
    - token significativo compartido por TODOS los servicios
      (CONFECCION-DE-CUELLO + SERVICIO-DE-CONFECCION -> "confeccion"), o
    - el proveedor como último recurso."""
    codes = [s.get("service_item") for s in servicios if s.get("service_item")]
    if codes:
        tok_lists = [[t for t in c.replace("_", "-").split("-") if t] for c in codes]
        # 1) prefijo común
        common_prefix = []
        for i in range(min(len(t) for t in tok_lists)):
            tok = tok_lists[0][i]
            if all(t[i] == tok for t in tok_lists):
                common_prefix.append(tok)
            else:
                break
        pref = [t.lower() for t in common_prefix if t.lower() not in _SLUG_STOPWORDS]
        if pref:
            return " ".join(pref[:2])
        # 2) token significativo compartido (el más largo)
        shared = set(t.lower() for t in tok_lists[0])
        for tl in tok_lists[1:]:
            shared &= set(t.lower() for t in tl)
        shared = [t for t in shared if t not in _SLUG_STOPWORDS and len(t) > 2]
        if shared:
            return max(shared, key=len)
    return (supplier or "operación").strip().lower()


def _resolve_production_operations(etapas, producto=None):
    """Envuelve ``_resolve_stage_graph`` fusionando las etapas del MISMO proveedor
    que ocupan el mismo punto del flujo -- en paralelo con el mismo origen, o en
    cadena A->B -- en UNA operación con varios servicios y UN resultado. Es lo que
    permite que "3 bordados del mismo taller" salgan como 3 renglones de servicio en
    una sola OC contra una sola pieza, sin 3 sub-ensamblajes intermedios.

    IMPORTANTE -- sin reducción transitiva: si una operación recibe de A y de B, y
    B a su vez recibe de A, las DOS entradas de upstream_keys se conservan tal
    cual se capturaron, cada una aportando la pieza COMPLETA (no una fracción).
    Antes (hasta 2026-09) este motor podaba automáticamente el vínculo "redundante"
    (A), asumiendo que ya llegaba de sobra vía B -- eso rompía el caso real de un
    corte que reparte piezas de una prenda a varios talleres en paralelo (una va a
    bordado, otra a colocación de cinta, otra se une directo en el paso final): las
    1,494 prendas completas pasan por los tres caminos, nada se divide entre ellos.
    ``upstream_redundantes`` (ver más abajo) señala esos casos para que la UI de
    Flujo de Producción pueda avisar -- sin borrar nada solo.

    Regresa una lista de ``frappe._dict`` en orden topológico, cada uno:
        op_key              id estable (node_key del nodo ancla)
        producto_terminado
        supplier
        is_terminal         produce el producto terminado
        output_item         item que produce (sintético si fusiona 2+; el
                            subensamblaje del nodo si es 1; el producto si es terminal)
        servicios           [ {service_item, price, lote_qty, lote_uom, modo_precio,
                               operaciones_por_pieza, precio_por_operacion} ]
                            -- servicios con el MISMO service_item se colapsan en uno
                            con el precio sumado (ej. dos cortes "SERVICO-DE-CORTE" a
                            $3 -> un renglón a $6).
        upstream_keys       set de op_key de las operaciones de las que recibe, TAL
                            CUAL se capturó (sin podar)
        upstream_redundantes subconjunto de upstream_keys que también es alcanzable
                            vía OTRO de los mismos upstream_keys -- informativo, no
                            se usa para excluir nada de ningún BOM/OC
        member_stage_keys   set de stage_id de las etapas fusionadas (materia prima /
                            almacenes se leen por aquí)

    Si nada se fusiona -> exactamente una operación por nodo, con un solo servicio,
    comportamiento idéntico al de ``_resolve_stage_graph`` recorrido a mano."""
    info, ordered = _resolve_stage_graph(etapas)

    def _svc(node):
        return {
            "service_item": node.get("servicio"),
            "price": flt(node.get("precio_servicio")),
            "lote_qty": flt(node.get("lote_qty")) or 1,
            "lote_uom": node.get("lote_uom"),
            "modo_precio": node.get("modo_precio"),
            "operaciones_por_pieza": flt(node.get("operaciones_por_pieza")) or 1,
            "precio_por_operacion": flt(node.get("precio_por_operacion")),
            # stage_id propio -- para que la UI de Flujo de Producción pueda ofrecer
            # "separar este servicio" apuntando exactamente a ESTA fila, aunque haya
            # quedado fusionado con otras del mismo proveedor.
            "stage_id": node.get("stage_id"),
            "no_agrupar": bool(node.get("no_agrupar")),
        }

    ops = {}
    order = []
    for n in ordered:
        nk = n["node_key"]
        g = info[nk]
        ops[nk] = frappe._dict(
            op_key=nk,
            producto_terminado=n.get("producto_terminado") or producto,
            supplier=n.get("proveedor"),
            is_terminal=g["is_terminal"],
            servicios=[_svc(n)] if n.get("servicio") else [],
            upstream_keys={u["node_key"] for u in g["upstream"]},
            member_stage_keys={n.get("parent_stage_key") or nk},
            stage_subensamblajes=[n.get("subensamblaje") or ""],
            anchor_node=n,
            # "No agrupar" (ver doctype Etapas Costeo): la persona lo marca desde
            # Flujo de Producción para sacar ESTE servicio de la fusión automática
            # con otros del mismo proveedor+origen -- sin esto, dos servicios que
            # comparten proveedor y de dónde reciben SIEMPRE se fusionan en un solo
            # bloque, sin importar si en la vida real se pueden entregar por
            # separado. Un nodo marcado nunca absorbe ni es absorbido (ver el ciclo
            # de fusión más abajo); los demás siguen fusionándose entre sí como
            # siempre.
            no_agrupar=bool(n.get("no_agrupar")),
            output_item=None,
        )
        order.append(nk)

    def _downstream(k):
        return {k2 for k2, o in ops.items() if k in o.upstream_keys}

    def _absorb(dst, src):
        for s in src.servicios:
            same = next((x for x in dst.servicios if x["service_item"] == s["service_item"]), None)
            if same:
                same["price"] = flt(same["price"]) + flt(s["price"])
            else:
                dst.servicios.append(s)
        dst.member_stage_keys |= src.member_stage_keys
        dst.stage_subensamblajes += src.stage_subensamblajes
        for o in ops.values():
            if src.op_key in o.upstream_keys:
                o.upstream_keys.discard(src.op_key)
                if o.op_key != dst.op_key:
                    o.upstream_keys.add(dst.op_key)
        dst.upstream_keys |= {u for u in src.upstream_keys if u != dst.op_key}
        del ops[src.op_key]

    changed = True
    while changed:
        changed = False
        # cadena A -> B (mismo proveedor, B recibe sólo de A, A alimenta sólo a B)
        for k in list(ops):
            b = ops.get(k)
            if not b or not b.supplier or len(b.upstream_keys) != 1 or b.no_agrupar:
                continue
            a = ops.get(next(iter(b.upstream_keys)))
            if not a or a.is_terminal or a.supplier != b.supplier or a.no_agrupar:
                continue
            if a.producto_terminado != b.producto_terminado or _downstream(a.op_key) != {k}:
                continue
            term = b.is_terminal
            _absorb(a, b)
            a.is_terminal = term
            changed = True
            break
        if changed:
            continue
        # paralelas: mismo proveedor + mismo origen
        groups = {}
        for k, op in ops.items():
            if not op.supplier or op.no_agrupar:
                continue
            groups.setdefault((op.producto_terminado, op.supplier, frozenset(op.upstream_keys)), []).append(k)
        for members in groups.values():
            if len(members) < 2:
                continue
            anchor = ops[members[0]]
            term = any(ops[m].is_terminal for m in members)
            for m in members[1:]:
                _absorb(anchor, ops[m])
            anchor.is_terminal = term
            changed = True
            break

    # upstream_redundantes: SOLO informativo -- señala, para cada operación, cuáles
    # de sus upstream_keys directos también son alcanzables vía OTRO de sus propios
    # upstream_keys (ej. recibe de A y de B, y B también recibe de A). Ya NO se
    # quita nada de upstream_keys por esto -- ver docstring de la función. La UI de
    # Flujo de Producción usa esto para avisar ("¿seguro? ya te llega indirecto
    # vía...") y dejar que la persona decida, en vez de que el motor borre solo.
    def _upstream_de(key, visto=None):
        visto = visto if visto is not None else set()
        for u in ops.get(key, frappe._dict(upstream_keys=set())).upstream_keys:
            if u not in visto:
                visto.add(u)
                _upstream_de(u, visto)
        return visto

    for op in ops.values():
        directos = list(op.upstream_keys)
        redundantes = set()
        for a in directos:
            for b in directos:
                if a != b and a in _upstream_de(b):
                    redundantes.add(a)
        op.upstream_redundantes = redundantes

    # re-orden topológico
    remaining = list(ops.values())
    resolved, seen, guard = [], set(), 0
    while remaining and guard < 1000:
        guard += 1
        progressed = False
        still = []
        for op in remaining:
            if op.upstream_keys <= seen:
                resolved.append(op)
                seen.add(op.op_key)
                progressed = True
            else:
                still.append(op)
        remaining = still
        if not progressed:
            resolved.extend(remaining)
            break

    taken = set()
    for op in resolved:
        # Nombre SIEMPRE automático: "{producto} · {palabra del servicio}" -- el
        # usuario ya no lo edita, se generó tedio sin valor.
        if op.is_terminal:
            op.output_item = op.producto_terminado
        else:
            # En MAYÚSCULAS: este nombre sintético se usa como item_code de un Item
            # real (sub-ensamblaje) en cuanto se materializa, y el hook de
            # homologación (costeo_yelke.overrides.uppercase_master) fuerza
            # item_code a mayúsculas al crearlo -- si aquí se generara en minúsculas,
            # la próxima vez que se recalcule este mismo nombre (para buscar la OC/
            # Item ya creados) ya no haría match contra lo que quedó guardado.
            base = f"{op.producto_terminado} · {_op_slug(op.servicios, op.supplier)}".upper()
            name, i = base, 2
            while name in taken:
                name, i = f"{base} {i}", i + 1
            op.output_item = name
        taken.add(op.output_item)
    return resolved


# --------------------------------------------------------------------------- #
# Estados de pieza (ver plan "inventario por pieza")
#
# La ruta de producción NO pertenece a la etapa sino a cada PIEZA física: el
# frente pasa por corte -> reflejante -> bordado, la espalda solo por corte, y
# cada paso que TRANSFORMA una pieza produce un artículo semiterminado propio.
# Modelar una operación como un solo artículo (op.output_item) mete piezas
# distintas en un bote fungible, y de ahí salían la cantidad inflada de la OC
# raíz, el precio mal repartido y los BOM forzosamente 1:1.
# --------------------------------------------------------------------------- #

def _piezas_de_producto(source, producto):
    """Piezas declaradas (Costeo Sub Ensamblaje) de un producto, ya normalizadas.
    ``cantidad`` es cuántas de esa pieza lleva UNA prenda (2 puños, 1 frente)."""
    out = []
    for row in source.get("tabla_subensamblajes_costeo") or []:
        if (row.get("producto_terminado") or "") != producto:
            continue
        nombre = (row.get("nombre") or "").strip()
        if not nombre:
            continue
        out.append(
            frappe._dict(
                nombre=nombre,
                stage_ids={x.strip() for x in (row.get("stage_ids") or "").split(",") if x.strip()},
                cantidad=flt(row.get("multiplicador")) or 1.0,
            )
        )
    return out


def _slug_pieza(nombre):
    """Nombre de pieza normalizado para incrustarlo en un item_code.

    Se pasa a ASCII sin acentos ("Puños" -> PUNOS): el código de artículo viaja a
    reportes, exportaciones y documentos del proveedor, y ahí un carácter acentuado
    se presta a problemas de codificación. El nombre que ve la persona conserva su
    ortografía -- esto solo afecta la clave.

    MAYÚSCULAS por el mismo motivo que op.output_item (ver
    _resolve_production_operations): el hook de homologación fuerza item_code a
    mayúsculas al crear el Item, así que generarlo en minúsculas rompería el match
    la próxima vez que se recalcule el nombre."""
    base = unicodedata.normalize("NFKD", (nombre or "").strip())
    base = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"[^0-9A-Za-z]+", "-", base).strip("-").upper()


def _op_letras_candidatas(op):
    """Letras candidatas para el sufijo de estado de una operación, en orden de
    preferencia: la inicial de cada palabra significativa de su slug (corte -> C,
    'colocacion reflejante' -> C, R; bordado -> B) y luego las demás letras de la
    primera palabra, como respaldo ante colisiones."""
    palabras = [w for w in _op_slug(op.servicios, op.supplier).split() if w]
    cands = []
    for w in palabras:
        c = w[0].upper()
        if c not in cands:
            cands.append(c)
    for ch in (palabras[0][1:] if palabras else ""):
        c = ch.upper()
        if c.isalnum() and c not in cands:
            cands.append(c)
    return cands or ["X"]


def _sufijos_de_operacion(ops, rutas):
    """{op_key: letra} para armar los sufijos acumulados del item_code (FRENTE-C ->
    FRENTE-CR -> FRENTE-CRB).

    Dos operaciones pueden COMPARTIR letra mientras ninguna pieza pase por las dos:
    el item_code sigue siendo único porque lleva el nombre de la pieza (los bordados
    de manga derecha e izquierda son ambos "B", y dan MANGA-DER-CB y MANGA-IZQ-CB).
    Sin esa holgura, el segundo bordado tendría que caer a una letra arbitraria.

    Se asigna recorriendo ``ops`` en orden topológico, así que el resultado es
    determinista: el mismo flujo siempre produce los mismos nombres."""
    conflicto = {op.op_key: set() for op in ops}
    for ruta in rutas.values():
        for a in ruta:
            for b in ruta:
                if a != b and a in conflicto:
                    conflicto[a].add(b)

    asignada = {}
    for op in ops:
        if op.is_terminal:
            continue
        usadas = {asignada[o] for o in conflicto.get(op.op_key, ()) if o in asignada}
        candidatas = _op_letras_candidatas(op)
        letra = next((c for c in candidatas if c not in usadas), None)
        if letra is None:
            base, i = candidatas[0], 2
            while f"{base}{i}" in usadas:
                i += 1
            letra = f"{base}{i}"
        asignada[op.op_key] = letra
    return asignada


def _fg_items_de_operacion(op, ps):
    """Artículos resultantes de esta operación, UNO POR PIEZA -- son los renglones
    que va a tener su orden de subcontratación.

    ÚNICO lugar donde se decide, porque tienen que coincidir sí o sí la OC
    (_build_stage_subcontracting_rows), el Subcontracting BOM
    (crear_subcontracting_bom) y la resolución de paradas: si divergen, ERPNext no
    encuentra el BOM del servicio y la transferencia al taller se queda vacía.

    Un renglón por pieza es lo que permite avanzar cada una por su cuenta (mandar
    las mangas hoy y los frentes cuando estén). Antes había un KIT por operación,
    que forzaba al taller a entregar todo junto.

    - Operación terminal -> el producto terminado (una sola entrada).
    - Producto sin piezas declaradas -> el output_item de siempre (una sola entrada).
    """
    if op.is_terminal:
        return [op.output_item]
    salidas = ps.salidas_por_op.get(op.op_key) or []
    return [e.item for e in salidas] or [op.output_item]


def _resolve_piece_states(ops, piezas, producto_terminado):
    """Descompone las operaciones en ESTADOS DE PIEZA.

    Cada vez que una operación transforma una pieza sale un artículo propio, y su
    insumo es el estado ANTERIOR DE LA MISMA PIEZA -- no el de la operación anterior
    del flujo. Por eso una pieza que se brinca etapas (la espalda, que no pasa por
    reflejante) no necesita ningún caso especial: simplemente no tiene estado ahí y
    la siguiente operación toma el último que exista.

    SIN piezas declaradas regresa una pieza implícita única cuyo item es exactamente
    ``op.output_item`` de siempre, y cuyos insumos son los ``upstream_keys`` tal cual
    -- comportamiento idéntico al anterior para todo costeo que no use piezas.

    KIT: la OC de subcontratación de ERPNext admite UN solo artículo resultante por
    renglón, y el proveedor debe seguir viendo un renglón por servicio a precio por
    prenda (no el desglose interno de piezas). Así que una operación cuyo resultado
    natural NO es "una unidad por prenda" -- porque produce varias piezas, o una
    pieza que va 2 veces por prenda -- produce un KIT (un juego por prenda) que
    después se desarma en sus piezas con un Stock Entry de re-empaque. Una operación
    que produce exactamente una pieza ×1 no lleva kit: su pieza es el fg_item directo.

    Regresa un ``frappe._dict``:
        estados            [ {op_key, pieza, item, cantidad, insumos:[(item, qty)]} ]
                           en orden topológico, solo operaciones NO terminales
        salidas_por_op     {op_key: [estado, ...]}
        lineas_por_op      {op_key: [{service_item, pieza, item, cantidad,
                                      precio_unitario}]} -- los renglones de su OC
        finales            {pieza: item_code}  -- último estado de cada pieza
        cantidades         {pieza: cantidad por prenda}
        terminal_insumos   [(item, qty)] -- lo que consume el producto terminado
        hay_piezas         bool
        avisos             [str]
    """
    no_terminales = [op for op in ops if not op.is_terminal]
    terminal = next((op for op in ops if op.is_terminal), None)
    por_key = {op.op_key: op for op in ops}
    avisos = []

    # ---- Qué piezas pasa cada operación ----
    # La matriz (Costeo Sub Ensamblaje.stage_ids) se marca POR SERVICIO: cada
    # stage_id es una fila de Etapas Costeo, o sea un servicio concreto. Una pieza
    # pasa por una operación si marcó alguno de sus servicios.
    #
    # Ese grano es el que permite que un taller con varios servicios distintos viva
    # en UNA sola tarjeta y aun así se sepa cuál es de cuál pieza -- "bordado manga
    # der" lo marcó solo la manga derecha, así que su precio va íntegro ahí.
    if piezas:
        nombres = {p.nombre for p in piezas}
        piezas_de_op = {
            op.op_key: {p.nombre for p in piezas if p.stage_ids & op.member_stage_keys}
            for op in no_terminales
        }

        # Punto de ensamble: la primera operación intermedia donde ya se unieron
        # todas las piezas (ver _ops_prenda_armada). De ahí en adelante se trabaja
        # la prenda armada como una sola unidad, no pieza por pieza.
        ops_armada = _ops_prenda_armada(no_terminales, ops, piezas_de_op, avisos, producto_terminado)
        for k in ops_armada:
            piezas_de_op.pop(k, None)

        # Una operación intermedia sin NINGUNA pieza sería un paso que desaparece del
        # flujo (y cortaría la cadena de BOM). Se interpreta como "pasan todas" -- el
        # default más seguro -- pero se avisa, porque casi siempre falta una casilla.
        for op in no_terminales:
            if op.op_key in ops_armada:
                continue
            if not piezas_de_op[op.op_key]:
                avisos.append(
                    f'Ninguna pieza de "{producto_terminado}" está marcada en el paso '
                    f'"{_op_slug(op.servicios, op.supplier)}" -- se asume que pasan todas.'
                )
                piezas_de_op[op.op_key] = set(nombres)

        orden = {op.op_key: i for i, op in enumerate(no_terminales)}
        rutas = {
            p.nombre: sorted(
                [op.op_key for op in no_terminales if p.nombre in piezas_de_op.get(op.op_key, ())],
                key=lambda k: orden.get(k, 0),
            )
            for p in piezas
        }
        cantidades = {p.nombre: p.cantidad for p in piezas}
    else:
        # Pieza implícita: el producto entero recorre todas las operaciones. Su item
        # en cada paso es el output_item de siempre.
        rutas = {None: [op.op_key for op in no_terminales]}
        cantidades = {None: 1.0}
        ops_armada = []

    # La prenda armada cuenta como una ruta más para repartir letras: así sus pasos
    # no repiten letra entre sí (ARMADA-K -> ARMADA-KA).
    sufijos = _sufijos_de_operacion(ops, {**rutas, "__armada__": ops_armada}) if piezas else {}

    # ---- Estados, encadenando cada pieza consigo misma ----
    estados, salidas_por_op, finales = [], {}, {}
    estado_por_pieza_op = {}
    for nombre, ruta in rutas.items():
        anterior, acumulado = None, ""
        for op_key in ruta:
            if piezas:
                acumulado += sufijos.get(op_key, "?")
                item = f"{producto_terminado} · {_slug_pieza(nombre)}-{acumulado}"
            else:
                item = por_key[op_key].output_item
            # Con piezas, el insumo es el estado ANTERIOR DE ESTA MISMA PIEZA (su
            # propia ruta). Sin piezas NO hay cadena por pieza: cada operación toma
            # sus upstream_keys tal cual -- pueden ser varias (procesos en paralelo
            # que convergen) y no son necesariamente la operación anterior en el
            # orden topológico. Encadenar a ciegas aquí rompía el grafo real.
            if piezas and anterior:
                insumos = [(anterior, 1.0)]
            else:
                insumos = [
                    (por_key[u].output_item, 1.0)
                    for u in por_key[op_key].upstream_keys
                    if u in por_key
                ]
            est = frappe._dict(
                op_key=op_key,
                pieza=nombre,
                item=item,
                cantidad=cantidades.get(nombre, 1.0),
                insumos=insumos,
            )
            estados.append(est)
            salidas_por_op.setdefault(op_key, []).append(est)
            estado_por_pieza_op[(nombre, op_key)] = est
            anterior = item
        if anterior:
            finales[nombre] = anterior

    # ---- Prenda armada: un solo artículo por prenda desde el punto de ensamble ----
    # El primer paso consume la última versión de CADA pieza con su cantidad por
    # prenda (puños x2...); los siguientes, la prenda armada del paso anterior.
    # `pieza` va en None: no es ninguna pieza, y así no aparece como opción de
    # "qué pieza entrega" (ver costeo_api._parada_subensamblajes).
    armada_final = None
    if ops_armada:
        acumulado = ""
        for i, op_key in enumerate(ops_armada):
            acumulado += sufijos.get(op_key, "?")
            item = f"{producto_terminado} · ARMADA-{acumulado}"
            insumos = ([(finales[n], flt(cantidades.get(n, 1.0))) for n in sorted(finales)]
                       if i == 0 else [(armada_final, 1.0)])
            est = frappe._dict(op_key=op_key, pieza=None, item=item, cantidad=1.0,
                               insumos=insumos, armada=True)
            estados.append(est)
            salidas_por_op.setdefault(op_key, []).append(est)
            armada_final = item

    # Reordena los estados al orden topológico de operaciones (las rutas se armaron
    # pieza por pieza, así que venían agrupados por pieza).
    orden_op = {op.op_key: i for i, op in enumerate(no_terminales)}
    estados.sort(key=lambda e: (orden_op.get(e.op_key, 0), str(e.pieza or "")))

    # ---- Renglones de OC de cada operación: servicio × pieza con su precio ----
    # Un renglón por pieza, siempre (es lo que permite avanzar cada una por su
    # cuenta). Lo único que cambia es de dónde sale el precio:
    #
    #  - servicio que NOMBRA sus piezas en la matriz -> aplica solo a ésas
    #    (bordado manga der: la manga derecha, punto);
    #  - servicio que no nombra ninguna -> cubre todas las piezas de la operación.
    #
    # En ambos casos el precio del servicio se cobra UNA sola vez por prenda: va
    # completo en una pieza portadora y las demás van en $0 (ver abajo el porqué).
    # La suma sobre las piezas reproduce exacto el precio por prenda del costeo,
    # que es la condición que no se puede romper: es lo que el taller cobra.
    piezas_por_nombre = {p.nombre: set(p.stage_ids) for p in piezas} if piezas else {}
    lineas_por_op = {}
    for op in no_terminales:
        salidas = salidas_por_op.get(op.op_key) or []
        if not salidas:
            continue
        por_pieza = {e.pieza: e for e in salidas}
        servicios = [sv for sv in op.servicios if sv.get("service_item")]
        unidades = sum(flt(e.cantidad) for e in salidas) or 1.0

        # A qué piezas aplica CADA servicio: las que marcaron SU casilla en la
        # matriz (stage_ids es por servicio, no por tarjeta). Un servicio marcado
        # por una sola pieza le cobra su precio íntegro; uno marcado por varias
        # -- o por ninguna, que se interpreta como "cubre todas"-- lo reparte.
        por_servicio = {}
        for sv in servicios:
            sid = sv.get("stage_id")
            suyas = [e for e in salidas if sid and sid in (piezas_por_nombre.get(e.pieza) or set())]
            por_servicio[sv["service_item"]] = suyas or list(salidas)

        lineas = []
        for sv in servicios:
            suyas = por_servicio[sv["service_item"]]
            # El precio NO se reparte entre las piezas: viaja completo en UNA de
            # ellas y las demás van en $0. Repartirlo obliga a un precio unitario
            # como $5/7 = $0.714286, y `rate` en ERPNext tiene 2 decimales: se
            # guardaba $0.71 y sobre decenas de miles de unidades se perdían
            # cientos de pesos frente al costeo (medido: -$227.82 en una sola OC
            # de corte). Concentrarlo da el total exacto al centavo.
            #
            # Lo que el taller cobra no cambia -- el formato "Orden de Maquila"
            # agrupa por servicio y divide entre prendas, así que sigue leyendo
            # "7,494 × $5.00". Lo que sí cambia es la valuación del inventario
            # intermedio: la pieza portadora carga todo el costo del servicio y
            # las demás solo su material. Decisión del usuario (2026-09-30): a
            # Yelke le importa la valuación de materia prima y mermas, no la de
            # los sub-ensamblajes.
            portadora = min(suyas, key=lambda e: (flt(e.cantidad) or 1.0, e.pieza))
            c = flt(portadora.cantidad) or 1.0
            precio = flt(sv["price"]) / c
            if round(precio, 2) != round(precio, 6):
                # Solo pasa si NINGUNA pieza del servicio va 1 por prenda y el
                # precio no se divide en centavos exactos. Raro, pero hay que
                # verlo venir en vez de perder dinero en silencio.
                avisos.append(
                    _("El precio de «{0}» ({1}) no se divide en centavos exactos entre "
                      "las {2} unidades de «{3}»; la orden puede quedar con una "
                      "diferencia de centavos.").format(
                          sv["service_item"], flt(sv["price"]), c, portadora.pieza))
            for est in suyas:
                lineas.append(frappe._dict(
                    service_item=sv["service_item"], pieza=est.pieza, item=est.item,
                    cantidad=flt(est.cantidad) or 1.0,
                    precio_unitario=precio if est is portadora else 0.0))
        lineas_por_op[op.op_key] = lineas

    # ---- Lo que consume el producto terminado ----
    if armada_final:
        terminal_insumos = [(armada_final, 1.0)]
    elif piezas:
        terminal_insumos = [(finales[n], flt(cantidades.get(n, 1.0))) for n in sorted(finales)]
    elif terminal:
        terminal_insumos = [
            (por_key[u].output_item, 1.0) for u in terminal.upstream_keys if u in por_key
        ]
    else:
        terminal_insumos = []

    return frappe._dict(
        estados=estados,
        salidas_por_op=salidas_por_op,
        lineas_por_op=lineas_por_op,
        finales=finales,
        cantidades=cantidades,
        terminal_insumos=terminal_insumos,
        hay_piezas=bool(piezas),
        avisos=avisos,
        # Operaciones que trabajan la prenda ya armada, en orden; la primera es
        # donde se une todo (punto de ensamble). Vacía si se arma en la final.
        ops_armada=list(ops_armada),
        items_armada={e.item for e in estados if e.get("armada")},
    )


def _ops_prenda_armada(no_terminales, ops, piezas_de_op, avisos, producto_terminado):
    """Operaciones intermedias que trabajan la prenda YA ARMADA, en orden.

    Una operación es el punto de ensamble si es la PRIMERA (en orden topológico)
    que cumple las tres condiciones:
      1. ninguna pieza la marca (no es trabajo sobre una pieza en particular);
      2. después de ella ya no hay trabajo por pieza: ninguna operación marcada por
         alguna pieza queda aguas abajo;
      3. le llegan todas las piezas: la última operación de cada pieza está aguas
         arriba de ella en el flujo. Aguas arriba y no "recibe de" directo: el flujo
         por default es lineal (cada paso recibe del anterior) y la ruta real de cada
         pieza la da la matriz de piezas, no las flechas -- el forro se corta y llega
         a confección aunque confección "reciba de" bordado manga.
    Las intermedias que siguen (acabado, lavado...) también cumplen las tres, por
    eso cuenta solo la primera: ésa une, las demás reciben la prenda armada.

    Una operación sin piezas marcadas que tiene trabajo por pieza DESPUÉS no es un
    ensamble sino una casilla olvidada: se queda con el aviso de "pasan todas" de
    siempre. Sin ensamble intermedio regresa [] y la operación final arma, como
    siempre."""
    por_key = {op.op_key: op for op in ops}
    hijos = {k: set() for k in por_key}
    for op in ops:
        for u in op.upstream_keys:
            if u in hijos:
                hijos[u].add(op.op_key)
    memo = {}

    def abajo(k):
        if k not in memo:
            memo[k] = set()
            for h in hijos.get(k, ()):
                memo[k] |= {h} | abajo(h)
        return memo[k]

    marcadas = [op.op_key for op in no_terminales if piezas_de_op.get(op.op_key)]
    if not marcadas:
        return []
    ultima_de_pieza = {}
    for op in no_terminales:  # vienen en orden topológico
        for nombre in piezas_de_op.get(op.op_key) or ():
            ultima_de_pieza[nombre] = op.op_key

    # Primera operación sin piezas y sin trabajo por pieza después (condiciones 1 y 2).
    ensamble = next((
        op.op_key for op in no_terminales
        if not piezas_de_op.get(op.op_key)
        and not (abajo(op.op_key) & set(marcadas))
    ), None)
    if not ensamble:
        return []
    # Condición 3: si no le llegan todas, no se adivina -- se dice cuáles faltan y
    # la operación se queda como hoy ("pasan todas").
    faltan = sorted(n for n, u in ultima_de_pieza.items() if ensamble not in abajo(u))
    if faltan:
        op = por_key[ensamble]
        avisos.append(
            f'"{producto_terminado}": el paso "{_op_slug(op.servicios, op.supplier)}" parece ser donde '
            f'se arma la prenda, pero no le llega {", ".join(faltan)} -- conéctala(s) en "recibe de" '
            f'o márcala(s) en ese paso.'
        )
        return []

    despues = [op.op_key for op in no_terminales if op.op_key in abajo(ensamble)]
    cadena = [ensamble] + despues
    # La prenda armada es UNA: no puede estar en dos talleres a la vez.
    for a, b in zip(cadena, cadena[1:]):
        if b not in abajo(a):
            avisos.append(
                f'"{producto_terminado}": después de armar la prenda, los pasos deben ir uno '
                f'tras otro -- "{_op_slug(por_key[a].servicios, por_key[a].supplier)}" y '
                f'"{_op_slug(por_key[b].servicios, por_key[b].supplier)}" quedaron en paralelo.'
            )
            break
    return cadena


def _get_finished_qty_map(source):
    qty_map = {}
    for row in source.get("costeo_producto") or []:
        item = row.get("finished_item")
        if item:
            qty_map[item] = flt(row.get("qty")) or 1
    return qty_map


def _get_finished_goods_warehouse_map(source):
    warehouse_map = {}
    for row in source.get("po_items") or []:
        item_code = row.get("item_code")
        warehouse = row.get("warehouse")
        if item_code and warehouse and item_code not in warehouse_map:
            warehouse_map[item_code] = warehouse
    return warehouse_map


def _get_item_default_warehouse(item_code, company):
    if not item_code:
        return None

    if company:
        warehouse = frappe.db.get_value(
            "Item Default",
            {"parent": item_code, "company": company},
            "default_warehouse",
        )
        if warehouse:
            return warehouse

    return frappe.db.get_value("Item Default", {"parent": item_code}, "default_warehouse")


def _get_supplier_warehouse(company, supplier):
    if not company or not supplier:
        return None

    if not frappe.db.has_column("Warehouse", "proveedor_asociado"):
        return None

    existing = frappe.db.get_value(
        "Warehouse",
        {
            "company": company,
            "is_group": 0,
            "disabled": 0,
            "proveedor_asociado": supplier,
        },
        "name",
    )
    if existing:
        return existing

    # Nadie dio de alta un almacén para este proveedor todavía (pasa siempre la
    # PRIMERA vez que se subcontrata con él) -- antes esto se quedaba en None sin
    # avisar, y la Orden de Subcontratación tronaba más adelante con un error crudo
    # de "supplier_warehouse" obligatorio que no explicaba nada. Se crea aquí mismo,
    # como el resto de los almacenes que la app ya arma solos (materia prima,
    # trabajo en proceso, producto terminado).
    return _crear_almacen_proveedor(company, supplier)


def _crear_almacen_proveedor(company, supplier):
    root = frappe.db.get_value(
        "Warehouse",
        {"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]},
        "name",
    )
    nombre = frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier
    try:
        wh = frappe.new_doc("Warehouse")
        wh.warehouse_name = nombre
        wh.company = company
        if root:
            wh.parent_warehouse = root
        wh.proveedor_asociado = supplier
        wh.flags.ignore_permissions = True
        wh.insert()
        return wh.name
    except Exception:
        frappe.log_error(title="No se pudo crear el almacén del proveedor", message=frappe.get_traceback())
        return None


def _get_purchase_tax_template(company, supplier=None):
    if not company:
        return None

    # Plantilla según el tipo de proveedor (formal / con retención / informal): la
    # resuelve la Tax Rule nativa de ERPNext a partir de la categoría de impuesto del
    # proveedor. Sin regla aplicable (o sin proveedor) sigue la lógica de siempre.
    if supplier:
        from erpnext.accounts.party import set_taxes

        try:
            por_proveedor = set_taxes(
                supplier, "Supplier", nowdate(), company,
                tax_category=frappe.db.get_value("Supplier", supplier, "tax_category"),
            )
        except Exception:
            por_proveedor = None
        if por_proveedor and frappe.db.get_value(
            "Purchase Taxes and Charges Template", {"name": por_proveedor, "company": company, "disabled": 0}
        ):
            return por_proveedor

    template = frappe.db.get_value(
        "Purchase Taxes and Charges Template",
        {"company": company, "disabled": 0, "is_default": 1},
        "name",
    )
    if template:
        return template

    iva_templates = frappe.get_all(
        "Purchase Taxes and Charges Template",
        fields=["name"],
        filters={"company": company, "disabled": 0, "title": ["like", "%IVA%"]},
        limit=1,
    )
    if iva_templates:
        return iva_templates[0].name

    return frappe.db.get_value(
        "Purchase Taxes and Charges Template",
        {"company": company, "disabled": 0},
        "name",
    )


def _guess_finished_goods_warehouse(company):
    if not company:
        return None

    patterns = [
        "%Producto Terminado%",
        "%Productos Terminados%",
        "%Finished Goods%",
    ]

    for pattern in patterns:
        rows = frappe.get_all(
            "Warehouse",
            fields=["name"],
            filters={
                "company": company,
                "is_group": 0,
                "disabled": 0,
                "name": ["like", pattern],
            },
            limit=1,
        )
        if rows:
            return rows[0].name

    for pattern in patterns:
        rows = frappe.get_all(
            "Warehouse",
            fields=["name"],
            filters={
                "company": company,
                "is_group": 0,
                "disabled": 0,
                "warehouse_name": ["like", pattern],
            },
            limit=1,
        )
        if rows:
            return rows[0].name

    return None


def _get_subcontracting_bom_map(finished_goods):
    if not finished_goods:
        return {}

    rows = frappe.get_all(
        "Subcontracting BOM",
        fields=[
            "name",
            "finished_good",
            "finished_good_bom",
            "service_item",
            "service_item_uom",
            "conversion_factor",
            "is_active",
            "modified",
        ],
        filters={"finished_good": ["in", list(set(finished_goods))], "is_active": 1},
        order_by="modified desc",
    )

    bom_map = {}
    for row in rows:
        if row.finished_good not in bom_map:
            bom_map[row.finished_good] = frappe._dict(row)
    return bom_map


def _get_service_stock_uom(item_code):
    if not item_code:
        return None
    return frappe.db.get_value("Item", item_code, "stock_uom")


def _build_stage_subcontracting_rows(source, qty_map_override=None):
    """``qty_map_override``, si se manda, reemplaza el mapa producto->cantidad que por
    default sale del costeo completo (_get_finished_qty_map) -- lo usa
    plan_crear_subcontratacion para que la cantidad de cada etapa refleje la OV
    específica del plan (que puede diferir del costeo si es una réplica con otra
    cantidad), no el total histórico del costeo."""
    stage_rows = []
    qty_map = qty_map_override or _get_finished_qty_map(source)
    fg_warehouse_map = _get_finished_goods_warehouse_map(source)
    company = _get_company_name(source)

    wip_warehouse = (
        source.get("sub_assembly_warehouse")
        or source.get("almacen_trabajo_en_proceso")
        or source.get("for_warehouse")
    )
    default_schedule_date = source.get("posting_date") or source.get("fecha") or nowdate()

    etapas_por_producto = {}
    for row in source.get("tabla_etapas_costeo") or []:
        producto = row.get("producto_terminado")
        if producto:
            etapas_por_producto.setdefault(producto, []).append(frappe._dict(row))

    for producto_terminado, etapas in etapas_por_producto.items():
        if qty_map_override is not None and producto_terminado not in qty_map_override:
            # Con override (plan de una OV específica), un producto que no está en el
            # mapa simplemente no es parte de ESA OV -- se omite en vez de caer al
            # default de 1, que generaría una OC de subcontratación fantasma.
            continue
        fg_qty_base = qty_map.get(producto_terminado) or 1
        operaciones = _resolve_production_operations(etapas, producto_terminado)
        piezas = _piezas_de_producto(source, producto_terminado)
        piece_states = _resolve_piece_states(operaciones, piezas, producto_terminado)

        for op in operaciones:
            servicios = [s for s in op.servicios if s.get("service_item")]
            if not op.supplier or not servicios:
                continue

            if op.is_terminal:
                target_warehouse = (
                    fg_warehouse_map.get(producto_terminado)
                    or _get_item_default_warehouse(producto_terminado, company)
                    or _guess_finished_goods_warehouse(company)
                    or wip_warehouse
                )
            else:
                target_warehouse = None  # se resuelve por pieza más abajo

            salidas = piece_states.salidas_por_op.get(op.op_key) or []

            # ── Etapa terminal: produce el artículo vendible, no piezas ──
            if op.is_terminal:
                k = len(servicios)
                shares, acum = [], 0.0
                for i in range(k):
                    nv = fg_qty_base if i == k - 1 else round(fg_qty_base * (i + 1) / k, 6)
                    shares.append(round(nv - acum, 6))
                    acum = nv
                for i, svc in enumerate(servicios):
                    stage_rows.append(frappe._dict({
                        "producto_terminado": producto_terminado,
                        "op_key": op.op_key,
                        "supplier": op.supplier,
                        "service_item": svc["service_item"],
                        "service_price": flt(svc["price"]),
                        "finished_good": op.output_item,
                        "finished_good_qty": shares[i],
                        "fg_qty_total": fg_qty_base,
                        "num_servicios": k,
                        "is_root": not op.upstream_keys,
                        "target_warehouse": target_warehouse,
                        "schedule_date": default_schedule_date,
                        "piezas_prenda": 1.0,
                    }))
                continue

            # ── Etapas intermedias: un renglón por (servicio, pieza) ──
            # El precio de cada uno ya viene resuelto en _resolve_piece_states: el
            # servicio que nombra su pieza cobra íntegro, el que cubre varias se
            # reparte. Aquí solo se traduce a cantidades del lote.
            #
            # Si VARIOS servicios de la misma tarjeta tocan la MISMA pieza (corte y
            # fusionado del mismo taller sobre el cuello), sus renglones comparten
            # fg_item: igual que en la etapa final, cada uno lleva una PORCIÓN de la
            # pieza (num_servicios = k) para que ERPNext produzca la pieza una vez y
            # no k veces -- el servicio se sigue cobrando por la cantidad completa
            # (fg_qty_total). Sin esto la OC pedía 5,760 cuellos para 2,880 prendas.
            lineas_op = piece_states.lineas_por_op.get(op.op_key) or []
            k_por_item = {}
            for ln in lineas_op:
                k_por_item[ln.item] = k_por_item.get(ln.item, 0) + 1
            visto_por_item, acum_por_item = {}, {}
            for ln in lineas_op:
                total_pieza = fg_qty_base * flt(ln.cantidad)
                k = k_por_item[ln.item]
                i = visto_por_item.get(ln.item, 0)
                visto_por_item[ln.item] = i + 1
                nv = total_pieza if i == k - 1 else round(total_pieza * (i + 1) / k, 6)
                porcion = round(nv - acum_por_item.get(ln.item, 0.0), 6)
                acum_por_item[ln.item] = nv
                stage_rows.append(frappe._dict({
                    "producto_terminado": producto_terminado,
                    "op_key": op.op_key,
                    "supplier": op.supplier,
                    "service_item": ln.service_item,
                    "service_price": ln.precio_unitario,
                    "finished_good": ln.item,
                    "finished_good_qty": porcion,
                    "fg_qty_total": total_pieza,
                    "num_servicios": k,
                    "is_root": not op.upstream_keys,
                    "target_warehouse": wip_warehouse or _get_item_default_warehouse(
                        ln.item, company),
                    "schedule_date": default_schedule_date,
                    "piezas_prenda": flt(ln.cantidad) or 1.0,
                }))

    return stage_rows


def _create_subcontracting_pos_from_stages(source, stage_rows, sales_order=None):
    """``sales_order``, si se manda, se graba en 'sales_order' de cada línea de
    servicio (campo nativo de Purchase Order Item) -- es lo que permite después
    filtrar las OC de maquila por OV (get_produccion_docs, get_reporte_final), ya
    que Subcontracting Order no tiene ese campo y hereda todo de la OC que le dio
    origen.

    UNA Purchase Order por PROVEEDOR (no por etapa): todas las etapas del mismo
    producto que comparten proveedor entran como líneas separadas de la MISMA OC.

    Las etapas del mismo proveedor en el mismo punto del flujo se FUSIONAN antes
    (ver _resolve_production_operations): "3 servicios de bordado distintos, mismo
    bordador" son 3 líneas de servicio con SU PRECIO que apuntan al MISMO `fg_item`
    (la única pieza que se recibe). ``finished_good_qty`` de cada línea es 1/k de la
    pieza (k = nº de servicios) para que ERPNext produzca UNA pieza, no k, mientras
    que ``service_qty`` es la pieza ENTERA -- cada servicio se factura completo.
    `fg_item` es la clave de trazabilidad de aquí en adelante (_po_for_bom_item,
    _etapas_rows_for_po, sub_get_flujo, sub_crear_sco, _sub_qty_disponible_info),
    que colapsan por él las líneas que lo comparten. Un fg_item DISTINTO por línea
    (proveedor que hace 2 cosas en momentos distintos) sigue siendo pieza aparte."""
    company = _get_company_name(source)
    if not company:
        frappe.throw(_("Company is required to create Subcontracting Purchase Orders."))

    so_item_cache = {}
    def _sales_order_item(item_code):
        """La línea de la OV de ese producto, o None si no hay EXACTAMENTE una.

        Si el MISMO producto viene en VARIAS líneas de la orden de venta (pasó en
        YT-OV-2026-307: 8,137 pzas a un precio y 1 pza a otro), ninguna de ellas
        explica por sí sola la cantidad AGREGADA que lleva la OC. Antes se tomaba
        una cualquiera con `get_value` y ERPNext comparaba el total contra esa:
        8,138 > 8,137 y rebotaba el documento con "over limit by Qty 1.0", dejando
        la OC de subcontratación imposible de validar.

        Con varias líneas se deja vacío, igual que con los subensamblajes: el campo
        `sales_order` de la línea alcanza para ligar la OC a su OV."""
        if item_code not in so_item_cache:
            filas = frappe.get_all(
                "Sales Order Item", filters={"parent": sales_order, "item_code": item_code},
                pluck="name", limit=2,
            )
            so_item_cache[item_code] = filas[0] if len(filas) == 1 else None
        return so_item_cache[item_code]

    bom_map = _get_subcontracting_bom_map([row.finished_good for row in stage_rows])
    taxes_template = _get_purchase_tax_template(company)  # aviso de "sin plantilla" (abajo)

    # Agrupa por proveedor preservando el orden de aparición (Python 3.7+: dict
    # mantiene orden de inserción) -- así la primera etapa de cada proveedor decide
    # el orden de las OC creadas, determinista y fácil de seguir en los mensajes.
    grupos = {}
    for row in stage_rows:
        grupos.setdefault(row.supplier, []).append(row)

    purchase_orders = []
    # fg_item cuyo sales_order_item ya se asignó a una línea -- ver más abajo (una
    # operación terminal fusionada reparte el producto en k líneas de servicio, pero
    # solo una debe contar contra la Sales Order Item).
    _soi_ya_asignado = set()

    for supplier, rows in grupos.items():
        po = frappe.new_doc("Purchase Order")
        po.company = company
        po.supplier = supplier
        po.is_subcontracted = 1
        po.transaction_date = source.get("posting_date") or source.get("fecha") or nowdate()
        # Fecha/almacén por defecto del grupo: los de la PRIMERA etapa -- cada línea
        # de todos modos trae los suyos propios (schedule_date/warehouse a nivel de
        # renglón), esto solo alimenta el default del selector si alguien agrega una
        # línea a mano después.
        po.schedule_date = rows[0].schedule_date or nowdate()

        supplier_warehouse = _get_supplier_warehouse(company, supplier)
        if supplier_warehouse:
            po.supplier_warehouse = supplier_warehouse

        # Sin esto, set_missing_values() cae al almacén por defecto de la compañía
        # (normalmente "Sucursales") en vez del almacén de destino real de la etapa
        # (WIP para etapas intermedias, Productos Terminados para la última) --
        # "Almacén (aceptado)" en el SPA mostraba ese default en vez del correcto.
        po.set_warehouse = rows[0].target_warehouse

        plantilla_proveedor = _get_purchase_tax_template(company, supplier)
        if plantilla_proveedor:
            po.taxes_and_charges = plantilla_proveedor

        rates_esperados = []  # por índice de renglón; se reimpone tras set_missing_values
        for row in rows:
            if not row.finished_good:
                frappe.throw(
                    _("Stage {0} for product {1} has no finished good configured.").format(
                        row.get("op_key") or "?", row.producto_terminado
                    )
                )

            if not row.target_warehouse:
                frappe.throw(
                    _(
                        "Stage {0} for product {1} has no destination warehouse. "
                        "Configure warehouse in Production Plan item or Item Defaults."
                    ).format(row.etapa or "?", row.producto_terminado)
                )

            bom_data = bom_map.get(row.finished_good)
            service_item = row.service_item or (bom_data.service_item if bom_data else None)
            if not service_item:
                frappe.throw(
                    _("No service item found for stage {0} and finished good {1}.").format(
                        row.get("op_key") or "?", row.finished_good
                    )
                )

            conversion_factor = flt(bom_data.conversion_factor) if bom_data else 1
            conversion_factor = conversion_factor or 1
            fg_qty = flt(row.finished_good_qty) or 1
            if flt(row.get("num_servicios") or 1) > 1:
                # Operación con varios servicios sobre una pieza: fg_qty es la porción
                # (k porciones = la pieza). El servicio se factura sobre la pieza
                # ENTERA (cada bordado se hace en las N prendas), así que la qty
                # facturable es el total, no la porción.
                service_qty = flt(row.get("fg_qty_total")) or (fg_qty * conversion_factor)
            else:
                service_qty = fg_qty * conversion_factor
            service_uom = (bom_data.service_item_uom if bom_data else None) or _get_service_stock_uom(service_item) or "Nos"
            if service_uom == "Lote":
                # El proveedor solo entrega lotes completos (ej. lotes de 25 piezas) -- si
                # fg_qty no es múltiplo exacto, hay que pedir de más, no truncar.
                service_qty = math.ceil(service_qty - 1e-6)

            item_row = {
                "fg_item": row.finished_good,
                "fg_item_qty": fg_qty,
                # Para el formato impreso, que agrupa los renglones por servicio y
                # cobra por PRENDA (ver patch v0_2_41). No se puede deducir del
                # renglón: los puños van 2 por prenda, así que su cantidad no son
                # prendas.
                "prendas": flt(row.get("fg_qty_total")) / (flt(row.get("piezas_prenda")) or 1),
                "producto_terminado": row.producto_terminado,
                "item_code": service_item,
                "qty": service_qty,
                "uom": service_uom,
                "warehouse": row.target_warehouse,
                "schedule_date": row.schedule_date or nowdate(),
                "rate": row.service_price or 0,
            }
            if bom_data and bom_data.finished_good_bom:
                item_row["bom"] = bom_data.finished_good_bom
            if sales_order:
                item_row["sales_order"] = sales_order
                # Solo el producto terminado (última etapa) es línea directa de la OV; un
                # subensamblaje intermedio no tiene su propia Sales Order Item -- se deja
                # sales_order_item vacío para esas filas, sales_order alcanza para filtrar.
                # En una operación terminal fusionada (varios servicios -> el producto)
                # SOLO la primera línea lleva sales_order_item: ERPNext valida el
                # "over allowance" sumando el qty de todas las líneas que apuntan a la
                # misma Sales Order Item, y como cada servicio factura el total, k
                # líneas sumarían k x la cantidad vendida y lo rechazaría.
                soi = _sales_order_item(row.finished_good)
                if soi and row.finished_good not in _soi_ya_asignado:
                    item_row["sales_order_item"] = soi
                    _soi_ya_asignado.add(row.finished_good)

            po.append("items", item_row)
            rates_esperados.append(flt(row.service_price))

        po.flags.ignore_permissions = 1
        po.set_missing_values()

        # set_missing_values() rellena `rate` desde la Lista de Precios cuando el
        # renglón viene en 0, y nuestros renglones en $0 son INTENCIONALES: el
        # precio de un servicio viaja completo en una sola pieza y las demás van
        # en cero (ver _resolve_piece_states). Sin esto, cada pieza volvía a cobrar
        # el precio íntegro y la OC de corte salía 7x -- $265,790 en vez de $37,970.
        # Se reimpone el precio del costeo, que es la única fuente válida.
        #
        # Hay que fijar SIEMPRE `price_list_rate`, aunque `rate` ya venga bien: si
        # se deja vacío, el validate() de insert() lo trae de la lista y de ahí
        # recalcula `rate` (accounts_controller.py:1136). Ponerlo en 0 explícito
        # -- 0 no es None -- es lo que corta esa cadena.
        for idx, it in enumerate(po.items):
            esperado = flt(rates_esperados[idx])
            it.rate = esperado
            it.price_list_rate = esperado
            it.discount_percentage = 0
            it.discount_amount = 0
            it.margin_type = ""
            it.margin_rate_or_amount = 0
            it.rate_with_margin = 0

        if plantilla_proveedor:
            po.taxes_and_charges = plantilla_proveedor
        po.calculate_taxes_and_totals()
        po.insert()
        purchase_orders.append(po.name)

    if purchase_orders:
        links = [frappe.utils.get_link_to_form("Purchase Order", po_name) for po_name in purchase_orders]
        frappe.msgprint(_("Purchase Orders created: {0}").format(", ".join(links)))
    else:
        frappe.msgprint(_("No Purchase Orders were created"))

    if not taxes_template:
        frappe.msgprint(
            _(
                "No Purchase Taxes and Charges Template was found for company {0}. "
                "Please add IVA taxes manually."
            ).format(company),
            alert=True,
            indicator="orange",
        )

    return {"purchase_orders": purchase_orders}


@frappe.whitelist()
def pp_make_subcontracting_purchase_orders(doc):
    source = _as_dict(doc)
    stage_rows = _build_stage_subcontracting_rows(source)

    if stage_rows:
        return _create_subcontracting_pos_from_stages(source, stage_rows)

    # Fallback: use standard Production Plan behavior when no stage configuration exists.
    pp = _build_production_plan_from_costeo(doc)
    grouped_rows = {}
    purchase_orders = []

    for row in pp.get("sub_assembly_items") or []:
        if row.type_of_manufacturing == "Subcontract":
            grouped_rows.setdefault(row.supplier, []).append(row)

    pp.make_subcontracted_purchase_order(grouped_rows, purchase_orders)
    pp.show_list_created_message("Purchase Order", purchase_orders)

    if not purchase_orders:
        frappe.msgprint(_("No Purchase Orders were created"))

    return {"purchase_orders": purchase_orders}


@frappe.whitelist()
def pp_get_default_suppliers(items, company=None, doc=None):
    if isinstance(items, str):
        items = json.loads(items)

    items = [item for item in (items or []) if item]
    if not items:
        return {}

    rows = frappe.get_all(
        "Item Default",
        fields=["parent", "default_supplier", "company"],
        filters={"parent": ["in", items], "default_supplier": ["is", "set"]},
        order_by="modified desc",
    )

    suppliers = {}
    for row in rows:
        parent = row.parent
        if not suppliers.get(parent):
            suppliers[parent] = row.default_supplier
            continue

        # Prefer company-specific default when available.
        if company and row.company == company:
            suppliers[parent] = row.default_supplier

    missing = [item for item in items if item not in suppliers]
    if missing:
        item_supplier_rows = frappe.get_all(
            "Item Supplier",
            fields=["parent", "supplier"],
            filters={"parent": ["in", missing], "supplier": ["is", "set"]},
            order_by="idx asc",
        )

        for row in item_supplier_rows:
            if not suppliers.get(row.parent):
                suppliers[row.parent] = row.supplier

    return suppliers
