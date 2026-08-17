import frappe
from frappe.utils import random_string


def execute():
    """Genera stage_id para las filas de Etapas Costeo creadas antes de que este
    campo existiera -- sin esto, las etapas viejas no se podrían referenciar desde
    'recibe_de' (procesos en paralelo, ver _resolve_stage_graph) aunque el costeo
    siga funcionando en modo lineal (fallback) mientras nadie las use."""
    rows = frappe.get_all("Etapas Costeo", filters={"stage_id": ["in", ["", None]]}, pluck="name")
    for name in rows:
        frappe.db.set_value("Etapas Costeo", name, "stage_id", random_string(10), update_modified=False)
    frappe.db.commit()
