import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """'qty_original'/'planned_qty_original' -- la cantidad EXACTA que de verdad se
    necesitaba (materia prima calculada por BOM / prendas del plan de producción),
    capturada como referencia al momento de crear la Solicitud de Material / el Plan.
    Sirve de base para la nueva regla de "comprar/producir hasta 5% de más" -- sin
    guardar el original, no habría contra qué comparar el límite una vez que el
    usuario ya editó la cantidad."""
    create_custom_fields(
        {
            "Material Request Item": [{
                "fieldname": "qty_original",
                "label": "Cantidad requerida (original)",
                "fieldtype": "Float",
                "insert_after": "qty",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
                "hidden": 1,
            }],
            "Production Plan Item": [{
                "fieldname": "planned_qty_original",
                "label": "Cantidad requerida (original)",
                "fieldtype": "Float",
                "insert_after": "planned_qty",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
                "hidden": 1,
            }],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Material Request Item")
    frappe.clear_cache(doctype="Production Plan Item")
