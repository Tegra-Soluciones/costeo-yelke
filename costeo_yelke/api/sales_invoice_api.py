import frappe
from frappe.utils import nowdate, add_days


@frappe.whitelist()
def get_sales_invoice_form_defaults():
    company = frappe.db.get_default("company") or ""

    customers = frappe.get_all(
        "Customer",
        fields=["name", "customer_name", "customer_group"],
        filters={"disabled": 0},
        order_by="customer_name asc",
        limit=200,
    )

    price_lists = frappe.get_all(
        "Price List",
        fields=["name", "currency"],
        filters={"selling": 1, "enabled": 1},
        order_by="name asc",
    )

    currencies = frappe.get_all(
        "Currency", fields=["name"], filters={"enabled": 1}, order_by="name asc", limit=50
    )

    tax_templates = frappe.get_all(
        "Sales Taxes and Charges Template",
        fields=["name", "company"],
        filters={"company": company} if company else {},
        order_by="name asc",
        limit=30,
    )

    terms_templates = frappe.get_all(
        "Terms and Conditions",
        fields=["name"],
        filters={"selling": 1},
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
        "Price List", {"selling": 1, "enabled": 1, "currency": "MXN"}, "name"
    ) or (price_lists[0]["name"] if price_lists else "")

    default_currency = frappe.db.get_value("Company", company, "default_currency") if company else "MXN"

    return {
        "company": company,
        "customers": customers,
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
def get_sales_invoices(status=None, customer=None, limit=50):
    filters = {}
    if status:
        filters["status"] = status
    if customer:
        filters["customer"] = customer

    rows = frappe.get_all(
        "Sales Invoice",
        fields=[
            "name", "status", "customer", "customer_name",
            "posting_date", "due_date", "grand_total", "outstanding_amount",
            "currency", "company", "docstatus", "is_return",
        ],
        filters=filters,
        order_by="posting_date desc, creation desc",
        limit=int(limit),
    )
    return rows


@frappe.whitelist()
def get_sales_invoice(name):
    doc = frappe.get_doc("Sales Invoice", name)

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
        "customer": doc.customer,
        "customer_name": doc.customer_name or "",
        "company": doc.company,
        "posting_date": str(doc.posting_date) if doc.posting_date else "",
        "due_date": str(doc.due_date) if doc.due_date else "",
        "currency": doc.currency,
        "selling_price_list": doc.selling_price_list or "",
        "conversion_rate": float(doc.conversion_rate or 1),
        "taxes_and_charges": doc.taxes_and_charges or "",
        "additional_discount_percentage": float(doc.additional_discount_percentage or 0),
        "discount_amount": float(doc.discount_amount or 0),
        "apply_discount_on": doc.apply_discount_on or "Grand Total",
        "total": float(doc.total or 0),
        "total_taxes_and_charges": float(doc.total_taxes_and_charges or 0),
        "grand_total": float(doc.grand_total or 0),
        "rounded_total": float(doc.rounded_total or 0),
        "outstanding_amount": float(doc.outstanding_amount or 0),
        "tc_name": doc.tc_name or "",
        "terms": doc.terms or "",
        "customer_address": doc.customer_address or "",
        "contact_person": doc.contact_person or "",
        "contact_email": doc.contact_email or "",
        "contact_mobile": doc.contact_mobile or "",
        "is_return": doc.is_return or 0,
        "po_no": doc.po_no or "",
        "creation": str(doc.creation),
        "modified": str(doc.modified),
        "items": items,
        "taxes": taxes,
    }


@frappe.whitelist()
def save_sales_invoice(data):
    import json
    if isinstance(data, str):
        data = json.loads(data)

    name = data.get("name") or ""

    if name:
        doc = frappe.get_doc("Sales Invoice", name)
        if doc.docstatus != 0:
            frappe.throw("Solo se pueden editar facturas en borrador.")
    else:
        doc = frappe.new_doc("Sales Invoice")

    for field in [
        "customer", "company", "posting_date", "due_date",
        "currency", "selling_price_list", "conversion_rate",
        "taxes_and_charges", "tc_name", "terms",
        "additional_discount_percentage", "discount_amount", "apply_discount_on",
        "customer_address", "contact_person", "contact_email", "contact_mobile", "po_no",
    ]:
        val = data.get(field)
        if val is not None and val != "":
            setattr(doc, field, val)

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
    return get_sales_invoice(doc.name)


@frappe.whitelist()
def submit_sales_invoice(name):
    doc = frappe.get_doc("Sales Invoice", name)
    if doc.docstatus != 0:
        frappe.throw("La factura ya fue enviada o cancelada.")
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.flags.ignore_links       = True
    doc.submit()
    frappe.db.commit()
    return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


@frappe.whitelist()
def cancel_sales_invoice(name):
    doc = frappe.get_doc("Sales Invoice", name)
    doc.flags.ignore_permissions = True
    doc.cancel()
    frappe.db.commit()
    return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


@frappe.whitelist()
def make_sales_invoice_from_so(sales_order_name):
    """Create a Sales Invoice (draft) from a confirmed Sales Order."""
    from erpnext.selling.doctype.sales_order.sales_order import (
        make_sales_invoice as _make_sinv,
    )

    sinv = _make_sinv(sales_order_name)
    sinv.flags.ignore_permissions = True
    sinv.flags.ignore_mandatory   = True
    sinv.flags.ignore_links       = True
    sinv.posting_date = nowdate()
    if not sinv.due_date:
        sinv.due_date = add_days(nowdate(), 30)
    sinv.insert()
    frappe.db.commit()
    return {"name": sinv.name, "doctype": "Sales Invoice"}


@frappe.whitelist()
def get_item_details_for_sinv(item_code, price_list=None):
    item = frappe.db.get_value(
        "Item",
        item_code,
        ["item_name", "description", "stock_uom", "standard_rate", "sales_uom"],
        as_dict=True,
    )
    if not item:
        return {}

    uom = item.get("sales_uom") or item.get("stock_uom") or ""
    if price_list and item_code:
        ip = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": price_list, "selling": 1},
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
