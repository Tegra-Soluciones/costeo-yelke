import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Reemplaza 'Familia de prenda' (nunca quedó claro para qué servía en la
    práctica) por una casilla que controla si, al guardar el Costeo, cada uno de
    sus productos se guarda/actualiza automáticamente como su propia plantilla (ver
    Costeo.on_update y costeo_template_api._sync_templates_from_costeo). Marcada por
    default -- si se desmarca, ese Costeo no toca sus plantillas al guardarse (el
    botón manual 'Guardar como Plantilla' sigue funcionando siempre, sin importar
    esta casilla)."""
    create_custom_fields(
        {
            "Costeo": [{
                "fieldname": "guardar_como_plantilla",
                "label": "Guardar productos como plantilla al guardar",
                "fieldtype": "Check",
                "default": "1",
                "insert_after": "familia_prenda",
                "depends_on": "eval:!doc.es_plantilla",
                # Un Costeo ya enviado (docstatus 1) solo puede seguir alimentando
                # Plantillas si esta casilla es editable ahí -- sin esto, Frappe
                # bloquea el cambio con UpdateAfterSubmitError y la casilla queda
                # congelada en lo que tenía al momento de enviarse.
                "allow_on_submit": 1,
                "description": "Cada producto de este Costeo se guarda (o actualiza) como su propia plantilla reutilizable cada vez que se guarda. Desmárcala si no quieres que este Costeo alimente Plantillas.",
            }]
        },
        ignore_validate=True,
        update=True,
    )

    # 'Por defecto' también para lo que ya existe: los Costeos reales (no
    # plantillas) creados antes de este campo no tienen valor -- se dejan
    # encendidos para que, la próxima vez que se guarden, empiecen a alimentar
    # Plantillas igual que uno nuevo. No dispara nada por sí solo (solo corre al
    # guardar, ver Costeo.on_update); esto únicamente fija el valor de la casilla.
    frappe.db.sql(
        "UPDATE `tabCosteo` SET guardar_como_plantilla = 1 "
        "WHERE (es_plantilla IS NULL OR es_plantilla = 0) "
        "AND (guardar_como_plantilla IS NULL OR guardar_como_plantilla = 0)"
    )
    frappe.clear_cache(doctype="Costeo")
