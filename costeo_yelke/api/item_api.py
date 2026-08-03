import frappe
from frappe import _


def _valuation_expense_account(company):
    """Cuenta 'Expenses Included In Valuation' de la compañía (o None si no existe).
    Se usa para capitalizar costos de servicio (maquila) en el inventario, en vez de
    caer en el 'default_expense_account' de la compañía (que suele ser Costo de Ventas
    y no debe tocarse hasta que exista una venta real)."""
    if not company:
        return None
    acc = frappe.db.get_value(
        "Account", {"company": company, "account_type": "Expenses Included In Valuation", "is_group": 0}, "name"
    )
    return acc or frappe.get_cached_value("Company", company, "expenses_included_in_valuation")


@frappe.whitelist()
def get_navbar_data():
    """Returns session info for the SPA top navbar."""
    user_name = frappe.session.user
    user_doc  = frappe.get_cached_doc("User", user_name)

    # Unread notifications
    unread = frappe.db.count(
        "Notification Log",
        filters={"for_user": user_name, "read": 0},
    )

    company = frappe.db.get_default("company") or ""
    company_currency = frappe.db.get_value("Company", company, "default_currency") if company else ""

    return {
        "user": {
            "name":       user_name,
            "full_name":  user_doc.full_name or user_name,
            "email":      user_doc.email,
            "user_image": user_doc.user_image or "",
        },
        "company":          company,
        "company_currency": company_currency,
        "unread_notifications": unread,
    }


@frappe.whitelist()
def get_notifications(limit=20):
    """Returns recent notifications for the current user."""
    user_name = frappe.session.user
    notifications = frappe.db.get_all(
        "Notification Log",
        filters={"for_user": user_name},
        fields=["name", "subject", "email_content", "type", "read",
                "document_type", "document_name", "from_user", "creation"],
        order_by="creation desc",
        limit=int(limit),
    )
    return notifications


@frappe.whitelist()
def mark_notifications_read():
    """Mark all notifications for the current user as read."""
    user_name = frappe.session.user
    frappe.db.set_value(
        "Notification Log",
        {"for_user": user_name, "read": 0},
        "read",
        1,
        update_modified=False,
    )
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def get_frappe_apps():
    """Returns apps registered via the add_to_apps_screen hook, plus ERPNext desk."""
    apps = []

    # Collect every entry registered in add_to_apps_screen across all installed apps
    for entry in frappe.get_hooks("add_to_apps_screen"):
        # entry is a dict: {name, logo, title, route}
        if isinstance(entry, dict):
            apps.append({
                "name":  entry.get("name", ""),
                "title": entry.get("title", entry.get("name", "")),
                "logo":  entry.get("logo") or None,
                "home":  entry.get("route", "/app"),
            })

    # Always include ERPNext desk as the first entry if not already present
    names = {a["name"] for a in apps}
    if "erpnext" not in names:
        apps.insert(0, {
            "name":  "erpnext",
            "title": "ERPNext",
            "logo":  None,
            "home":  "/app",
        })

    return apps


@frappe.whitelist()
def get_item_form_defaults():
    """Returns data needed to pre-populate the New Item form."""
    companies = frappe.get_all("Company", fields=["name", "default_currency"], limit=5)
    default_company = frappe.db.get_default("company") or (companies[0].name if companies else "")

    item_groups = frappe.get_all(
        "Item Group",
        fields=["name", "parent_item_group"],
        filters={"is_group": 0},
        order_by="name asc",
    )

    uoms = frappe.get_all("UOM", fields=["name"], order_by="name asc", limit=0)  # 0 = sin límite

    brands = frappe.get_all("Brand", fields=["name"], order_by="name asc", limit=50)

    warehouses = frappe.get_all(
        "Warehouse",
        fields=["name", "company"],
        filters={"is_group": 0, "disabled": 0},
        order_by="name asc",
        limit=50,
    )

    cost_centers = frappe.get_all(
        "Cost Center",
        fields=["name", "company"],
        filters={"is_group": 0, "disabled": 0},
        order_by="name asc",
        limit=50,
    )

    price_lists = frappe.get_all("Price List", fields=["name", "buying", "selling", "currency"], limit=20)

    currencies = frappe.get_all("Currency", fields=["name"], filters={"enabled": 1}, order_by="name asc", limit=50)

    # Check if Mexico Compliance is installed
    has_mexico_compliance = frappe.db.exists("Module Def", "ERPNext Mexico Compliance")

    return {
        "companies": companies,
        "default_company": default_company,
        "item_groups": item_groups,
        "uoms": uoms,
        "brands": brands,
        "warehouses": warehouses,
        "cost_centers": cost_centers,
        "price_lists": price_lists,
        "currencies": currencies,
        "has_mexico_compliance": bool(has_mexico_compliance),
    }


@frappe.whitelist()
def get_pricing_rules(item_code):
    """Get all Pricing Rules linked to this item."""
    rules = frappe.db.sql("""
        SELECT DISTINCT
            pr.name, pr.title, pr.disable, pr.selling, pr.buying,
            pr.min_qty, pr.max_qty, pr.rate_or_discount,
            pr.rate, pr.discount_percentage, pr.discount_amount,
            pr.currency, pr.for_price_list, pr.customer,
            pr.valid_from, pr.valid_upto, pr.company
        FROM `tabPricing Rule` pr
        INNER JOIN `tabPricing Rule Item Code` pri ON pri.parent = pr.name
        WHERE pri.item_code = %s AND pr.apply_on = 'Item Code'
        ORDER BY pr.min_qty ASC, pr.creation ASC
    """, item_code, as_dict=True)
    return rules


@frappe.whitelist()
def save_pricing_rules(item_code, rules):
    """Save pricing rules for an item (create/update/delete by diff)."""
    import json
    if isinstance(rules, str):
        rules = json.loads(rules)

    keep_names = {r["name"] for r in rules if r.get("name")}

    # Delete removed rules
    existing = frappe.db.sql("""
        SELECT DISTINCT pr.name FROM `tabPricing Rule` pr
        INNER JOIN `tabPricing Rule Item Code` pri ON pri.parent = pr.name
        WHERE pri.item_code = %s AND pr.apply_on = 'Item Code'
    """, item_code, as_dict=True)
    for row in existing:
        if row.name not in keep_names:
            frappe.delete_doc("Pricing Rule", row.name, force=True, ignore_permissions=True)

    saved = 0
    for r in rules:
        if not r.get("rate_or_discount"):
            continue

        # Auto-title
        title = r.get("title") or "{} - {} {}".format(
            item_code,
            r.get("rate_or_discount", "Descuento"),
            int(r.get("min_qty") or 0),
        )

        if r.get("name") and frappe.db.exists("Pricing Rule", r["name"]):
            doc = frappe.get_doc("Pricing Rule", r["name"])
        else:
            doc = frappe.new_doc("Pricing Rule")
            doc.apply_on = "Item Code"
            doc.price_or_product_discount = "Price"
            doc.append("items", {"item_code": item_code})

        doc.title                = title
        doc.disable              = int(r.get("disable") or 0)
        doc.selling              = int(r.get("selling") or 0)
        doc.buying               = int(r.get("buying") or 0)
        doc.min_qty              = float(r.get("min_qty") or 0)
        doc.max_qty              = float(r.get("max_qty") or 0)
        doc.rate_or_discount     = r.get("rate_or_discount") or "Discount Percentage"
        doc.rate                 = float(r.get("rate") or 0)
        doc.discount_percentage  = float(r.get("discount_percentage") or 0)
        doc.discount_amount      = float(r.get("discount_amount") or 0)
        doc.currency             = r.get("currency") or "MXN"
        doc.for_price_list       = r.get("for_price_list") or None
        doc.customer             = r.get("customer") or None
        doc.valid_from           = r.get("valid_from") or None
        doc.valid_upto           = r.get("valid_upto") or None
        doc.company              = r.get("company") or None

        doc.flags.ignore_permissions = True
        doc.flags.ignore_links       = True
        doc.flags.ignore_mandatory   = True
        if doc.name and frappe.db.exists("Pricing Rule", doc.name):
            doc.save()
        else:
            doc.insert()
        saved += 1

    frappe.db.commit()
    return {"saved": saved}


@frappe.whitelist()
def save_item_prices(item_code, prices):
    """Replace all Item Price records for this item with the provided list."""
    import json
    if isinstance(prices, str):
        prices = json.loads(prices)

    stock_uom  = frappe.db.get_value("Item", item_code, "stock_uom") or ""
    item_name  = frappe.db.get_value("Item", item_code, "item_name") or ""

    # Build set of names that should survive
    keep_names = {row["name"] for row in prices if row.get("name")}

    # Delete removed records
    existing = frappe.get_all("Item Price", filters={"item_code": item_code}, pluck="name")
    for name in existing:
        if name not in keep_names:
            frappe.delete_doc("Item Price", name, force=True, ignore_permissions=True)

    saved  = 0
    errors = []

    for row in prices:
        price_list = row.get("price_list")
        rate       = row.get("price_list_rate")
        if not price_list or rate is None or rate == "":
            continue

        # Validate price list exists before trying to save
        if not frappe.db.exists("Price List", price_list):
            errors.append(f"Lista de precios no encontrada: '{price_list}'")
            continue

        pl_currency = frappe.db.get_value("Price List", price_list, "currency") or "MXN"
        currency    = row.get("currency") or pl_currency

        def _set_common(doc):
            doc.price_list      = price_list
            doc.price_list_rate = float(rate)
            doc.uom             = row.get("uom") or stock_uom or ""
            doc.currency        = currency
            doc.customer        = row.get("customer") or ""
            doc.supplier        = row.get("supplier") or ""
            doc.valid_from      = row.get("valid_from") or None
            doc.valid_upto      = row.get("valid_upto") or None
            doc.note            = row.get("note") or ""
            # Skip Frappe link + mandatory validation — we already checked manually
            doc.flags.ignore_permissions = True
            doc.flags.ignore_links       = True
            doc.flags.ignore_mandatory   = True

        try:
            if row.get("name") and frappe.db.exists("Item Price", row["name"]):
                doc = frappe.get_doc("Item Price", row["name"])
                _set_common(doc)
                doc.save()
            else:
                doc = frappe.new_doc("Item Price")
                doc.item_code = item_code
                doc.item_name = item_name
                _set_common(doc)
                doc.insert()

            # ERPNext's before_save hook clears supplier for selling-only price lists
            # and clears customer for buying-only price lists. Force-write them back
            # directly to the DB after the save to preserve what the user entered.
            supplier_val = row.get("supplier") or ""
            customer_val = row.get("customer") or ""
            if supplier_val or customer_val:
                frappe.db.set_value(
                    "Item Price",
                    doc.name,
                    {"supplier": supplier_val, "customer": customer_val},
                    update_modified=False,
                )

            saved += 1
        except Exception as exc:
            errors.append(str(exc))

    frappe.db.commit()

    if errors and saved == 0:
        frappe.throw("Errores al guardar precios: " + "; ".join(errors))

    return {"saved": saved, "errors": errors}


@frappe.whitelist()
def save_item_uoms(item_code, uoms):
    """Replace the UOM conversion table (Item.uoms child) for an item."""
    import json
    if isinstance(uoms, str):
        uoms = json.loads(uoms)

    doc = frappe.get_doc("Item", item_code)

    # Replace entire child table
    doc.uoms = []
    for row in uoms:
        uom = row.get("uom") or ""
        factor = float(row.get("conversion_factor") or 1)
        if uom and uom != doc.stock_uom:
            doc.append("uoms", {"uom": uom, "conversion_factor": factor})

    doc.flags.ignore_permissions = True
    doc.flags.ignore_links       = True
    doc.flags.ignore_mandatory   = True
    doc.save()
    frappe.db.commit()
    return {"saved": len(doc.uoms)}


@frappe.whitelist()
def get_item(item_code):
    """Return full item data for the SPA detail view."""
    doc = frappe.get_doc("Item", item_code)

    def row_to_dict(row, fields):
        return {f: row.get(f) for f in fields}

    item_defaults = [
        row_to_dict(r, ["company", "default_warehouse", "default_price_list",
                        "buying_cost_center", "selling_cost_center", "default_supplier"])
        for r in doc.item_defaults
    ]

    supplier_items = [
        row_to_dict(r, ["supplier", "supplier_part_no", "supplier_part_name", "uom"])
        for r in doc.supplier_items
    ]

    taxes = [
        row_to_dict(r, ["item_tax_template"])
        for r in doc.taxes
    ]

    # UOM Conversion Table (child: doc.uoms)
    uom_conversions = [
        {"uom": r.uom, "conversion_factor": float(r.conversion_factor or 1)}
        for r in doc.uoms
    ]

    # Item Prices (separate doctype)
    item_prices = frappe.get_all(
        "Item Price",
        fields=["name", "price_list", "price_list_rate", "currency", "uom",
                "valid_from", "valid_upto", "customer", "supplier", "note"],
        filters={"item_code": item_code},
        order_by="price_list asc",
    )

    # Pricing Rules
    pricing_rules = frappe.db.sql("""
        SELECT DISTINCT pr.name, pr.title, pr.disable, pr.selling, pr.buying,
               pr.min_qty, pr.max_qty, pr.rate_or_discount,
               pr.rate, pr.discount_percentage, pr.discount_amount,
               pr.currency, pr.for_price_list, pr.customer,
               pr.valid_from, pr.valid_upto, pr.company
        FROM `tabPricing Rule` pr
        INNER JOIN `tabPricing Rule Item Code` pri ON pri.parent = pr.name
        WHERE pri.item_code = %s AND pr.apply_on = 'Item Code'
        ORDER BY pr.min_qty ASC, pr.creation ASC
    """, item_code, as_dict=True)

    return {
        "name": doc.name,
        "item_code": doc.item_code,
        "item_name": doc.item_name,
        "item_group": doc.item_group,
        "stock_uom": doc.stock_uom,
        "disabled": doc.disabled,
        "is_stock_item": doc.is_stock_item,
        "is_sales_item": doc.is_sales_item,
        "is_purchase_item": doc.is_purchase_item,
        "include_item_in_manufacturing": doc.include_item_in_manufacturing,
        "is_sub_contracted_item": doc.is_sub_contracted_item,
        "description": doc.description,
        "image": doc.image,
        "brand": doc.brand,
        "standard_rate": doc.standard_rate,
        "weight_per_unit": doc.weight_per_unit,
        "weight_uom": doc.weight_uom,
        "sales_uom": doc.sales_uom,
        "max_discount": doc.max_discount,
        "purchase_uom": doc.purchase_uom,
        "min_order_qty": doc.min_order_qty,
        "lead_time_days": doc.lead_time_days,
        "has_batch_no": doc.has_batch_no,
        "batch_number_series": doc.batch_number_series,
        "has_serial_no": doc.has_serial_no,
        "serial_no_series": doc.serial_no_series,
        "default_bom": doc.default_bom,
        "country_of_origin": doc.country_of_origin,
        "customs_tariff_number": doc.customs_tariff_number,
        "mx_product_service_key": getattr(doc, "mx_product_service_key", None),
        "creation": str(doc.creation),
        "modified": str(doc.modified),
        "item_defaults": item_defaults,
        "supplier_items": supplier_items,
        "uom_conversions": uom_conversions,
        "item_prices": item_prices,
        "pricing_rules": pricing_rules,
        "taxes": taxes,
    }


@frappe.whitelist()
def update_item(item_code, data):
    """Update scalar fields of an existing Item."""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Item", item_code)

    editable_fields = [
        "item_name", "item_group", "stock_uom", "disabled", "brand", "description",
        "is_stock_item", "is_sales_item", "is_purchase_item",
        "include_item_in_manufacturing", "is_sub_contracted_item",
        "standard_rate", "weight_per_unit", "weight_uom",
        "has_batch_no", "batch_number_series",
        "has_serial_no", "serial_no_series",
        "country_of_origin", "customs_tariff_number",
        "mx_product_service_key",
        "default_bom",
    ]

    for field in editable_fields:
        if field in data:
            setattr(doc, field, data[field])

    doc.flags.ignore_permissions = True
    doc.flags.ignore_links       = True
    doc.flags.ignore_mandatory   = True
    doc.save()
    frappe.db.commit()
    return {"updated": True, "item_code": item_code}


@frappe.whitelist()
def create_item(data):
    """Create a new Item with all fields including prices, suppliers, and Mexico Compliance."""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.new_doc("Item")

    # Core fields
    scalar_fields = [
        "item_code", "item_name", "item_group", "stock_uom", "disabled",
        "is_stock_item", "is_fixed_asset", "description", "brand",
        "is_purchase_item", "purchase_uom", "min_order_qty", "lead_time_days",
        "is_customer_provided_item", "customer",
        "is_sales_item", "sales_uom", "standard_rate", "max_discount",
        "default_bom", "is_sub_contracted_item", "include_item_in_manufacturing",
        "has_batch_no", "has_serial_no",
        "weight_per_unit", "weight_uom",
        "country_of_origin", "customs_tariff_number",
        "enable_deferred_revenue", "enable_deferred_expense",
        "mx_product_service_key",
    ]

    for field in scalar_fields:
        val = data.get(field)
        if val is not None and val != "":
            setattr(doc, field, val)

    # Item Defaults (child table)
    is_service = data.get("item_group") == "Servicios"
    for row in data.get("item_defaults") or []:
        expense_account = row.get("expense_account")
        if not expense_account and is_service:
            # Servicios (p. ej. maquila de subcontratación): capitalizar el costo en el
            # inventario vía "Gastos incluidos en la valoración", NUNCA en Costo de Ventas
            # (que solo debe tocarse al vender, no al producir).
            expense_account = _valuation_expense_account(row.get("company"))
        doc.append("item_defaults", {
            "company": row.get("company"),
            "default_warehouse": row.get("default_warehouse"),
            "default_price_list": row.get("default_price_list"),
            "buying_cost_center": row.get("buying_cost_center"),
            "selling_cost_center": row.get("selling_cost_center"),
            "default_supplier": row.get("default_supplier"),
            "expense_account": expense_account,
        })

    # Supplier Items child table
    for row in data.get("supplier_items") or []:
        if row.get("supplier"):
            doc.append("supplier_items", {
                "supplier": row.get("supplier"),
                "supplier_part_no": row.get("supplier_part_no") or "",
                "supplier_part_name": row.get("supplier_part_name") or "",
                "uom": row.get("uom") or "",
            })

    # UOM Conversion Table
    for row in data.get("uom_conversions") or []:
        uom = row.get("uom") or ""
        factor = float(row.get("conversion_factor") or 1)
        if uom and uom != data.get("stock_uom"):
            doc.append("uoms", {"uom": uom, "conversion_factor": factor})

    # Taxes child table
    for row in data.get("taxes") or []:
        if row.get("item_tax_template"):
            doc.append("taxes", {"item_tax_template": row["item_tax_template"]})

    doc.flags.ignore_permissions = True
    doc.insert()

    # Item Price records (created separately after item is saved)
    price_errors = []
    for row in data.get("item_prices") or []:
        price_list = row.get("price_list")
        rate = row.get("price_list_rate")
        if not price_list or rate is None or rate == "":
            continue
        try:
            price_doc = frappe.new_doc("Item Price")
            price_doc.item_code = doc.item_code
            price_doc.item_name = doc.item_name
            price_doc.price_list = price_list
            price_doc.uom = row.get("uom") or doc.stock_uom
            price_doc.price_list_rate = float(rate)
            price_doc.currency = row.get("currency") or frappe.db.get_value("Price List", price_list, "currency") or "MXN"
            if row.get("valid_from"):  price_doc.valid_from  = row["valid_from"]
            if row.get("valid_upto"):  price_doc.valid_upto  = row["valid_upto"]
            if row.get("customer"):    price_doc.customer    = row["customer"]
            if row.get("supplier"):    price_doc.supplier    = row["supplier"]
            if row.get("note"):        price_doc.note        = row["note"]
            price_doc.flags.ignore_permissions = True
            price_doc.flags.ignore_links       = True
            price_doc.flags.ignore_mandatory   = True
            price_doc.insert()

            # Force-write supplier/customer back — ERPNext's before_save clears
            # supplier for selling-only lists and customer for buying-only lists.
            supplier_val = row.get("supplier") or ""
            customer_val = row.get("customer") or ""
            if supplier_val or customer_val:
                frappe.db.set_value(
                    "Item Price",
                    price_doc.name,
                    {"supplier": supplier_val, "customer": customer_val},
                    update_modified=False,
                )
        except Exception as e:
            price_errors.append(str(e))

    # Pricing Rules (created after item is inserted)
    for r in data.get("pricing_rules") or []:
        if not r.get("rate_or_discount"):
            continue
        try:
            title = r.get("title") or "{} - {} {}".format(
                doc.item_code, r.get("rate_or_discount", "Descuento"), int(r.get("min_qty") or 0)
            )
            rule = frappe.new_doc("Pricing Rule")
            rule.title               = title
            rule.apply_on            = "Item Code"
            rule.price_or_product_discount = "Price"
            rule.selling             = int(r.get("selling") or 0)
            rule.buying              = int(r.get("buying") or 0)
            rule.min_qty             = float(r.get("min_qty") or 0)
            rule.max_qty             = float(r.get("max_qty") or 0)
            rule.rate_or_discount    = r.get("rate_or_discount") or "Discount Percentage"
            rule.rate                = float(r.get("rate") or 0)
            rule.discount_percentage = float(r.get("discount_percentage") or 0)
            rule.discount_amount     = float(r.get("discount_amount") or 0)
            rule.currency            = r.get("currency") or "MXN"
            if r.get("for_price_list"): rule.for_price_list = r["for_price_list"]
            if r.get("customer"):       rule.customer       = r["customer"]
            if r.get("valid_from"):     rule.valid_from     = r["valid_from"]
            if r.get("valid_upto"):     rule.valid_upto     = r["valid_upto"]
            if r.get("company"):        rule.company        = r["company"]
            rule.append("items", {"item_code": doc.item_code})
            rule.flags.ignore_permissions = True
            rule.flags.ignore_links       = True
            rule.flags.ignore_mandatory   = True
            rule.insert()
        except Exception as e:
            price_errors.append(f"Pricing rule: {e}")

    frappe.db.commit()

    result = {"name": doc.name, "item_code": doc.item_code}
    if price_errors:
        result["price_warnings"] = price_errors
    return result
