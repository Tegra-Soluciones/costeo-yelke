# -*- coding: utf-8 -*-
# Copyright (c) 2025, Tu Empresa and contributors
# For license information, please see license.txt

import json
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
        customer_token = _build_costeo_customer_token(self.cliente)
        self.name = make_autoname(f"CST-{customer_token}-.YYYY.-.#####", doc=self)

    def validate(self):
        self.validate_at_least_one_product_to_produce()
        self.cleanup_orphan_children()

    def validate_at_least_one_product_to_produce(self):
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
    return source.get("company") or source.get("compañia")


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

    return frappe.db.get_value(
        "Warehouse",
        {
            "company": company,
            "is_group": 0,
            "disabled": 0,
            "proveedor_asociado": supplier,
        },
        "name",
    )


def _get_purchase_tax_template(company):
    if not company:
        return None

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


def _build_stage_subcontracting_rows(source):
    stage_rows = []
    qty_map = _get_finished_qty_map(source)
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
        etapas_ordenadas = sorted(etapas, key=_stage_sort_key)
        fg_qty = qty_map.get(producto_terminado) or 1

        for index, etapa in enumerate(etapas_ordenadas):
            proveedor = etapa.get("proveedor")
            servicio = etapa.get("servicio")
            if not proveedor or not servicio:
                continue

            es_ultima = index == len(etapas_ordenadas) - 1
            finished_good = producto_terminado if es_ultima else (etapa.get("subensamblaje") or producto_terminado)

            target_warehouse = None
            if es_ultima:
                target_warehouse = fg_warehouse_map.get(producto_terminado)
                if not target_warehouse:
                    target_warehouse = _get_item_default_warehouse(producto_terminado, company)
                if not target_warehouse:
                    target_warehouse = _guess_finished_goods_warehouse(company)
                if not target_warehouse:
                    target_warehouse = wip_warehouse
            else:
                target_warehouse = wip_warehouse
                if not target_warehouse:
                    target_warehouse = _get_item_default_warehouse(finished_good, company)

            stage_rows.append(
                frappe._dict(
                    {
                        "producto_terminado": producto_terminado,
                        "etapa": etapa.get("etapa"),
                        "supplier": proveedor,
                        "service_item": servicio,
                        "service_price": flt(etapa.get("precio_servicio")),
                        "finished_good": finished_good,
                        "finished_good_qty": fg_qty,
                        "target_warehouse": target_warehouse,
                        "schedule_date": default_schedule_date,
                    }
                )
            )

    return stage_rows


def _create_subcontracting_pos_from_stages(source, stage_rows):
    company = _get_company_name(source)
    if not company:
        frappe.throw(_("Company is required to create Subcontracting Purchase Orders."))

    bom_map = _get_subcontracting_bom_map([row.finished_good for row in stage_rows])
    taxes_template = _get_purchase_tax_template(company)
    purchase_orders = []

    for row in stage_rows:
        if not row.finished_good:
            frappe.throw(
                _("Stage {0} for product {1} has no finished good configured.").format(
                    row.etapa or "?", row.producto_terminado
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
                    row.etapa or "?", row.finished_good
                )
            )

        conversion_factor = flt(bom_data.conversion_factor) if bom_data else 1
        conversion_factor = conversion_factor or 1
        fg_qty = flt(row.finished_good_qty) or 1
        service_qty = fg_qty * conversion_factor
        service_uom = (bom_data.service_item_uom if bom_data else None) or _get_service_stock_uom(service_item) or "Nos"

        po = frappe.new_doc("Purchase Order")
        po.company = company
        po.supplier = row.supplier
        po.is_subcontracted = 1
        po.transaction_date = source.get("posting_date") or source.get("fecha") or nowdate()
        po.schedule_date = row.schedule_date or nowdate()

        supplier_warehouse = _get_supplier_warehouse(company, row.supplier)
        if supplier_warehouse:
            po.supplier_warehouse = supplier_warehouse

        if taxes_template:
            po.taxes_and_charges = taxes_template

        item_row = {
            "fg_item": row.finished_good,
            "fg_item_qty": fg_qty,
            "item_code": service_item,
            "qty": service_qty,
            "uom": service_uom,
            "warehouse": row.target_warehouse,
            "schedule_date": row.schedule_date or nowdate(),
            "rate": row.service_price or 0,
        }
        if bom_data and bom_data.finished_good_bom:
            item_row["bom"] = bom_data.finished_good_bom

        po.append("items", item_row)
        po.flags.ignore_permissions = 1
        po.set_missing_values()
        if taxes_template:
            po.taxes_and_charges = taxes_template
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
