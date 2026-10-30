"""Apaga los flujos de aprobación nativos de ERPNext (Workflow) de Orden de compra y
Cotización y la notificación que colgaba de ellos.

La aprobación de la app es otra (api/aprobaciones.py, estado_aprobacion_yelke) y no
usa el Workflow. Los dos convivían: cada orden de compra mandaba ~10 correos genéricos
"Workflow Action on Purchase Order" a todos los usuarios con el rol, y el 8-oct
agotaron el límite de 50 correos por hora de la cuenta de envío. Solo se desactivan
(is_active / enabled = 0); se pueden volver a prender desde el escritorio.
"""
import frappe


def execute():
    for wf in frappe.get_all("Workflow", filters={"is_active": 1,
                                                  "document_type": ["in", ["Purchase Order", "Quotation"]]},
                             pluck="name"):
        frappe.db.set_value("Workflow", wf, "is_active", 0)
    if frappe.db.exists("Notification", "Aprobación de Documentos"):
        frappe.db.set_value("Notification", "Aprobación de Documentos", "enabled", 0)
    # Las acciones pendientes del flujo apagado ya no llevan a nada.
    frappe.db.delete("Workflow Action", {"status": "Open",
                                         "reference_doctype": ["in", ["Purchase Order", "Quotation"]]})
    frappe.clear_cache()
