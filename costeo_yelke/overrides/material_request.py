import json

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.stock.doctype.material_request import material_request as erpnext_material_request


def _parse_args(args):
    if args is None:
        return {}
    if isinstance(args, str):
        return json.loads(args)
    return args


def _is_pending_row(row):
    qty = row.ordered_qty or row.received_qty
    return flt(qty) < flt(row.stock_qty)


def _get_pending_rows(material_request, filtered_children):
    pending_rows = []
    selected = set(filtered_children or [])

    for row in material_request.items:
        if selected and row.name not in selected:
            continue
        if _is_pending_row(row):
            pending_rows.append(row)

    return pending_rows


def _make_supplier_purchase_order(material_request_name, supplier, row_names):
    allowed_rows = set(row_names)

    def select_item(row):
        return (
            row.name in allowed_rows
            and _is_pending_row(row)
            and (row.get("supplier") or "") == supplier
        )

    def postprocess(source, target_doc):
        target_doc.supplier = supplier
        erpnext_material_request.set_missing_values(source, target_doc)

    po_doc = get_mapped_doc(
        "Material Request",
        material_request_name,
        {
            "Material Request": {
                "doctype": "Purchase Order",
                "validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
            },
            "Material Request Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "material_request_item"],
                    ["parent", "material_request"],
                    ["uom", "stock_uom"],
                    ["uom", "uom"],
                    ["sales_order", "sales_order"],
                    ["sales_order_item", "sales_order_item"],
                    ["wip_composite_asset", "wip_composite_asset"],
                ],
                "postprocess": erpnext_material_request.update_item,
                "condition": select_item,
            },
        },
        None,
        postprocess,
    )

    if not po_doc.get("items"):
        return None

    _set_purchase_order_custom_abbr(po_doc)
    _apply_supplier_item_prices(po_doc)

    po_doc.flags.ignore_permissions = 1
    po_doc.insert()
    return po_doc


def _set_purchase_order_custom_abbr(po_doc):
    if not po_doc or not po_doc.get("company"):
        return

    if not frappe.get_meta("Purchase Order").has_field("custom_abbr"):
        return

    if po_doc.get("custom_abbr"):
        return

    po_doc.custom_abbr = (po_doc.get("company") or "")[:3].upper()


def _get_buying_price_list(po_doc):
    return po_doc.get("buying_price_list") or frappe.db.get_single_value("Buying Settings", "buying_price_list")


def _get_supplier_item_rate(po_doc, po_item, price_list):
    from erpnext.stock.get_item_details import get_item_price

    uom = po_item.get("uom")
    stock_uom = po_item.get("stock_uom") or uom
    conversion_factor = flt(po_item.get("conversion_factor")) or 1

    item_price_args = {
        "price_list": price_list,
        "supplier": po_doc.get("supplier"),
        "uom": uom,
        "transaction_date": po_doc.get("transaction_date"),
    }
    item_price_data = get_item_price(item_price_args, po_item.get("item_code"))

    if not item_price_data and stock_uom and stock_uom != uom:
        item_price_args["uom"] = stock_uom
        item_price_data = get_item_price(item_price_args, po_item.get("item_code"))

    if not item_price_data:
        return None

    price_list_rate = flt(item_price_data[0][1])
    item_price_uom = item_price_data[0][2]

    if item_price_uom == uom:
        return price_list_rate

    if po_doc.get("price_list_uom_dependant"):
        return price_list_rate

    return price_list_rate * conversion_factor


def _apply_supplier_item_prices(po_doc):
    if not po_doc.get("supplier") or not po_doc.get("items"):
        return

    price_list = _get_buying_price_list(po_doc)
    if not price_list:
        return

    po_doc.buying_price_list = price_list
    has_price_update = False

    for po_item in po_doc.get("items"):
        if not po_item.get("item_code"):
            continue

        price_rate = _get_supplier_item_rate(po_doc, po_item, price_list)
        if price_rate is None:
            continue

        po_item.price_list_rate = price_rate
        po_item.rate = price_rate
        po_item.amount = flt(po_item.get("qty")) * flt(price_rate)
        has_price_update = True

    if has_price_update:
        po_doc.calculate_taxes_and_totals()


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
    args = _parse_args(args)

    if target_doc:
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    if args.get("default_supplier"):
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    if not frappe.db.has_column("Material Request Item", "supplier"):
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    material_request = frappe.get_doc("Material Request", source_name)
    if material_request.material_request_type != "Purchase" or material_request.docstatus != 1:
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    pending_rows = _get_pending_rows(material_request, args.get("filtered_children"))
    if not pending_rows:
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    rows_with_supplier = [row for row in pending_rows if row.get("supplier")]
    if not rows_with_supplier:
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    # Keep default behavior if supplier assignment is partial.
    if len(rows_with_supplier) != len(pending_rows):
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    grouped_rows = {}
    for row in pending_rows:
        grouped_rows.setdefault(row.supplier, []).append(row.name)

    created_purchase_orders = []
    first_po_doc = None

    for supplier, row_names in grouped_rows.items():
        po_doc = _make_supplier_purchase_order(material_request.name, supplier, row_names)
        if not po_doc:
            continue

        created_purchase_orders.append(po_doc.name)
        if not first_po_doc:
            first_po_doc = po_doc

    if not first_po_doc:
        return erpnext_material_request.make_purchase_order(source_name, target_doc=target_doc, args=args)

    links = [frappe.utils.get_link_to_form("Purchase Order", po_name) for po_name in created_purchase_orders]
    frappe.msgprint(_("Purchase Orders created: {0}").format(", ".join(links)))
    return first_po_doc
