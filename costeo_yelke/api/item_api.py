import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, now_datetime, nowdate


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


_ROLES_PRECIO_ACORDADO = {"CEO", "Sales Manager"}
_ROLE_VALIDAR_PRECIO_ACORDADO = "CEO"


def _es_ceo():
    return _ROLE_VALIDAR_PRECIO_ACORDADO in frappe.get_roles()


@frappe.whitelist()
def crear_precio_acordado(item_code, customer, price_list_rate, valid_from, valid_upto=None, price_list=None, costeo=None):
    """Guarda (o extiende) un Item Price para Cliente+Artículo con vigencia -- así un
    pedido recurrente dentro de esa ventana ya no necesita pasar por un Costeo/Cotización
    nuevo: ERPNext toma el precio directamente por la vigencia, sin depender de una
    aprobación por pedido. Si ya existe un precio vigente para ese mismo periodo, lo
    actualiza en vez de duplicarlo.

    Cualquier usuario interno puede CAPTURARLO (queda en borrador, igual que cualquier
    documento sin validar en esta app) -- lo que está restringido es VALIDARLO (ver
    validar_precio_acordado, solo rol CEO). Por eso cada guardado (nuevo o editado)
    regresa el precio a borrador: si alguien ajusta un precio ya validado, tiene que
    volver a pasar por la validación del CEO antes de contar como vigente."""
    price_list = price_list or frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
    stock_uom  = frappe.db.get_value("Item", item_code, "stock_uom") or ""
    item_name  = frappe.db.get_value("Item", item_code, "item_name") or ""

    existing = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "customer": customer, "price_list": price_list, "valid_from": valid_from},
        "name",
    )

    doc = frappe.get_doc("Item Price", existing) if existing else frappe.new_doc("Item Price")
    doc.item_code       = item_code
    doc.item_name       = item_name
    doc.price_list      = price_list
    doc.price_list_rate = float(price_list_rate)
    doc.uom             = stock_uom
    doc.customer        = customer
    doc.valid_from       = valid_from
    doc.valid_upto       = valid_upto or None
    if costeo and frappe.db.has_column("Item Price", "costeo"):
        doc.costeo = costeo
    if frappe.db.has_column("Item Price", "precio_acordado_validado"):
        doc.precio_acordado_validado = 0
    doc.flags.ignore_permissions = True
    doc.flags.ignore_links       = True
    doc.flags.ignore_mandatory   = True

    if doc.is_new():
        doc.insert()
    else:
        doc.save()

    # ERPNext's before_save hook clears `customer` for price lists not marked buying=1 --
    # force it back, same workaround used in save_item_prices above.
    frappe.db.set_value("Item Price", doc.name, "customer", customer, update_modified=False)
    frappe.db.commit()
    return {"name": doc.name, "price_list": price_list}


@frappe.whitelist()
def get_precio_acordado_costeo_status(costeo: str) -> dict:
    """Precios acordados capturados para este costeo (todos los artículos fijados juntos
    desde 'Fijar Precio'), con su estado borrador/validado -- para que el SPA muestre el
    badge y, si el usuario es CEO, el botón de validar."""
    rows = frappe.get_all(
        "Item Price",
        filters={"costeo": costeo},
        fields=["name", "item_code", "item_name", "price_list_rate", "valid_upto", "precio_acordado_validado"],
        order_by="item_code asc",
    )
    return {
        "items": rows,
        "todos_validados": bool(rows) and all(r.precio_acordado_validado for r in rows),
        "es_ceo": _es_ceo(),
    }


@frappe.whitelist()
def validar_precios_acordados_costeo(costeo: str) -> dict:
    """Valida (aprueba) TODOS los precios acordados capturados para este costeo de un
    jalón -- solo un usuario con rol CEO puede hacerlo. Mientras no estén validados,
    _precio_acordado_vigente (costeo_api.py) no los cuenta como vigentes, así que
    generar_replica_ov los sigue tratando como si no existiera precio acordado."""
    if not _es_ceo():
        frappe.throw(_("Solo un usuario con rol CEO puede validar el precio acordado."))
    names = frappe.get_all("Item Price", filters={"costeo": costeo}, pluck="name")
    if not names:
        frappe.throw(_("No hay ningún precio acordado capturado para este costeo."))
    for name in names:
        frappe.db.set_value("Item Price", name, "precio_acordado_validado", 1, update_modified=False)
    frappe.db.commit()
    return {"ok": True, "validated": len(names)}


# ─────────────────────────────────────────────────────────────────────────────
# Recordatorios de vigencia del precio acordado
# ─────────────────────────────────────────────────────────────────────────────

def _precio_acordado_actual():
    """Fila más reciente (por valid_upto) de cada Item Price con cliente -- mismo
    criterio que _precio_acordado_vigente en costeo_api.py, para no avisar de un precio
    viejo que ya quedó superado por uno posterior con distinta vigencia."""
    price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
    return frappe.db.sql(
        """
        select ip.name as item_price, ip.item_code, ip.customer, ip.valid_upto,
               ip.price_list_rate, ip.costeo
        from `tabItem Price` ip
        inner join (
            select item_code, customer, max(valid_upto) as max_upto
            from `tabItem Price`
            where price_list=%(pl)s and customer is not null and customer != '' and valid_upto is not null
            group by item_code, customer
        ) latest
          on latest.item_code = ip.item_code
         and latest.customer = ip.customer
         and latest.max_upto = ip.valid_upto
        where ip.price_list=%(pl)s
        """,
        {"pl": price_list},
        as_dict=True,
    )


def _crear_recordatorio_si_falta(row, tipo_aviso):
    """Crea el recordatorio (con su Notification Log para CEO/Sales Manager) si no
    existe ya uno para esta misma fila de Item Price + tipo de aviso -- así una corrida
    del scheduler que se repite (o que corre varios días después de lo esperado) no
    duplica avisos."""
    if frappe.db.exists("Precio Acordado Recordatorio", {"item_price": row.item_price, "tipo_aviso": tipo_aviso}):
        return

    item_name = frappe.db.get_value("Item", row.item_code, "item_name") or row.item_code
    doc = frappe.get_doc({
        "doctype": "Precio Acordado Recordatorio",
        "customer": row.customer,
        "item_code": row.item_code,
        "item_name": item_name,
        "costeo": row.get("costeo"),
        "item_price": row.item_price,
        "price_list_rate": row.price_list_rate,
        "valid_upto": row.valid_upto,
        "tipo_aviso": tipo_aviso,
        "estado": "Pendiente",
    })
    doc.flags.ignore_permissions = True
    doc.insert()

    vence_texto = "vence" if tipo_aviso == "Un mes antes" else "venció"
    subject = _("El precio acordado de {0} con {1} {2} el {3}").format(
        item_name, row.customer, vence_texto, formatdate(row.valid_upto),
    )
    usuarios = set(frappe.get_all(
        "Has Role",
        filters={"role": ["in", list(_ROLES_PRECIO_ACORDADO)], "parenttype": "User"},
        pluck="parent",
    ))
    for user in usuarios:
        if not frappe.db.get_value("User", user, "enabled"):
            continue
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": subject,
            "for_user": user,
            "type": "Alert",
            "document_type": "Precio Acordado Recordatorio",
            "document_name": doc.name,
        }).insert(ignore_permissions=True)


def revisar_vigencias_precio_acordado():
    """Diario (scheduler, ver hooks.py): avisa 1 mes antes y el día que vence un precio
    acordado. El '<=' (en vez de '==') hace el chequeo tolerante a que el cron no corra
    exactamente ese día -- el dedupe de _crear_recordatorio_si_falta evita duplicados en
    las corridas siguientes."""
    hoy = getdate(nowdate())
    for row in _precio_acordado_actual():
        dias = (getdate(row.valid_upto) - hoy).days
        if dias <= 30:
            _crear_recordatorio_si_falta(row, "Un mes antes")
        if dias <= 0:
            _crear_recordatorio_si_falta(row, "Día de vencimiento")


def _customer_primary_contact(customer):
    """Email/teléfono del contacto del cliente -- vía Dynamic Link -> Contact (no hay
    selector de contacto aquí como en el SPA, así que se resuelve del lado servidor)."""
    contact_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
        "parent",
    )
    if not contact_name:
        return {"email": None, "phone": None}
    c = frappe.db.get_value("Contact", contact_name, ["email_id", "mobile_no", "phone"], as_dict=True) or {}
    return {"email": c.get("email_id"), "phone": c.get("mobile_no") or c.get("phone")}


@frappe.whitelist()
def enviar_recordatorio_precio_email(recordatorio):
    """Envía al cliente un correo avisando la vigencia de su precio acordado -- mismo
    patrón de frappe.sendmail usado en costeo_api.enviar_por_correo, sin adjunto (este
    aviso no tiene un documento que mandar)."""
    doc = frappe.get_doc("Precio Acordado Recordatorio", recordatorio)
    contact = _customer_primary_contact(doc.customer)
    if not contact.get("email"):
        frappe.throw(_("El cliente {0} no tiene un correo de contacto registrado.").format(doc.customer))

    vence_texto = "vence" if doc.tipo_aviso == "Un mes antes" else "venció"
    message = _(
        "Estimado cliente,<br><br>Le recordamos que el precio acordado de <b>{0}</b> "
        "{1} el <b>{2}</b>. Quedamos atentos para renovar las condiciones si así lo desea."
    ).format(doc.item_name or doc.item_code, vence_texto, formatdate(doc.valid_upto))
    frappe.sendmail(
        recipients=[contact["email"]],
        subject=_("Vigencia de precio acordado -- {0}").format(doc.item_name or doc.item_code),
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )
    doc.db_set("enviado_email_el", now_datetime(), update_modified=False)
    doc.db_set("estado", "Enviado", update_modified=False)
    return {"ok": True, "email": contact["email"]}


@frappe.whitelist()
def get_recordatorio_whatsapp_link(recordatorio):
    """Arma el link manual de wa.me con el mensaje precargado -- mismo patrón ya usado
    en el SPA (useDocumentActions.js: descarga PDF + abre wa.me); aquí no hay PDF que
    adjuntar, solo el mensaje. El envío en sí lo hace el usuario a mano en WhatsApp Web,
    por eso marcar_recordatorio_enviado se llama aparte, después de abrir el link."""
    from urllib.parse import quote

    doc = frappe.get_doc("Precio Acordado Recordatorio", recordatorio)
    contact = _customer_primary_contact(doc.customer)
    phone = "".join(ch for ch in (contact.get("phone") or "") if ch.isdigit())
    if not phone:
        frappe.throw(_("El cliente {0} no tiene un teléfono de contacto registrado.").format(doc.customer))

    vence_texto = "vence" if doc.tipo_aviso == "Un mes antes" else "venció"
    message = _("Hola, le recordamos que el precio acordado de *{0}* {1} el {2}. Quedamos atentos.").format(
        doc.item_name or doc.item_code, vence_texto, formatdate(doc.valid_upto),
    )
    return {"url": f"https://wa.me/{phone}?text={quote(message)}"}


@frappe.whitelist()
def marcar_recordatorio_enviado(recordatorio, canal):
    """Marca un recordatorio como enviado por el canal indicado -- usado por el botón de
    WhatsApp, que al ser un flujo manual (abrir wa.me) no tiene confirmación real del
    lado servidor."""
    if canal not in ("email", "whatsapp"):
        frappe.throw(_("Canal inválido."))
    field = "enviado_email_el" if canal == "email" else "enviado_whatsapp_el"
    frappe.db.set_value("Precio Acordado Recordatorio", recordatorio, {
        field: now_datetime(),
        "estado": "Enviado",
    })
    return {"ok": True}


@frappe.whitelist()
def descartar_recordatorio(recordatorio):
    """Cierra un recordatorio que ya no aplica (ej. el cliente ya renovó por otro medio)."""
    frappe.db.set_value("Precio Acordado Recordatorio", recordatorio, "estado", "Descartado")
    return {"ok": True}


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
        # product_key es el campo real y obligatorio (usado por mexico_einvoice para el CFDI).
        # mx_product_service_key es una columna legada (ya no tiene DocField/Custom Field
        # asociado, pero sigue viva en la tabla) que otra app de facturación en producción
        # todavia lee -- si product_key esta vacio (item viejo, cargado antes del cambio de
        # campo), se usa como respaldo para no perder el dato en el formulario.
        "mx_product_service_key": doc.get("product_key") or frappe.db.get_value("Item", doc.name, "mx_product_service_key"),
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
        "default_bom",
    ]

    for field in editable_fields:
        if field in data:
            setattr(doc, field, data[field])

    # "mx_product_service_key" (nombre del campo en la SPA) se guarda en el Item real
    # como "product_key" (obligatorio, usado por mexico_einvoice para el CFDI) -- ver
    # nota completa en create_item(). Se replica también en la columna legada
    # "mx_product_service_key" (sin DocField propio, se escribe vía SQL directo) porque
    # otra app de facturación en producción todavía lee de ahí.
    sat_key = data.get("mx_product_service_key")
    if "mx_product_service_key" in data:
        doc.product_key = sat_key

    doc.flags.ignore_permissions = True
    doc.flags.ignore_links       = True
    doc.flags.ignore_mandatory   = True
    doc.save()
    if "mx_product_service_key" in data:
        frappe.db.set_value("Item", doc.name, "mx_product_service_key", sat_key, update_modified=False)
    frappe.db.commit()
    return {"updated": True, "item_code": item_code}


@frappe.whitelist()
def get_tela_conversion_fields(item_code: str) -> dict:
    """Metros por kilo guardados en el Item, para precargar el conversor $/kg -> $/m
    de telas en el Costeo. El "item" de un renglón de materia prima en el Costeo es
    texto libre (no siempre corresponde todavía a un Item real) -- por eso no truena
    si no existe, solo regresa vacío para que el conversor arranque en blanco."""
    if not item_code or not frappe.db.exists("Item", item_code):
        return {}
    return {"metros_por_kilo": frappe.db.get_value("Item", item_code, "metros_por_kilo")}


@frappe.whitelist()
def guardar_tela_conversion(item_code: str, metros_por_kilo=None) -> dict:
    """Guarda metros_por_kilo en el Item para no volver a capturarlo la próxima vez
    que esa misma tela se use en otro costeo."""
    if not item_code or not frappe.db.exists("Item", item_code):
        frappe.throw(_('El artículo "{0}" todavía no existe como Item -- créalo primero para poder guardar la conversión.').format(item_code))
    # metros_por_kilo es una columna Float estándar de Frappe -- no acepta NULL, solo 0
    # como "sin capturar" (mismo criterio que ya usa get_tela_conversion_fields al leer).
    frappe.db.set_value("Item", item_code, "metros_por_kilo", flt(metros_por_kilo), update_modified=False)
    return {"ok": True}


@frappe.whitelist()
def create_item(data, ignore_mandatory=False):
    """Create a new Item with all fields including prices, suppliers, and Mexico Compliance.

    ignore_mandatory: usado por materializaciones parciales (p. ej. el Producto
    Terminado de un Costeo al pasar a cotización), que a propósito solo llenan un
    subconjunto mínimo de campos y dejan el resto (como la clave SAT) para
    completarse después, antes de producción/facturación."""
    import json
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(ignore_mandatory, str):
        ignore_mandatory = ignore_mandatory.lower() in ("1", "true", "yes")

    doc = frappe.new_doc("Item")

    # Core fields
    scalar_fields = [
        "item_code", "item_name", "item_group", "stock_uom", "disabled",
        "is_stock_item", "is_fixed_asset", "description", "brand", "image",
        "is_purchase_item", "purchase_uom", "min_order_qty", "lead_time_days",
        "is_customer_provided_item", "customer",
        "is_sales_item", "sales_uom", "standard_rate", "max_discount",
        "default_bom", "is_sub_contracted_item", "include_item_in_manufacturing",
        "has_batch_no", "has_serial_no",
        "weight_per_unit", "weight_uom",
        "country_of_origin", "customs_tariff_number",
        "enable_deferred_revenue", "enable_deferred_expense",
        "over_delivery_receipt_allowance", "over_billing_allowance",
    ]

    for field in scalar_fields:
        val = data.get(field)
        if val is not None and val != "":
            setattr(doc, field, val)

    # La SPA llama a este campo "mx_product_service_key" (nombre visible en el
    # formulario), pero el campo real en Item (custom field de mexico_einvoice,
    # obligatorio, usado para el CFDI) es "product_key" -- se mapea aparte para no
    # perder el valor. También se replica más abajo en la columna legada
    # "mx_product_service_key" (ya no tiene DocField propio, pero otra app de
    # facturación en producción todavía lee de ahí).
    sat_key = data.get("mx_product_service_key")
    if sat_key:
        doc.product_key = sat_key

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
    if ignore_mandatory:
        doc.flags.ignore_mandatory = True
    doc.insert()

    if sat_key:
        frappe.db.set_value("Item", doc.name, "mx_product_service_key", sat_key, update_modified=False)

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
