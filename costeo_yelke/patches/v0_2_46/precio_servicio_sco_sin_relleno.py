import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
    """El precio de cada servicio del encargo (Subcontracting Order Service Item.rate)
    trae de fábrica `fetch_from: item_code.standard_rate` con `fetch_if_empty`: un
    renglón en $0 se rellena con el precio estándar del servicio. El modelo por pieza
    deja en $0 A PROPÓSITO las piezas que no cargan el precio (el servicio se cobra
    completo en la pieza portadora, ver precio-pieza-portadora), así que el relleno
    duplicaba la maquila en la valuación (fusionado de los puños a $3 en la chamarra:
    $9,162 de más). Los encargos siempre nacen de la OC, que ya trae su precio."""
    make_property_setter("Subcontracting Order Service Item", "rate", "fetch_from", "", "Small Text",
                         validate_fields_for_doctype=False)
    make_property_setter("Subcontracting Order Service Item", "rate", "fetch_if_empty", "0", "Check",
                         validate_fields_for_doctype=False)
    frappe.clear_cache(doctype="Subcontracting Order Service Item")
    frappe.clear_cache(doctype="Subcontracting Order")
