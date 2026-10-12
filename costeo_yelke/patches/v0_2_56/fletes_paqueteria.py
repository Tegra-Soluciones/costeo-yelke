"""Fletes con proveedor de paquetería, IVA acreditable y retención de 4%.

Todo costo de envío con importe se le paga a un proveedor de paquetería/transporte
y se registra con SU factura (borrador automático, ver api/fletes.py): IVA 16%
acreditable y, si el proveedor es de autotransporte de carga, retención de 4% de
IVA (art. 1-A LIVA). Aquí se deja la configuración, idempotente:

- Proveedor: casillas "Proveedor de paquetería / transporte" y "Retiene 4% IVA".
- Grupo de proveedores "Transporte y paquetería".
- Artículo de servicio "SERVICIO DE FLETE" (no inventariable) para esas facturas.
- Campos de captura en cada lugar donde hay costo de envío (costos adicionales de
  envío/recibo de taller, orden y recibo de compra, remisión) y en la factura de
  compra (de qué documento salió el flete).
- Por compañía: cuenta "4% IVA RETENIDO FLETES" (si no existe) y dos plantillas de
  impuestos de compra para fletes, con la MISMA cuenta de IVA que el resto de las
  compras de la compañía (decisión de Yelke, 2026-10-12).
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

ITEM_FLETE = "SERVICIO DE FLETE"
GRUPO = "Transporte y paquetería"


def execute():
    _campos()
    _grupo_y_articulo()
    for c in frappe.get_all("Company", fields=["name", "abbr"]):
        try:
            _compania(c.name, c.abbr)
        except Exception:
            frappe.log_error(title=f"v0_2_56 fletes: {c.name}")


def _campos():
    flete_link = {"fieldtype": "Link", "options": "Purchase Invoice", "read_only": 1, "no_copy": 1}
    create_custom_fields({
        "Supplier": [
            {"fieldname": "es_paqueteria", "label": "Proveedor de paquetería / transporte", "fieldtype": "Check",
             "insert_after": "supplier_group"},
            {"fieldname": "retiene_iva_fletes", "label": "Retiene 4% IVA (autotransporte de carga)", "fieldtype": "Check",
             "insert_after": "es_paqueteria", "depends_on": "es_paqueteria",
             "description": "Servicio de autotransporte terrestre de bienes: su factura de flete lleva retención de 4% de IVA. "
                            "En paquetería y mensajería normalmente no aplica."},
        ],
        "Landed Cost Taxes and Charges": [
            {"fieldname": "flete_incluye_iva", "label": "El importe incluye IVA", "fieldtype": "Check",
             "insert_after": "poliza_flete"},
            {"fieldname": "flete_importe_capturado", "label": "Importe capturado", "fieldtype": "Currency",
             "insert_after": "flete_incluye_iva", "read_only": 1},
            dict(flete_link, fieldname="factura_flete", label="Factura del flete", insert_after="flete_importe_capturado"),
        ],
        "Purchase Order": [
            {"fieldname": "flete_modo", "label": "Costo de envío", "fieldtype": "Select",
             "options": "\nLo cobra el proveedor\nPaquetería externa", "insert_after": "taxes_and_charges"},
            {"fieldname": "flete_proveedor", "label": "Proveedor de paquetería", "fieldtype": "Link", "options": "Supplier",
             "insert_after": "flete_modo", "depends_on": "eval:doc.flete_modo=='Paquetería externa'"},
            {"fieldname": "flete_incluye_iva", "label": "El costo de envío incluye IVA", "fieldtype": "Check",
             "insert_after": "flete_proveedor"},
            {"fieldname": "flete_importe_capturado", "label": "Costo de envío capturado", "fieldtype": "Currency",
             "insert_after": "flete_incluye_iva", "read_only": 1},
        ],
        "Purchase Receipt": [
            {"fieldname": "flete_modo", "label": "Costo de envío", "fieldtype": "Select",
             "options": "\nLo cobra el proveedor\nPaquetería externa", "insert_after": "taxes_and_charges"},
            {"fieldname": "flete_proveedor", "label": "Proveedor de paquetería", "fieldtype": "Link", "options": "Supplier",
             "insert_after": "flete_modo", "depends_on": "eval:doc.flete_modo=='Paquetería externa'"},
            {"fieldname": "flete_incluye_iva", "label": "El costo de envío incluye IVA", "fieldtype": "Check",
             "insert_after": "flete_proveedor"},
            {"fieldname": "flete_importe_capturado", "label": "Costo de envío capturado", "fieldtype": "Currency",
             "insert_after": "flete_incluye_iva", "read_only": 1},
            dict(flete_link, fieldname="factura_flete", label="Factura del flete", insert_after="flete_importe_capturado"),
        ],
        "Delivery Note": [
            {"fieldname": "flete_incluye_iva", "label": "El costo de envío incluye IVA", "fieldtype": "Check",
             "insert_after": "flete_costo"},
            {"fieldname": "flete_importe_capturado", "label": "Costo de envío capturado", "fieldtype": "Currency",
             "insert_after": "flete_incluye_iva", "read_only": 1},
            dict(flete_link, fieldname="flete_factura", label="Factura del flete", insert_after="flete_importe_capturado"),
        ],
        "Purchase Invoice": [
            {"fieldname": "es_factura_flete", "label": "Factura de flete", "fieldtype": "Check", "read_only": 1,
             "insert_after": "bill_date", "no_copy": 1},
            {"fieldname": "flete_origen_doctype", "label": "Flete de (tipo)", "fieldtype": "Link", "options": "DocType",
             "read_only": 1, "insert_after": "es_factura_flete", "no_copy": 1, "depends_on": "es_factura_flete"},
            {"fieldname": "flete_origen", "label": "Flete de", "fieldtype": "Dynamic Link", "options": "flete_origen_doctype",
             "read_only": 1, "insert_after": "flete_origen_doctype", "no_copy": 1, "depends_on": "es_factura_flete"},
            {"fieldname": "flete_costeo", "label": "Costeo del flete", "fieldtype": "Link", "options": "Costeo",
             "read_only": 1, "insert_after": "flete_origen", "no_copy": 1, "depends_on": "es_factura_flete"},
        ],
    }, update=True)


def _grupo_y_articulo():
    if not frappe.db.exists("Supplier Group", GRUPO):
        padre = frappe.db.get_value("Supplier Group", {"is_group": 1}, "name", order_by="lft asc")
        frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": GRUPO, "parent_supplier_group": padre}).insert(
            ignore_permissions=True)
    if not frappe.db.exists("Item", ITEM_FLETE):
        uom = next((u for u in ("E48 - Unidad de servicio", "H87 - Pieza", "Nos", "Unit") if frappe.db.exists("UOM", u)), None)
        grupo = "Servicios" if frappe.db.exists("Item Group", "Servicios") else \
            frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        frappe.get_doc({"doctype": "Item", "item_code": ITEM_FLETE, "item_name": ITEM_FLETE, "item_group": grupo,
                        "stock_uom": uom, "is_stock_item": 0, "is_purchase_item": 1, "is_sales_item": 0,
                        "include_item_in_manufacturing": 0,
                        "description": "Costo de envío / flete pagado a un proveedor de paquetería o transporte."}).insert(
            ignore_permissions=True, ignore_mandatory=True)  # campos fiscales de otras apps (p. ej. product_key)


def _cuenta_iva_compras(company):
    """La cuenta de IVA (16%, se suma) de la plantilla de compras que usa la app para
    la compañía -- la misma que el resto de las compras."""
    from costeo_yelke.costeo_yelke.doctype.costeo.costeo import _get_purchase_tax_template

    plantilla = _get_purchase_tax_template(company)
    filas = frappe.get_all("Purchase Taxes and Charges", filters={"parent": plantilla, "parenttype":
                           "Purchase Taxes and Charges Template", "add_deduct_tax": "Add"},
                           fields=["account_head", "rate"], order_by="idx asc") if plantilla else []
    fila = next((f for f in filas if abs((f.rate or 0) - 16) < 0.01), None) or (filas[0] if filas else None)
    return fila.account_head if fila else None


def _compania(company, abbr):
    iva = _cuenta_iva_compras(company)
    if not iva:
        return
    ret = frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_name": ["like", "%RETENIDO FLETE%"]})
    if not ret:
        padre = frappe.db.get_value("Account", iva, "parent_account")
        acc = frappe.get_doc({"doctype": "Account", "account_name": "4% IVA RETENIDO FLETES", "company": company,
                              "parent_account": padre, "is_group": 0, "account_type": "Tax", "root_type": "Liability"})
        acc.insert(ignore_permissions=True)
        ret = acc.name
    for titulo, con_ret in (("FLETE IVA 16%", False), ("FLETE IVA 16% RET 4%", True)):
        nombre = f"{titulo} - {abbr}"
        if frappe.db.exists("Purchase Taxes and Charges Template", nombre):
            continue
        filas = [{"charge_type": "On Net Total", "account_head": iva, "rate": 16, "description": "IVA 16%",
                  "category": "Total", "add_deduct_tax": "Add"}]
        if con_ret:
            filas.append({"charge_type": "On Net Total", "account_head": ret, "rate": 4,
                          "description": "Retención 4% IVA (autotransporte)", "category": "Total", "add_deduct_tax": "Deduct"})
        frappe.get_doc({"doctype": "Purchase Taxes and Charges Template", "title": titulo, "company": company,
                        "taxes": filas}).insert(ignore_permissions=True)
