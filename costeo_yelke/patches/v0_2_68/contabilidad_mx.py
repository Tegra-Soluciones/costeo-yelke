"""Configuración contable de la operación (auditoría del 2026-10-27), idempotente:

1. Cuenta por cobrar de clientes: "CUENTAS POR COBRAR CLIENTES" como la de la
   compañía (YELKE TEXTILES cobraba en DEUDORES VARIOS). Se crea si no existe.
2. IVA en base a flujo de efectivo (api/cuentas_mx.py): cuatro cuentas por compañía
   -- acreditable pendiente de pago / pagado, trasladado no cobrado / cobrado -- en
   vez de una sola "IVA". Las plantillas de compras van a la acreditable pendiente y
   las de ventas a la trasladada no cobrada; el paso a pagado/cobrado lo hace la app
   al registrar cada pago. Campos en la póliza para ligarla a su factura.
3. Valuación por costo promedio (decisión de Yelke del 2026-10-13): con FIFO el
   recibo del taller valúa cada material por su lado y las capas del almacén del
   taller se descuadran.
4. Redondeo: si Global Defaults lo desactiva pero nunca se guardó, los documentos
   nuevos seguían redondeando al peso (falta el Property Setter que pone ERPNext al
   guardarlo).

Lo ya contabilizado no se toca: aplica de aquí en adelante.
"""
import frappe

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from costeo_yelke.api.cuentas_mx import (
    ACRED_PAGADO, ACRED_PENDIENTE, CXC_CLIENTES, FAMILIA_IVA, TRAS_COBRADO, TRAS_NO_COBRADO, cuenta,
)


def execute():
    _campos_poliza()
    for c in frappe.get_all("Company", fields=["name", "abbr", "default_currency"]):
        for paso in (_cuenta_por_cobrar, _iva_separado):
            try:
                paso(c)
            except Exception:
                frappe.log_error(title=f"v0_2_68 contabilidad_mx: {paso.__name__} {c.name}")
    _valuacion_costo_promedio()
    _redondeo()
    frappe.clear_cache()


def _nueva_cuenta(company, nombre, padre, root_type, account_type, moneda):
    acc = frappe.get_doc({"doctype": "Account", "company": company, "account_name": nombre, "parent_account": padre,
                          "is_group": 0, "root_type": root_type, "account_type": account_type,
                          "account_currency": moneda})
    acc.flags.ignore_permissions = True
    acc.insert()
    return acc.name


def _grupo_impuestos(company, root_type):
    """Dónde van las cuentas nuevas de IVA: junto a las de IVA que ya tenga el catálogo
    de ese lado (activo o pasivo); si no hay, el primer grupo de impuestos."""
    junto = frappe.db.get_value("Account", {"company": company, "is_group": 0, "root_type": root_type,
                                            "account_name": ["in", list(FAMILIA_IVA)]}, "parent_account",
                                order_by="lft asc")
    return junto or frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": root_type,
                                                    "account_name": ["like", "%impuesto%"]}, "name", order_by="lft asc")


# ── 1. Cuenta por cobrar ─────────────────────────────────────────────────────
def _cuenta_por_cobrar(c):
    actual = frappe.db.get_value("Company", c.name, "default_receivable_account")
    cuenta = frappe.db.get_value("Account", {"company": c.name, "account_name": CXC_CLIENTES, "is_group": 0})
    if not cuenta:
        padre = frappe.db.get_value("Account", actual, "parent_account") if actual else \
            frappe.db.get_value("Account", {"company": c.name, "is_group": 1, "root_type": "Asset",
                                            "account_name": ["like", "%cobrar%"]}, "name", order_by="lft asc")
        if not padre:
            return
        cuenta = _nueva_cuenta(c.name, CXC_CLIENTES, padre, "Asset", "Receivable", c.default_currency)
    elif frappe.db.get_value("Account", cuenta, "account_type") != "Receivable":
        frappe.db.set_value("Account", cuenta, "account_type", "Receivable")
    if actual == cuenta:
        return
    frappe.db.set_value("Company", c.name, "default_receivable_account", cuenta)
    # Clientes o grupos que apuntaban a la cuenta vieja como la suya en esta compañía.
    if actual:
        for pa in frappe.get_all("Party Account", filters={"company": c.name, "account": actual,
                                                           "parenttype": ["in", ["Customer", "Customer Group"]]},
                                 pluck="name"):
            frappe.db.set_value("Party Account", pa, "account", cuenta)


# ── 2. IVA en base a flujo de efectivo ───────────────────────────────────────
def _campos_poliza():
    # Data y no Link: una liga dura impediría cancelar la factura (la póliza de IVA
    # se cancela junto con ella, ver cuentas_mx.al_mover_factura).
    create_custom_fields({"Journal Entry": [
        {"fieldname": "iva_factura_doctype", "label": "IVA pagado/cobrado de (tipo)", "fieldtype": "Data",
         "read_only": 1, "no_copy": 1, "insert_after": "user_remark"},
        {"fieldname": "iva_factura", "label": "IVA pagado/cobrado de", "fieldtype": "Data", "read_only": 1,
         "no_copy": 1, "insert_after": "iva_factura_doctype", "search_index": 1},
    ]}, update=True)


def _iva_separado(c):
    activo = _grupo_impuestos(c.name, "Asset")
    generica = cuenta(c.name, "IVA")
    pasivo = (frappe.db.get_value("Account", generica, "parent_account") if generica else None) \
        or _grupo_impuestos(c.name, "Liability")
    if not activo or not pasivo:
        return
    cuentas = {}
    for nombre, padre, root in ((ACRED_PENDIENTE, activo, "Asset"), (ACRED_PAGADO, activo, "Asset"),
                                (TRAS_NO_COBRADO, pasivo, "Liability"), (TRAS_COBRADO, pasivo, "Liability")):
        cuentas[nombre] = cuenta(c.name, nombre) or _nueva_cuenta(c.name, nombre, padre, root, "Tax", c.default_currency)
        # Las plantillas de impuestos solo aceptan cuentas de tipo "Tax".
        if frappe.db.get_value("Account", cuentas[nombre], "account_type") != "Tax":
            frappe.db.set_value("Account", cuentas[nombre], "account_type", "Tax")
    compras, ventas = cuentas[ACRED_PENDIENTE], cuentas[TRAS_NO_COBRADO]
    familia = set(frappe.get_all("Account", filters={"company": c.name, "is_group": 0,
                                                     "account_name": ["in", list(FAMILIA_IVA)]}, pluck="name"))

    # Plantillas de compras -> acreditable pendiente; de ventas -> trasladado no cobrado.
    for hijo, plantilla, destino in (("Purchase Taxes and Charges", "Purchase Taxes and Charges Template", compras),
                                     ("Sales Taxes and Charges", "Sales Taxes and Charges Template", ventas)):
        for fila in frappe.get_all(hijo, filters={"parenttype": plantilla, "account_head": ["in", list(familia)]},
                                   fields=["name", "account_head"]):
            if fila.account_head != destino:
                frappe.db.set_value(hijo, fila.name, "account_head", destino, update_modified=False)
    # Plantilla de impuestos por artículo: sirve en compras y en ventas, así que lleva
    # las dos pendientes con la tasa de IVA que ya tenía.
    for tpl_name in set(frappe.get_all("Item Tax Template Detail", filters={"tax_type": ["in", list(familia)]},
                                       pluck="parent")):
        tpl = frappe.get_doc("Item Tax Template", tpl_name)
        if tpl.get("company") and tpl.company != c.name:
            continue
        tasa = next(t.tax_rate for t in tpl.taxes if t.tax_type in familia)
        tpl.taxes = [t for t in tpl.taxes if t.tax_type not in familia]
        for destino in (compras, ventas):
            tpl.append("taxes", {"tax_type": destino, "tax_rate": tasa})
        tpl.flags.ignore_permissions = True
        tpl.save()


# ── 3. Valuación ─────────────────────────────────────────────────────────────
def _valuacion_costo_promedio():
    if frappe.db.get_single_value("Stock Settings", "valuation_method") == "Moving Average":
        return
    if frappe.db.count("Stock Ledger Entry"):
        # Con movimientos ERPNext no deja cambiarlo desde Stock Settings; el promedio
        # parte de la tasa de valuación del último movimiento, así que sigue continuo.
        frappe.db.set_single_value("Stock Settings", "valuation_method", "Moving Average")
    else:
        ss = frappe.get_single("Stock Settings")
        ss.valuation_method = "Moving Average"
        ss.flags.ignore_permissions = True
        ss.save()


# ── 4. Redondeo ──────────────────────────────────────────────────────────────
def _redondeo():
    if not frappe.db.get_single_value("Global Defaults", "disable_rounded_total"):
        return
    aplicado = frappe.db.get_value("Property Setter", {"doc_type": "Sales Invoice", "field_name": "disable_rounded_total",
                                                       "property": "default"}, "value")
    if aplicado != "1":
        gd = frappe.get_single("Global Defaults")
        gd.flags.ignore_permissions = True
        gd.save()
