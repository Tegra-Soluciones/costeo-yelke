"""Configuración contable de una compañía para que el flujo de Costeo Yelke cierre
completo: inventario perpetuo, cuentas por defecto, impuestos por tipo de proveedor y
almacenes. Nació de la auditoría de YELKE TEXTILES (sandbox, 2026-10-01): sin
inventario perpetuo ni cuentas de inventario la compañía tenía $1.5M en el libro de
inventario y $0 en contabilidad, y los fletes caían en Costo de Ventas.

- ``diagnostico_compania`` es de SOLO LECTURA: lista lo que falta. La usa el aviso
  del SPA y sirve para revisar compañías reales antes de un despliegue.
- ``configurar_compania`` es idempotente (se puede correr varias veces): crea lo que
  falta y asigna los defaults. NO toca compañías con movimientos sin que se pida
  explícitamente -- prender el inventario perpetuo con existencias previas exige un
  procedimiento contable aparte.
"""

import frappe
from frappe import _

# Cuentas que la app busca por NOMBRE literal (ver costeo_api: _payable_account_para_proveedor,
# _crear_poliza_flete_remision, _crear_poliza_overhead_venta).
CUENTA_PROVEEDORES = "CUENTAS POR PAGAR PROVEEDORES"
CUENTA_FLETES = "TRANSPORTE Y FLETES"
CUENTA_OVERHEAD = "GASTOS INDIRECTOS ABSORBIDOS"
CUENTA_REDONDEO = "REDONDEO"

# Impuestos (catálogo "Mexico - Plan de Cuentas").
CUENTA_IVA_ACREDITABLE = "IVA ACREDITABLE o PAGADO A PROVEEDORES"
CUENTA_IVA_TRASLADADO = "IVA POR TRASLADAR o COBRADO"
CUENTA_ISR_RETENIDO = "RETENCIONES ISR  PROVEEDORES"
CUENTA_IVA_RETENIDO = "IVA RETENIDO PROVEEDORES"  # hoja nueva bajo el grupo RETENCIONES VARIAS

# Categorías de impuesto de proveedor (globales en ERPNext). El nombre dice cuándo
# elegirla: es lo único que se captura en el proveedor, y de ahí la Tax Rule decide
# la plantilla de cada compra.
CATEGORIA_FORMAL = "CON FACTURA - IVA 16%"
CATEGORIA_RETENCION = "CON FACTURA - IVA 16% CON RETENCIONES"
CATEGORIA_INFORMAL = "SIN FACTURA - SIN IVA"

PLANTILLA_COMPRA_FORMAL = "COMPRA CON FACTURA IVA 16%"
PLANTILLA_COMPRA_RETENCION = "COMPRA CON FACTURA IVA 16% CON RETENCIONES"
PLANTILLA_COMPRA_INFORMAL = "COMPRA SIN FACTURA SIN IVA"
PLANTILLA_VENTA = "VENTA IVA 16%"

ALMACEN_MP = "Materia Prima"
ALMACEN_WIP = "Trabajo en Proceso"
ALMACEN_PT = "Producto Terminado"
# Los que crea ERPNext al dar de alta la compañía y que la app no usa: se desactivan
# para que nadie mande material ahí por error (el árbol queda con un solo juego).
ALMACENES_NATIVOS_SOBRANTES = ("Stores", "Work In Progress", "Finished Goods")


def _account(company, account_name):
    return frappe.db.get_value("Account", {"company": company, "account_name": account_name}, "name")


def _account_by_type(company, account_type):
    return frappe.db.get_value(
        "Account", {"company": company, "account_type": account_type, "is_group": 0}, "name"
    )


def _warehouse(company, warehouse_name):
    return frappe.db.get_value(
        "Warehouse",
        {"company": company, "warehouse_name": warehouse_name, "is_group": 0, "disabled": 0},
        "name",
    )


@frappe.whitelist()
def diagnostico_compania(company: str) -> dict:
    """Qué le falta a la compañía para que inventario y contabilidad cuadren.
    Regresa {ok, faltantes: [texto]} -- solo lectura."""
    if not company or not frappe.db.exists("Company", company):
        # Sin faltantes: el SPA consulta mientras se teclea el nombre y no debe avisar
        # de nada hasta que la compañía sea una real.
        return {"ok": False, "existe": False, "faltantes": []}

    c = frappe.get_cached_doc("Company", company)
    faltantes = []

    if not c.enable_perpetual_inventory:
        faltantes.append(_("Inventario perpetuo desactivado: el inventario no se refleja en contabilidad."))

    campos = {
        "default_inventory_account": _("Cuenta de inventario"),
        "stock_received_but_not_billed": _("Cuenta de recibido no facturado"),
        "expenses_included_in_valuation": _("Cuenta de gastos incluidos en la valuación (fletes)"),
        "stock_adjustment_account": _("Cuenta de ajuste de inventario"),
        "default_expense_account": _("Cuenta de costo de ventas"),
        "default_income_account": _("Cuenta de ingresos"),
        "default_receivable_account": _("Cuenta de clientes"),
        "default_payable_account": _("Cuenta de proveedores"),
        "round_off_account": _("Cuenta de redondeo"),
        "cost_center": _("Centro de costos"),
    }
    for campo, etiqueta in campos.items():
        if not c.get(campo):
            faltantes.append(_("Falta: {0}").format(etiqueta))

    for nombre in (CUENTA_PROVEEDORES, CUENTA_FLETES, CUENTA_OVERHEAD):
        if not _account(company, nombre):
            faltantes.append(_("Falta la cuenta '{0}'").format(nombre))

    if not frappe.db.exists("Purchase Taxes and Charges Template", {"company": company, "disabled": 0}):
        faltantes.append(_("No hay plantilla de impuestos de compra"))
    if not frappe.db.exists("Sales Taxes and Charges Template", {"company": company, "disabled": 0}):
        faltantes.append(_("No hay plantilla de impuestos de venta"))

    # Mismo buscador que usa la app (acepta variantes de nombre: Stores, WIP,
    # Finished Goods...), para no reportar faltantes que en la práctica sí encuentra.
    from costeo_yelke.api.costeo_api import get_company_defaults
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _guess_finished_goods_warehouse

    alm = get_company_defaults(company)
    if not alm.get("almacen_materias_primas"):
        faltantes.append(_("Falta el almacén de materia prima"))
    if not alm.get("almacen_trabajo_en_proceso"):
        faltantes.append(_("Falta el almacén de trabajo en proceso"))
    if not _guess_finished_goods_warehouse(company):
        faltantes.append(_("Falta el almacén de producto terminado"))

    servicios_gasto = frappe.db.get_value(
        "Item Default", {"parent": "Servicios", "parenttype": "Item Group", "company": company}, "expense_account"
    )
    if not servicios_gasto:
        faltantes.append(_("El grupo 'Servicios' no tiene cuenta de gasto para esta compañía (maquila)"))

    return {"ok": not faltantes, "faltantes": faltantes}


# ─────────────────────────────────────────────────────────────────────────────
# Configuración (idempotente)
# ─────────────────────────────────────────────────────────────────────────────

def _crear_cuenta(company, account_name, parent_name, root_type, account_type=None):
    existente = _account(company, account_name)
    if existente:
        return existente
    parent = _account(company, parent_name)
    if not parent:
        frappe.throw(_("No existe la cuenta padre '{0}' en {1}").format(parent_name, company))
    acc = frappe.get_doc({
        "doctype": "Account",
        "account_name": account_name,
        "parent_account": parent,
        "company": company,
        "root_type": root_type,
        "is_group": 0,
        "account_type": account_type or "",
    })
    acc.flags.ignore_permissions = True
    acc.insert()
    return acc.name


def _set_account_type(account, account_type):
    if account and frappe.db.get_value("Account", account, "account_type") != account_type:
        frappe.db.set_value("Account", account, "account_type", account_type)


def _asegurar_almacen(company, warehouse_name):
    existente = frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": warehouse_name}, "name")
    if existente:
        if frappe.db.get_value("Warehouse", existente, "disabled"):
            frappe.db.set_value("Warehouse", existente, "disabled", 0)
        return existente
    root = frappe.db.get_value(
        "Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]}, "name"
    )
    wh = frappe.get_doc({
        "doctype": "Warehouse",
        "warehouse_name": warehouse_name,
        "company": company,
        "parent_warehouse": root,
    })
    wh.flags.ignore_permissions = True
    wh.insert()
    return wh.name


def _asegurar_categoria(nombre):
    if not frappe.db.exists("Tax Category", nombre):
        frappe.get_doc({"doctype": "Tax Category", "title": nombre}).insert(ignore_permissions=True)
    return nombre


def _asegurar_plantilla_compra(company, titulo, filas, categoria, is_default=0, disabled=0):
    abbr = frappe.get_cached_value("Company", company, "abbr")
    nombre = f"{titulo} - {abbr}"
    if frappe.db.exists("Purchase Taxes and Charges Template", nombre):
        return nombre
    doc = frappe.get_doc({
        "doctype": "Purchase Taxes and Charges Template",
        "title": titulo,
        "company": company,
        "tax_category": categoria,
        "is_default": is_default,
        "disabled": disabled,
        "taxes": filas,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _asegurar_plantilla_venta(company, titulo, filas, is_default=0):
    abbr = frappe.get_cached_value("Company", company, "abbr")
    nombre = f"{titulo} - {abbr}"
    if frappe.db.exists("Sales Taxes and Charges Template", nombre):
        return nombre
    doc = frappe.get_doc({
        "doctype": "Sales Taxes and Charges Template",
        "title": titulo,
        "company": company,
        "is_default": is_default,
        "taxes": filas,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _asegurar_tax_rule(company, categoria, plantilla):
    filtros = {"company": company, "tax_type": "Purchase", "tax_category": categoria}
    if frappe.db.exists("Tax Rule", filtros):
        return
    frappe.get_doc({
        "doctype": "Tax Rule",
        "tax_type": "Purchase",
        "company": company,
        "tax_category": categoria,
        "purchase_tax_template": plantilla,
        "priority": 1,
    }).insert(ignore_permissions=True)


def _asegurar_default_grupo(item_group, company, **campos):
    """Fila de Item Default (por compañía) dentro de un Item Group."""
    if not frappe.db.exists("Item Group", item_group):
        return
    grupo = frappe.get_doc("Item Group", item_group)
    fila = next((r for r in grupo.get("item_group_defaults") or [] if r.company == company), None)
    if not fila:
        fila = grupo.append("item_group_defaults", {"company": company})
    cambio = False
    for k, v in campos.items():
        if v and fila.get(k) != v:
            fila.set(k, v)
            cambio = True
    # Item Default trae de fábrica el almacén default de Stock Settings (de OTRA
    # compañía) y entonces el grupo no guarda -- se reemplaza por uno de esta.
    if not fila.default_warehouse or frappe.db.get_value("Warehouse", fila.default_warehouse, "company") != company:
        fila.default_warehouse = _warehouse(company, ALMACEN_MP)
        cambio = True
    if cambio or fila.is_new():
        grupo.flags.ignore_permissions = True
        grupo.save()


def configurar_compania(company: str, abbr: str = None, crear: bool = False) -> dict:
    """Deja la compañía lista para Costeo Yelke. Con ``crear=True`` la da de alta
    (catálogo "Mexico - Plan de Cuentas", MXN). Para una compañía que YA tiene
    movimientos de inventario NO prende el inventario perpetuo (lo reporta)."""
    if not frappe.db.exists("Company", company):
        if not crear:
            frappe.throw(_("La compañía {0} no existe.").format(company))
        frappe.get_doc({
            "doctype": "Company",
            "company_name": company,
            "abbr": abbr,
            "default_currency": "MXN",
            "country": "Mexico",
            "chart_of_accounts": "Mexico - Plan de Cuentas",
        }).insert(ignore_permissions=True)

    c = frappe.get_doc("Company", company)
    avisos = []

    # ── Cuentas que faltan en el catálogo ────────────────────────────────────
    proveedores = _account(company, CUENTA_PROVEEDORES) or _crear_cuenta(
        company, CUENTA_PROVEEDORES, "PROVEEDORES OCASIONALES", "Liability", "Payable")
    _set_account_type(proveedores, "Payable")
    _crear_cuenta(company, CUENTA_OVERHEAD, "COSTO", "Expense", "Expense Account")
    # OJO: en "Mexico - Plan de Cuentas" el grupo "OTROS EGRESOS 1" cuelga de Ingresos;
    # el redondeo va en un grupo de gastos.
    redondeo = _crear_cuenta(company, CUENTA_REDONDEO, "GASTOS GENERALES 1", "Expense", "Round Off")
    iva_acred = _account(company, CUENTA_IVA_ACREDITABLE)
    iva_tras = _account(company, CUENTA_IVA_TRASLADADO)
    _set_account_type(iva_acred, "Tax")
    _set_account_type(iva_tras, "Tax")
    isr_ret = _account(company, CUENTA_ISR_RETENIDO)
    iva_ret = _crear_cuenta(company, CUENTA_IVA_RETENIDO, "RETENCIONES VARIAS", "Liability", "Tax")
    _set_account_type(isr_ret, "Tax")
    _set_account_type(iva_ret, "Tax")

    # ── Defaults de la compañía ──────────────────────────────────────────────
    tiene_movimientos = frappe.db.exists("Stock Ledger Entry", {"company": company, "is_cancelled": 0})
    defaults = {
        "default_inventory_account": _account(company, "INVENTARIOS") or _account_by_type(company, "Stock"),
        "stock_received_but_not_billed": _account_by_type(company, "Stock Received But Not Billed"),
        "expenses_included_in_valuation": _account_by_type(company, "Expenses Included In Valuation"),
        "stock_adjustment_account": _account(company, "AJUSTE DE INVENTARIOS OBSOLETOS")
        or _account_by_type(company, "Stock Adjustment"),
        "default_expense_account": _account(company, "COSTO DE VENTAS"),
        "default_income_account": _account(company, "VENTAS NACIONALES"),
        "default_receivable_account": _account(company, "CUENTAS POR COBRAR CLIENTES"),
        "default_payable_account": proveedores,
        "round_off_account": redondeo,
    }
    # Al crear la compañía ERPNext ya llena clientes/proveedores/ingresos con cuentas
    # equivocadas del catálogo mexicano (OTRAS CUENTAS POR COBRAR, POLIZA DE SEGURO
    # POR PAGAR, VENTAS EXPORTACION): en una compañía SIN movimientos se sobrescriben.
    forzar = {"default_receivable_account", "default_payable_account", "default_income_account"}
    for campo, valor in defaults.items():
        if valor and campo in forzar and not tiene_movimientos and c.get(campo) != valor:
            c.set(campo, valor)
        elif valor and not c.get(campo):
            c.set(campo, valor)
        elif not valor and not c.get(campo):
            avisos.append(f"No se encontró cuenta para {campo}")
    if not c.round_off_cost_center:
        c.round_off_cost_center = c.cost_center
    if not c.enable_perpetual_inventory:
        if tiene_movimientos:
            avisos.append("La compañía ya tiene movimientos: el inventario perpetuo NO se prendió solo.")
        else:
            c.enable_perpetual_inventory = 1
    c.flags.ignore_permissions = True
    c.save()

    # ── Almacenes ─────────────────────────────────────────────────────────────
    for nombre in (ALMACEN_MP, ALMACEN_WIP, ALMACEN_PT):
        _asegurar_almacen(company, nombre)
    for nombre in ALMACENES_NATIVOS_SOBRANTES:
        wh = frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": nombre}, "name")
        if wh and not frappe.db.exists("Stock Ledger Entry", {"warehouse": wh}):
            frappe.db.set_value("Warehouse", wh, "disabled", 1)

    # ── Impuestos ─────────────────────────────────────────────────────────────
    for cat in (CATEGORIA_FORMAL, CATEGORIA_RETENCION, CATEGORIA_INFORMAL):
        _asegurar_categoria(cat)

    iva_compra = [{
        "charge_type": "On Net Total", "account_head": iva_acred, "rate": 16,
        "description": "IVA 16%", "category": "Total", "add_deduct_tax": "Add",
    }]
    p_formal = _asegurar_plantilla_compra(company, PLANTILLA_COMPRA_FORMAL, iva_compra, CATEGORIA_FORMAL, is_default=1)
    # Los porcentajes de retención los fija el contador -- se deja en 0 y DESACTIVADA
    # para que nadie la use por error antes.
    p_ret = _asegurar_plantilla_compra(company, PLANTILLA_COMPRA_RETENCION, iva_compra + [
        {"charge_type": "On Net Total", "account_head": isr_ret, "rate": 0,
         "description": "ISR retenido (definir % con el contador)", "category": "Total", "add_deduct_tax": "Deduct"},
        {"charge_type": "On Net Total", "account_head": iva_ret, "rate": 0,
         "description": "IVA retenido (definir % con el contador)", "category": "Total", "add_deduct_tax": "Deduct"},
    ], CATEGORIA_RETENCION, disabled=1)
    p_informal = _asegurar_plantilla_compra(company, PLANTILLA_COMPRA_INFORMAL, [], CATEGORIA_INFORMAL)
    _asegurar_tax_rule(company, CATEGORIA_FORMAL, p_formal)
    _asegurar_tax_rule(company, CATEGORIA_INFORMAL, p_informal)
    if not frappe.db.get_value("Purchase Taxes and Charges Template", p_ret, "disabled"):
        _asegurar_tax_rule(company, CATEGORIA_RETENCION, p_ret)

    _asegurar_plantilla_venta(company, PLANTILLA_VENTA, [{
        "charge_type": "On Net Total", "account_head": iva_tras, "rate": 16,
        "description": "IVA 16%",
    }], is_default=1)

    # ── Defaults por grupo de artículo ───────────────────────────────────────
    eiv = c.expenses_included_in_valuation
    _asegurar_default_grupo("Servicios", company, expense_account=eiv)
    _asegurar_default_grupo("Materia prima", company, default_warehouse=_warehouse(company, ALMACEN_MP))
    _asegurar_default_grupo("Sub-Ensamblajes", company, default_warehouse=_warehouse(company, ALMACEN_WIP))
    _asegurar_default_grupo(
        "Productos Terminados", company,
        default_warehouse=_warehouse(company, ALMACEN_PT), income_account=c.default_income_account,
    )

    frappe.db.commit()
    return {"company": company, "avisos": avisos, "diagnostico": diagnostico_compania(company)}
