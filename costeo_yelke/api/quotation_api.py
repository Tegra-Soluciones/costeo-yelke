import frappe
from frappe.utils import nowdate


@frappe.whitelist()
def get_quotation_form_defaults():
    """Returns data needed to populate the Quotation form."""
    company = frappe.db.get_default("company") or ""

    customers = frappe.get_all(
        "Customer",
        fields=["name", "customer_name", "customer_group", "territory"],
        filters={"disabled": 0},
        order_by="customer_name asc",
        limit=200,
    )

    price_lists = frappe.get_all(
        "Price List",
        fields=["name", "currency", "buying", "selling"],
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
def get_quotations(status=None, customer=None, limit=50):
    """Returns a list of quotations with key fields."""
    filters = {}
    if status:
        filters["status"] = status
    if customer:
        filters["party_name"] = customer

    rows = frappe.get_all(
        "Quotation",
        fields=[
            "name", "status", "quotation_to", "party_name", "customer_name",
            "transaction_date", "valid_till", "grand_total", "currency",
            "company", "order_type", "docstatus",
        ],
        filters=filters,
        order_by="transaction_date desc, creation desc",
        limit=int(limit),
    )
    return rows


@frappe.whitelist()
def get_quotation(name):
    """Returns full quotation data for the SPA detail view."""
    doc = frappe.get_doc("Quotation", name)

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
            "discount_amount": float(r.discount_amount or 0),
            "amount": float(r.amount or 0),
            "net_amount": float(r.net_amount or 0),
            "warehouse": r.warehouse or "",
            "item_tax_template": r.item_tax_template or "",
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
        "quotation_to": doc.quotation_to,
        "party_name": doc.party_name,
        "customer_name": doc.customer_name or "",
        "company": doc.company,
        "transaction_date": str(doc.transaction_date) if doc.transaction_date else "",
        "valid_till": str(doc.valid_till) if doc.valid_till else "",
        "order_type": doc.order_type or "Sales",
        "custom_tipo_formato": doc.get("custom_tipo_formato") or "Normal",
        "currency": doc.currency,
        "selling_price_list": doc.selling_price_list,
        "conversion_rate": float(doc.conversion_rate or 1),
        "taxes_and_charges": doc.taxes_and_charges or "",
        "additional_discount_percentage": float(doc.additional_discount_percentage or 0),
        "discount_amount": float(doc.discount_amount or 0),
        "apply_discount_on": doc.apply_discount_on or "Grand Total",
        "total": float(doc.total or 0),
        "total_taxes_and_charges": float(doc.total_taxes_and_charges or 0),
        "grand_total": float(doc.grand_total or 0),
        "rounded_total": float(doc.rounded_total or 0),
        "in_words": doc.in_words or "",
        "tc_name": doc.tc_name or "",
        "terms": doc.terms or "",
        "customer_address": doc.customer_address or "",
        "shipping_address_name": doc.shipping_address_name or "",
        "contact_person": doc.contact_person or "",
        "contact_email":  doc.contact_email or "",
        "contact_mobile": doc.contact_mobile or "",
        "creation": str(doc.creation),
        "modified": str(doc.modified),
        "items": items,
        "taxes": taxes,
    }


@frappe.whitelist()
def save_quotation(data):
    """Create or update a Quotation. Pass name=None/empty to create."""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    name = data.get("name") or ""

    if name:
        doc = frappe.get_doc("Quotation", name)
        if doc.docstatus != 0:
            frappe.throw("Solo se pueden editar cotizaciones en borrador.")
    else:
        doc = frappe.new_doc("Quotation")

    # Scalar fields
    for field in [
        "quotation_to", "party_name", "company", "transaction_date",
        "valid_till", "order_type", "custom_tipo_formato", "currency", "selling_price_list",
        "conversion_rate", "taxes_and_charges", "tc_name", "terms",
        "additional_discount_percentage", "discount_amount", "apply_discount_on",
        "customer_address", "shipping_address_name", "contact_person",
        "contact_email", "contact_mobile",
    ]:
        val = data.get(field)
        if val is not None and val != "":
            setattr(doc, field, val)

    # Items
    doc.items = []
    for r in data.get("items") or []:
        if not r.get("item_code"):
            continue
        row = doc.append("items", {})
        row.item_code          = r["item_code"]
        row.item_name          = r.get("item_name") or r["item_code"]
        row.description        = r.get("description") or ""
        row.qty                = float(r.get("qty") or 1)
        row.uom                = r.get("uom") or ""
        row.conversion_factor  = float(r.get("conversion_factor") or 1)
        row.rate               = float(r.get("rate") or 0)
        row.discount_percentage = float(r.get("discount_percentage") or 0)
        row.warehouse          = r.get("warehouse") or ""

    # Taxes – keep template-driven taxes; don't override
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
    return get_quotation(doc.name)


@frappe.whitelist()
def submit_quotation(name):
    """Submit a draft quotation."""
    doc = frappe.get_doc("Quotation", name)
    if doc.docstatus != 0:
        frappe.throw("La cotización ya fue enviada o cancelada.")
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.flags.ignore_links       = True
    doc.submit()
    frappe.db.commit()
    return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


@frappe.whitelist()
def cancel_quotation(name):
    """Cancel a submitted quotation."""
    doc = frappe.get_doc("Quotation", name)
    doc.flags.ignore_permissions = True
    doc.cancel()
    frappe.db.commit()
    return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


@frappe.whitelist()
def make_sales_order(name):
    """Create a Sales Order from a submitted Quotation."""
    from costeo_yelke.api.sales_order_api import make_sales_order_from_quotation
    return make_sales_order_from_quotation(name)


@frappe.whitelist()
def get_item_details_for_quotation(item_code, price_list=None, currency=None):
    """Return item defaults for the quotation item row."""
    item = frappe.db.get_value(
        "Item",
        item_code,
        ["item_name", "description", "stock_uom", "standard_rate", "sales_uom"],
        as_dict=True,
    )
    if not item:
        return {}

    rate = 0.0
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


@frappe.whitelist()
def prefill_from_costeo(costeo):
    """Returns prefill data from a Costeo document for a new Quotation."""
    doc = frappe.get_doc("Costeo", costeo)

    items = []
    for p in doc.costeo_producto:
        if not p.finished_item:
            continue
        item_name = frappe.db.get_value("Item", p.finished_item, "item_name") or p.finished_item
        uom = frappe.db.get_value("Item", p.finished_item, "stock_uom") or "Nos"
        items.append({
            "item_code": p.finished_item,
            "item_name": item_name,
            "qty": float(p.qty or 1),
            "uom": uom,
            "conversion_factor": 1,
            "rate": float(p.unit_sales_price or 0),
            "price_list_rate": float(p.unit_sales_price or 0),
            "discount_percentage": 0,
            "description": "",
        })

    tax_template = _get_sales_tax_template(doc.compañia)

    return {
        "quotation_to": "Customer",
        "party_name": doc.cliente or "",
        "company": doc.compañia or "",
        "transaction_date": nowdate(),
        "order_type": "Sales",
        "taxes_and_charges": tax_template or "",
        "costeo": costeo,
        "items": items,
    }


@frappe.whitelist()
def get_quotation_print_formats():
    """Returns available print formats for Quotation."""
    formats = frappe.get_all(
        "Print Format",
        filters={"doc_type": "Quotation", "disabled": 0},
        fields=["name"],
        order_by="name asc",
    )
    # Always include Standard
    names = [f["name"] for f in formats]
    if "Standard" not in names:
        formats = [{"name": "Standard"}] + formats
    return formats


@frappe.whitelist()
def send_quotation_email(name, recipients, subject, message, print_format=None, attach_pdf=1):
    """Send a quotation via email, optionally attaching the PDF."""
    import json
    if isinstance(recipients, str):
        try:
            recipients = json.loads(recipients)
        except Exception:
            recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    attachments = []
    if int(attach_pdf or 0):
        fmt = print_format or "Standard"
        try:
            attachments = [frappe.attach_print("Quotation", name, print_format=fmt, lang=None)]
        except Exception:
            pass

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=attachments,
        reference_doctype="Quotation",
        reference_name=name,
        now=True,
    )
    frappe.db.commit()
    return {"ok": True}


def _get_sales_tax_template(company):
    return frappe.db.get_value(
        "Sales Taxes and Charges Template",
        {"company": company, "is_default": 1},
        "name",
    ) or frappe.db.get_value(
        "Sales Taxes and Charges Template",
        {"company": company},
        "name",
    )
