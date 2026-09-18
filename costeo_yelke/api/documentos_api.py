import frappe

from costeo_yelke.utils import nombres_comerciales

# Listas para las páginas /solicitudes-material, /recibos-compra, /remisiones y
# /facturas-compra del sidebar "Documentos" -- doctypes que, a diferencia de Cotización/
# Orden de Venta/Orden de Compra/Factura de venta, no tenían su propia página ni ruta en
# el SPA todavía. Cada una resuelve 'costeo' (directo si el doctype ya tiene la columna,
# o vía el documento padre si no) para que la lista pueda redirigir al detalle del Costeo.


@frappe.whitelist()
def get_material_requests(status=None, company=None, limit=100):
    if not frappe.db.has_column("Material Request", "costeo"):
        return []
    filters = {}
    if status:
        filters["status"] = status
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Material Request",
        fields=[
            "name", "status", "material_request_type", "transaction_date",
            "schedule_date", "docstatus", "company", "costeo",
        ],
        filters=filters,
        order_by="transaction_date desc, creation desc",
        limit=int(limit),
    )


@frappe.whitelist()
def get_purchase_receipts(status=None, company=None, limit=100):
    filters = {}
    if status:
        filters["status"] = status
    if company:
        filters["company"] = company

    rows = frappe.get_all(
        "Purchase Receipt",
        fields=[
            "name", "status", "supplier", "supplier_name",
            "posting_date", "grand_total", "currency", "company", "docstatus",
        ],
        filters=filters,
        order_by="posting_date desc, creation desc",
        limit=int(limit),
    )
    # Sin columna propia -- vía Purchase Receipt Item.purchase_order -> Purchase Order.costeo.
    if rows and frappe.db.has_column("Purchase Order", "costeo"):
        names = [r["name"] for r in rows]
        po_by_pr = {
            i.parent: i.purchase_order
            for i in frappe.get_all(
                "Purchase Receipt Item", filters={"parent": ["in", names], "purchase_order": ["is", "set"]},
                fields=["parent", "purchase_order"],
            )
        }
        po_names = list(set(po_by_pr.values()))
        costeo_by_po = {
            p.name: p.costeo
            for p in frappe.get_all("Purchase Order", filters={"name": ["in", po_names]}, fields=["name", "costeo"])
        } if po_names else {}
        for r in rows:
            po = po_by_pr.get(r["name"])
            r["costeo"] = costeo_by_po.get(po) if po else None
    nombres = nombres_comerciales("Supplier", [r["supplier"] for r in rows], "supplier_name")
    for r in rows:
        r["supplier_name"] = nombres.get(r["supplier"], r["supplier_name"])
    return rows


@frappe.whitelist()
def get_delivery_notes(status=None, company=None, limit=100):
    if not frappe.db.has_column("Delivery Note", "costeo"):
        return []
    filters = {}
    if status:
        filters["status"] = status
    if company:
        filters["company"] = company
    rows = frappe.get_all(
        "Delivery Note",
        fields=[
            "name", "status", "customer", "customer_name",
            "posting_date", "grand_total", "currency", "company", "docstatus", "costeo",
        ],
        filters=filters,
        order_by="posting_date desc, creation desc",
        limit=int(limit),
    )
    nombres = nombres_comerciales("Customer", [r["customer"] for r in rows], "customer_name")
    for r in rows:
        r["customer_name"] = nombres.get(r["customer"], r["customer_name"])
    return rows


@frappe.whitelist()
def get_purchase_invoices(status=None, company=None, limit=100):
    filters = {}
    if status:
        filters["status"] = status
    if company:
        filters["company"] = company

    rows = frappe.get_all(
        "Purchase Invoice",
        fields=[
            "name", "status", "supplier", "supplier_name",
            "posting_date", "due_date", "grand_total", "outstanding_amount",
            "currency", "company", "docstatus",
        ],
        filters=filters,
        order_by="posting_date desc, creation desc",
        limit=int(limit),
    )
    # Sin columna propia -- vía Purchase Invoice Item.purchase_order/purchase_receipt.
    if rows and frappe.db.has_column("Purchase Order", "costeo"):
        names = [r["name"] for r in rows]
        items = frappe.get_all(
            "Purchase Invoice Item", filters={"parent": ["in", names]},
            fields=["parent", "purchase_order", "purchase_receipt"],
        )
        po_by_pi, pr_by_pi = {}, {}
        for i in items:
            if i.purchase_order and i.parent not in po_by_pi:
                po_by_pi[i.parent] = i.purchase_order
            if i.purchase_receipt and i.parent not in pr_by_pi:
                pr_by_pi[i.parent] = i.purchase_receipt

        po_names = list(set(po_by_pi.values()))
        costeo_by_po = {
            p.name: p.costeo
            for p in frappe.get_all("Purchase Order", filters={"name": ["in", po_names]}, fields=["name", "costeo"])
        } if po_names else {}

        pr_names = list(set(pr_by_pi.values()))
        po_by_pr = {
            i.parent: i.purchase_order
            for i in frappe.get_all(
                "Purchase Receipt Item", filters={"parent": ["in", pr_names], "purchase_order": ["is", "set"]},
                fields=["parent", "purchase_order"],
            )
        } if pr_names else {}

        for r in rows:
            po = po_by_pi.get(r["name"])
            if not po:
                pr = pr_by_pi.get(r["name"])
                po = po_by_pr.get(pr) if pr else None
            r["costeo"] = costeo_by_po.get(po) if po else None
    nombres = nombres_comerciales("Supplier", [r["supplier"] for r in rows], "supplier_name")
    for r in rows:
        r["supplier_name"] = nombres.get(r["supplier"], r["supplier_name"])
    return rows
