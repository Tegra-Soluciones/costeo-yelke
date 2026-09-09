import frappe
from frappe.utils import nowdate, add_days


@frappe.whitelist()
def get_purchase_order_form_defaults():
    company = frappe.db.get_default("company") or ""

    suppliers = frappe.get_all(
        "Supplier",
        fields=["name", "supplier_name", "supplier_group"],
        filters={"disabled": 0},
        order_by="supplier_name asc",
        limit=200,
    )

    price_lists = frappe.get_all(
        "Price List",
        fields=["name", "currency"],
        filters={"buying": 1, "enabled": 1},
        order_by="name asc",
    )

    currencies = frappe.get_all(
        "Currency", fields=["name"], filters={"enabled": 1}, order_by="name asc", limit=50
    )

    tax_templates = frappe.get_all(
        "Purchase Taxes and Charges Template",
        fields=["name", "company"],
        filters={"company": company} if company else {},
        order_by="name asc",
        limit=30,
    )

    terms_templates = frappe.get_all(
        "Terms and Conditions",
        fields=["name"],
        filters={"buying": 1},
        order_by="name asc",
        limit=30,
    )

    warehouses = frappe.get_all(
        "Warehouse",
        fields=["name", "company"],
        filters={"is_group": 0, "disabled": 0},
        order_by="name asc",
        limit=50,
    )

    uoms = frappe.get_all("UOM", fields=["name"], order_by="name asc", limit=0)

    default_price_list = frappe.db.get_value(
        "Price List", {"buying": 1, "enabled": 1, "currency": "MXN"}, "name"
    ) or (price_lists[0]["name"] if price_lists else "")

    default_currency = frappe.db.get_value("Company", company, "default_currency") if company else "MXN"

    return {
        "company": company,
        "suppliers": suppliers,
        "price_lists": price_lists,
        "currencies": currencies,
        "tax_templates": tax_templates,
        "terms_templates": terms_templates,
        "warehouses": warehouses,
        "uoms": uoms,
        "default_price_list": default_price_list,
        "default_currency": default_currency,
    }


@frappe.whitelist()
def get_purchase_orders(status=None, supplier=None, company=None, limit=50):
    filters = {}
    if status:
        filters["status"] = status
    if supplier:
        filters["supplier"] = supplier
    if company:
        filters["company"] = company

    fields = [
        "name", "status", "supplier", "supplier_name",
        "transaction_date", "schedule_date", "grand_total", "currency",
        "company", "docstatus", "is_subcontracted",
    ]
    if frappe.db.has_column("Purchase Order", "costeo"):
        fields.append("costeo")

    rows = frappe.get_all(
        "Purchase Order",
        fields=fields,
        filters=filters,
        order_by="transaction_date desc, creation desc",
        limit=int(limit),
    )
    return rows


@frappe.whitelist()
def get_purchase_order(name):
    doc = frappe.get_doc("Purchase Order", name)

    items = []
    for r in doc.items:
        image = frappe.db.get_value("Item", r.item_code, "image") or ""
        items.append({
            "name": r.name,
            "item_code": r.item_code,
            "item_name": r.item_name,
            "description": r.description or "",
            "qty": float(r.qty or 1),
            "uom": r.uom,
            "stock_uom": r.stock_uom,
            "conversion_factor": float(r.conversion_factor or 1),
            "price_list_rate": float(r.price_list_rate or 0),
            "rate": float(r.rate or 0),
            "discount_percentage": float(r.discount_percentage or 0),
            "amount": float(r.amount or 0),
            "net_amount": float(r.net_amount or 0),
            "schedule_date": str(r.schedule_date) if r.schedule_date else "",
            "warehouse": r.warehouse or "",
            "image": image,
        })

    taxes = []
    for r in doc.taxes:
        taxes.append({
            "name": r.name,
            "charge_type": r.charge_type,
            "account_head": r.account_head,
            "description": r.description or "",
            "rate": float(r.rate or 0),
            "tax_amount": float(r.tax_amount or 0),
            "total": float(r.total or 0),
        })

    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.status,
        "supplier": doc.supplier,
        "supplier_name": doc.supplier_name or "",
        "company": doc.company,
        "transaction_date": str(doc.transaction_date) if doc.transaction_date else "",
        "schedule_date": str(doc.schedule_date) if doc.schedule_date else "",
        "currency": doc.currency,
        "buying_price_list": doc.buying_price_list or "",
        "conversion_rate": float(doc.conversion_rate or 1),
        "taxes_and_charges": doc.taxes_and_charges or "",
        "additional_discount_percentage": float(doc.additional_discount_percentage or 0),
        "discount_amount": float(doc.discount_amount or 0),
        "apply_discount_on": doc.apply_discount_on or "Grand Total",
        "total": float(doc.total or 0),
        "total_taxes_and_charges": float(doc.total_taxes_and_charges or 0),
        "grand_total": float(doc.grand_total or 0),
        "tc_name": doc.tc_name or "",
        "terms": doc.terms or "",
        "supplier_address": doc.supplier_address or "",
        "contact_person": doc.contact_person or "",
        "contact_email": doc.contact_email or "",
        "contact_mobile": doc.contact_mobile or "",
        "creation": str(doc.creation),
        "modified": str(doc.modified),
        "items": items,
        "taxes": taxes,
    }


@frappe.whitelist()
def save_purchase_order(data):
    import json
    if isinstance(data, str):
        data = json.loads(data)

    name = data.get("name") or ""

    if name:
        doc = frappe.get_doc("Purchase Order", name)
        if doc.docstatus != 0:
            frappe.throw("Solo se pueden editar órdenes de compra en borrador.")
    else:
        doc = frappe.new_doc("Purchase Order")

    for field in [
        "supplier", "company", "transaction_date", "schedule_date",
        "currency", "buying_price_list", "conversion_rate",
        "taxes_and_charges", "tc_name", "terms",
        "additional_discount_percentage", "discount_amount", "apply_discount_on",
        "supplier_address", "contact_person", "contact_email", "contact_mobile",
    ]:
        val = data.get(field)
        if val is not None and val != "":
            setattr(doc, field, val)

    schedule_date = data.get("schedule_date") or add_days(nowdate(), 7)

    doc.items = []
    for r in data.get("items") or []:
        if not r.get("item_code"):
            continue
        row = doc.append("items", {})
        row.item_code         = r["item_code"]
        row.item_name         = r.get("item_name") or r["item_code"]
        row.description       = r.get("description") or ""
        row.qty               = float(r.get("qty") or 1)
        row.uom               = r.get("uom") or ""
        row.conversion_factor = float(r.get("conversion_factor") or 1)
        row.rate              = float(r.get("rate") or 0)
        row.discount_percentage = float(r.get("discount_percentage") or 0)
        row.warehouse         = r.get("warehouse") or ""
        row.schedule_date     = r.get("schedule_date") or schedule_date

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.flags.ignore_links       = True
    doc.run_method("set_missing_values")
    doc.run_method("calculate_taxes_and_totals")

    if name:
        doc.save()
    else:
        doc.insert()

    frappe.db.commit()
    return get_purchase_order(doc.name)


@frappe.whitelist()
def submit_purchase_order(name):
    doc = frappe.get_doc("Purchase Order", name)
    if doc.docstatus != 0:
        frappe.throw("La orden de compra ya fue enviada o cancelada.")
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.flags.ignore_links       = True
    doc.submit()
    frappe.db.commit()
    return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


@frappe.whitelist()
def cancel_purchase_order(name):
    doc = frappe.get_doc("Purchase Order", name)
    doc.flags.ignore_permissions = True
    doc.cancel()
    frappe.db.commit()
    return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


@frappe.whitelist()
def make_purchase_order_from_sales_order(sales_order_name, supplier):
    """Create a Purchase Order from a confirmed Sales Order for a given supplier."""
    so = frappe.get_doc("Sales Order", sales_order_name)
    if so.docstatus != 1:
        frappe.throw("La orden de venta debe estar confirmada.")

    schedule_date = add_days(nowdate(), 7)

    po = frappe.new_doc("Purchase Order")
    po.supplier        = supplier
    po.company         = so.company
    po.transaction_date = nowdate()
    po.schedule_date   = schedule_date
    po.currency        = so.currency

    for item in so.items:
        row = po.append("items", {})
        row.item_code     = item.item_code
        row.item_name     = item.item_name
        row.description   = item.description or ""
        row.qty           = float(item.qty or 1)
        row.uom           = item.uom
        row.rate          = float(item.rate or 0)
        row.schedule_date = schedule_date
        row.warehouse     = item.warehouse or ""

    po.flags.ignore_permissions = True
    po.flags.ignore_mandatory   = True
    po.flags.ignore_links       = True
    po.run_method("set_missing_values")
    po.run_method("calculate_taxes_and_totals")
    po.insert()
    frappe.db.commit()
    return {"name": po.name, "doctype": "Purchase Order"}


@frappe.whitelist()
def make_purchase_invoice_from_po(po_name):
    """Create a Purchase Invoice (draft) from a submitted Purchase Order."""
    from erpnext.buying.doctype.purchase_order.purchase_order import (
        make_purchase_invoice as _make_pinv,
    )

    pinv = _make_pinv(po_name)
    pinv.flags.ignore_permissions = True
    pinv.flags.ignore_mandatory   = True
    pinv.flags.ignore_links       = True
    pinv.posting_date = nowdate()
    pinv.insert()
    frappe.db.commit()
    return {"name": pinv.name, "doctype": "Purchase Invoice"}


@frappe.whitelist()
def get_item_details_for_po(item_code, price_list=None):
    item = frappe.db.get_value(
        "Item",
        item_code,
        ["item_name", "description", "stock_uom", "standard_rate", "purchase_uom"],
        as_dict=True,
    )
    if not item:
        return {}

    uom = item.get("purchase_uom") or item.get("stock_uom") or ""
    if price_list and item_code:
        ip = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": price_list, "buying": 1},
            "price_list_rate",
        )
        rate = float(ip or item.get("standard_rate") or 0)
    else:
        rate = float(item.get("standard_rate") or 0)

    image = frappe.db.get_value("Item", item_code, "image") or ""

    return {
        "item_name": item.get("item_name") or item_code,
        "description": item.get("description") or "",
        "stock_uom": item.get("stock_uom") or "",
        "uom": uom,
        "rate": rate,
        "price_list_rate": rate,
        "image": image,
    }
