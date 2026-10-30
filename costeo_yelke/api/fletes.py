"""Fletes pagados a un proveedor de paquetería / transporte.

Todo costo de envío con importe se le paga a un transportista y se registra con SU
factura de compra (ERPNext nativo), que se crea sola en BORRADOR al validar el
documento donde se capturó el flete. En ella se captura el folio del CFDI y se
adjuntan el XML/PDF y la carta porte; al validarla quedan:

    cargo   cuenta de gasto del flete (base, sin IVA)
    cargo   IVA 16% (misma cuenta que el resto de las compras de la compañía)
    abono   4% IVA retenido      -- solo si el proveedor "Retiene 4% IVA"
    abono   proveedor de paquetería (total a pagar)

La cuenta de gasto depende de dónde nació el flete:

- Envío de material al taller, recibo del taller y recibo de compra con paquetería
  externa: el flete se suma al costo del material (inventario) y el documento abona
  la cuenta puente "Gastos incluidos en la valoración"; la factura del flete carga
  esa MISMA cuenta, así que la puente queda en cero.
- Remisión al cliente: gasto de distribución "TRANSPORTE Y FLETES".

El importe se puede capturar con o sin IVA ("El importe incluye IVA"): lo que se
capitaliza al inventario o se carga al gasto es siempre la BASE sin IVA -- el IVA
acreditable no es costo.

Configuración (plantillas, cuenta de retención, artículo, campos): patch v0_2_56.
Reemplaza las pólizas de flete de antes (sin IVA ni retención); los documentos
viejos con póliza se respetan tal cual.
"""
import frappe
from frappe import _
from frappe.utils import flt

ITEM_FLETE = "SERVICIO DE FLETE"
TASA_IVA = 0.16


def base_sin_iva(importe, incluye_iva):
    importe = flt(importe)
    return round(importe / (1 + TASA_IVA), 2) if incluye_iva else round(importe, 2)


def plantilla_flete(company, proveedor):
    abbr = frappe.get_cached_value("Company", company, "abbr")
    retiene = proveedor and frappe.db.get_value("Supplier", proveedor, "retiene_iva_fletes")
    nombre = f"FLETE IVA 16% RET 4% - {abbr}" if retiene else f"FLETE IVA 16% - {abbr}"
    return nombre if frappe.db.exists("Purchase Taxes and Charges Template", nombre) else None


def cuenta_gasto_distribucion(company):
    for nombre in ("TRANSPORTE Y FLETES", "FLETES Y TRANSPORTES"):
        cuenta = frappe.db.get_value("Account", {"company": company, "account_name": nombre, "is_group": 0})
        if cuenta:
            return cuenta
    frappe.throw(_("No se encontró la cuenta 'TRANSPORTE Y FLETES' en {0}.").format(company))


def crear_factura_flete(company, proveedor, base, cuenta_gasto, fecha, origen_doctype, origen, descripcion="",
                        costeo=None):
    """Factura de compra del transportista, en BORRADOR, por la base sin IVA del flete.
    Regresa su nombre."""
    if flt(base) <= 0 or not proveedor:
        return None
    from erpnext.controllers.accounts_controller import get_taxes_and_charges

    cost_center = frappe.get_cached_value("Company", company, "cost_center")
    pi = frappe.new_doc("Purchase Invoice")
    pi.company = company
    pi.supplier = proveedor
    pi.posting_date = fecha
    pi.set_posting_time = 1
    pi.es_factura_flete = 1
    pi.flete_origen_doctype = origen_doctype
    pi.flete_origen = origen
    if costeo and pi.meta.get_field("flete_costeo"):
        pi.flete_costeo = costeo
    pi.remarks = _("Flete {0} — {1} {2}").format(descripcion or "", _(origen_doctype), origen).replace("  ", " ")
    pi.append("items", {
        "item_code": ITEM_FLETE,
        "item_name": ITEM_FLETE,
        "description": (descripcion or ITEM_FLETE) + f" — {_(origen_doctype)} {origen}",
        "qty": 1,
        "rate": flt(base),
        "expense_account": cuenta_gasto,
        "cost_center": cost_center,
    })
    plantilla = plantilla_flete(company, proveedor)
    if plantilla:
        pi.taxes_and_charges = plantilla
        for t in get_taxes_and_charges("Purchase Taxes and Charges Template", plantilla) or []:
            pi.append("taxes", t)
    pi.flags.ignore_permissions = True
    pi.flags.ignore_mandatory = True
    pi.insert()
    return pi.name


def soltar_factura_flete(nombre):
    """Al cancelar el documento de origen: borra la factura del flete si sigue en
    borrador. Si ya se validó (ya se registró la deuda), no se toca: se avisa para que
    se cancele a mano si de verdad no procede."""
    if not nombre or not frappe.db.exists("Purchase Invoice", nombre):
        return
    ds = frappe.db.get_value("Purchase Invoice", nombre, "docstatus")
    if ds == 0:
        frappe.delete_doc("Purchase Invoice", nombre, ignore_permissions=True, force=True)
    elif ds == 1:
        frappe.msgprint(_("La factura del flete {0} ya está validada y no se canceló sola; "
                          "cancélala a mano si ese flete ya no procede.").format(nombre), indicator="orange", alert=True)


def costeo_de(doc):
    """Costeo al que pertenece un documento (para la bandeja de Facturas)."""
    if doc.get("costeo"):
        return doc.costeo
    if doc.doctype == "Purchase Receipt":
        po = next((it.purchase_order for it in doc.items if it.get("purchase_order")), None)
        return frappe.db.get_value("Purchase Order", po, "costeo") if po else None
    sco = doc.get("subcontracting_order") or next(
        (it.get("subcontracting_order") for it in (doc.get("items") or []) if it.get("subcontracting_order")), None)
    if sco:
        po = frappe.db.get_value("Subcontracting Order", sco, "purchase_order")
        return frappe.db.get_value("Purchase Order", po, "costeo") if po else None
    return None


# ── Costos adicionales (envío al taller / recibo del taller) ─────────────────

def facturas_costos_adicionales(doc):
    """on_submit: una factura de flete por renglón de costo adicional con importe y
    proveedor (los viejos con póliza se respetan)."""
    costeo = costeo_de(doc)
    for r in doc.get("additional_costs") or []:
        monto = flt(r.get("base_amount") or r.amount)
        if monto <= 0 or not r.get("proveedor_flete") or r.get("poliza_flete") or r.get("factura_flete"):
            continue
        pi = crear_factura_flete(doc.company, r.proveedor_flete, monto, r.expense_account, doc.posting_date,
                                 doc.doctype, doc.name, r.description, costeo)
        if pi:
            frappe.db.set_value("Landed Cost Taxes and Charges", r.name, "factura_flete", pi, update_modified=False)


def soltar_facturas_costos_adicionales(doc):
    for r in doc.get("additional_costs") or []:
        soltar_factura_flete(r.get("factura_flete"))


# ── Recibo de compra con paquetería externa ─────────────────────────────────

def factura_flete_recibo(doc, method=None):
    """Purchase Receipt on_submit: si el envío lo cobró una paquetería externa, su
    factura (la fila de flete del recibo se capitalizó al inventario contra la cuenta
    puente; la factura carga esa misma cuenta)."""
    if doc.get("flete_modo") != "Paquetería externa" or not doc.get("flete_proveedor") or doc.get("factura_flete"):
        return
    from costeo_yelke.api.costeo_api import FLETE_DESCRIPTION

    fila = next((t for t in (doc.get("taxes") or []) if t.description == FLETE_DESCRIPTION), None)
    if not fila or flt(fila.base_tax_amount or fila.tax_amount) <= 0:
        return
    pi = crear_factura_flete(doc.company, doc.flete_proveedor, flt(fila.base_tax_amount or fila.tax_amount),
                             fila.account_head, doc.posting_date, doc.doctype, doc.name, _("Envío de material"),
                             costeo_de(doc))
    if pi:
        frappe.db.set_value("Purchase Receipt", doc.name, "factura_flete", pi, update_modified=False)


def soltar_factura_flete_recibo(doc, method=None):
    soltar_factura_flete(doc.get("factura_flete"))


def validar_flete_recibo(doc, method=None):
    """Purchase Receipt before_submit: con paquetería externa e importe, el proveedor
    de paquetería es obligatorio."""
    if doc.get("flete_modo") != "Paquetería externa":
        return
    from costeo_yelke.api.costeo_api import FLETE_DESCRIPTION

    fila = next((t for t in (doc.get("taxes") or []) if t.description == FLETE_DESCRIPTION), None)
    if fila and flt(fila.tax_amount) > 0 and not doc.get("flete_proveedor"):
        frappe.throw(_("Indica el proveedor de paquetería que cobró el envío."))


# ── Remisión al cliente ─────────────────────────────────────────────────────

def soltar_factura_remision(doc, method=None):
    """Delivery Note on_cancel: la factura del flete al cliente sigue al documento."""
    soltar_factura_flete(doc.get("flete_factura"))


# ── Factura del flete ───────────────────────────────────────────────────────

def validar_factura_flete(doc, method=None):
    """Purchase Invoice before_submit: una factura de FLETE se valida además con el
    folio del CFDI. El PDF lo exige contabilidad.validar_archivos_factura para TODA
    factura; la carta porte va en los adjuntos generales. Sin ese campo (sitio sin el
    patch v0_2_58) se sigue pidiendo algún adjunto, como antes."""
    if not doc.get("es_factura_flete"):
        return
    if not (doc.get("bill_no") or "").strip():
        frappe.throw(_("Captura el folio del CFDI del proveedor de paquetería antes de validar la factura del flete."))
    if not frappe.db.has_column("Purchase Invoice", "factura_pdf") and not frappe.db.exists(
            "File", {"attached_to_doctype": "Purchase Invoice", "attached_to_name": doc.name}):
        frappe.throw(_("Adjunta el CFDI (XML o PDF) y, si aplica, la carta porte antes de validar la factura del flete."))


# ── IVA del flete que cobra el mismo proveedor ──────────────────────────────

FLETE_IVA_DESCRIPTION = "IVA del flete"


def _cuenta_iva(doc):
    """La cuenta de IVA de la propia compra; si no trae, la de la plantilla de fletes."""
    for t in doc.get("taxes") or []:
        if t.charge_type == "On Net Total" and flt(t.rate) == TASA_IVA * 100 and t.add_deduct_tax != "Deduct":
            return t.account_head
    abbr = frappe.get_cached_value("Company", doc.company, "abbr")
    return frappe.db.get_value("Purchase Taxes and Charges",
                               {"parent": f"FLETE IVA 16% - {abbr}", "parenttype": "Purchase Taxes and Charges Template"},
                               "account_head")


def _recalcular(doc):
    doc.calculate_taxes_and_totals()
    # El reparto del flete al costo de cada renglón (item_tax_amount) se calcula sobre
    # los impuestos de antes; se rehace para que el recibo capitalice solo el flete.
    if doc.doctype in ("Purchase Receipt", "Purchase Invoice") and hasattr(doc, "update_valuation_rate"):
        doc.update_valuation_rate()


def ajustar_iva_flete(doc, method=None):
    """validate de Orden de compra, Recibo y Factura de compra (después de
    quitar_iva_sin_alta_sat): con el flete cobrado por el MISMO proveedor y la casilla
    "cobra IVA" marcada, pone justo debajo del flete el renglón "IVA del flete" (16%
    sobre el renglón anterior, categoría Total: el IVA es acreditable, no costo del
    inventario). Si no aplica, lo quita. Se rehace en cada guardado para que el
    renglón de referencia (row_id) nunca quede apuntando a otro."""
    if not doc.meta.has_field("flete_cobra_iva") or doc.get("es_factura_flete"):
        return
    from costeo_yelke.api.costeo_api import FLETE_DESCRIPTION

    taxes = [t for t in (doc.get("taxes") or []) if t.description != FLETE_IVA_DESCRIPTION]
    había = len(taxes) != len(doc.get("taxes") or [])
    flete = next((t for t in taxes if t.description == FLETE_DESCRIPTION), None)
    sin_sat = frappe.db.has_column("Supplier", "sin_alta_sat") and doc.get("supplier") \
        and frappe.db.get_value("Supplier", doc.supplier, "sin_alta_sat")
    aplica = (flete and flt(flete.tax_amount) > 0 and frappe.utils.cint(doc.get("flete_cobra_iva"))
              and doc.get("flete_modo") != "Paquetería externa" and not sin_sat
              and flete.category != "Valuation")
    cuenta = _cuenta_iva(doc) if aplica else None
    if not (aplica and cuenta):
        if había:
            doc.set("taxes", taxes)
            for i, t in enumerate(doc.taxes, 1):
                t.idx = i
            _recalcular(doc)
        return
    pos = taxes.index(flete)
    actuales = list(doc.get("taxes") or [])
    ya = actuales[pos + 1] if len(actuales) > pos + 1 else None
    if ya is not None and ya.description == FLETE_IVA_DESCRIPTION and ya.account_head == cuenta \
            and str(ya.row_id) == str(pos + 1) and len(actuales) == len(taxes) + 1:
        # Ya está bien puesto: rehacerlo en cada guardado cambiaba el renglón aunque
        # nada cambiara, y la factura salía como "cambió después de enviarse".
        return
    doc.set("taxes", taxes[:pos + 1])
    doc.append("taxes", {
        "charge_type": "On Previous Row Amount", "row_id": str(pos + 1), "rate": TASA_IVA * 100,
        "account_head": cuenta, "description": FLETE_IVA_DESCRIPTION, "category": "Total",
        "add_deduct_tax": "Add",
    })
    for t in taxes[pos + 1:]:
        doc.append("taxes", t)
    for i, t in enumerate(doc.taxes, 1):
        t.idx = i
    _recalcular(doc)
