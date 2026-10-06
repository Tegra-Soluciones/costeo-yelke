import frappe


def execute():
    """El campo `conversion_factor` (UOM Conversion Detail, y todas las líneas de
    documento que lo usan -- Purchase/Sales Order Item, Material Request Item,
    Stock Entry Detail, etc.) no trae una precisión propia definida, así que
    ERPNext lo redondea a la precisión GLOBAL del sitio (System Settings ->
    Precisión decimal, 3 en este sitio) cada vez que se guarda un documento
    (ver erpnext/controllers/taxes_and_totals.py, calculate_item_values ->
    round_floats_in). Con una UDM cuyo factor real es una fracción chica --
    como "H87 - Pieza" para los botones (1/1728 = 0.000578704, ver
    costeo_yelke/api/item_api.py y la sesión donde se dieron de alta) -- ese
    redondeo lo trunca a 0.001, un error de ~73% en la cantidad real de
    material que se guarda en cualquier transacción que use esa UDM.

    Corrección acotada: darle a `conversion_factor` su PROPIA precisión (9
    decimales) en cualquier doctype donde exista, sin tocar la precisión
    global del sitio (que afectaría a todos los demás números del sistema).
    frappe.make_property_setter sin `doctype` aplica el Property Setter a
    TODOS los doctypes que declaren ese fieldname -- es idempotente (borra
    cualquier Property Setter previo con la misma llave antes de crear el
    nuevo, ver PropertySetter.validate)."""
    frappe.make_property_setter(
        {
            "fieldname": "conversion_factor",
            "property": "precision",
            "value": "9",
            "property_type": "Int",
        },
        validate_fields_for_doctype=False,
    )
