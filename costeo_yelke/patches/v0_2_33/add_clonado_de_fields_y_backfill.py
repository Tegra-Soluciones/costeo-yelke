import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Una variante de talla (Costeo Producto.variante_talla_de) nace como un
    CLON de las etapas/materiales de su producto base -- mismos proveedores,
    mismos servicios, mismo grafo, solo con stage_id/material_id nuevos (ver
    crear_variante_talla, costeo_api.py) para no compartirlos con la base. La
    correspondencia base->variante existía solo como variable local dentro de
    esa función y nunca se guardaba -- sin ella, "Flujo de Producción" no
    tenía forma de saber que dos filas (una de la base, otra de la variante)
    son la MISMA operación en dos productos distintos, y no podía propagar un
    cambio de una a la otra.

    Este patch:
    1. Agrega los dos campos donde esa correspondencia se guarda desde ahora
       (`clonado_de_stage_id` en Etapas Costeo, `clonado_de_material_id` en
       Costeo Producto Detalle) -- crear_variante_talla ya se actualizó para
       llenarlos en cualquier variante NUEVA.
    2. Rellena esos campos para las variantes que YA EXISTEN (creadas antes
       de este cambio, sin la correspondencia guardada) -- empareja las
       etapas/materiales de cada variante con los de su base por POSICIÓN
       relativa (mismo orden en que crear_variante_talla las clonó: recorre
       la lista de la base en orden y agrega en ese mismo orden, así que la
       fila N de la variante siempre corresponde a la fila N de la base)."""
    create_custom_fields(
        {
            "Etapas Costeo": [
                {
                    "fieldname": "clonado_de_stage_id",
                    "label": "Clonado de (stage_id de la base)",
                    "fieldtype": "Data",
                    "insert_after": "stage_id",
                    "hidden": 1,
                    "description": "Si esta etapa se clonó de un producto base al crear una variante de talla, aquí queda el stage_id ORIGINAL (de la base) -- para que Flujo de Producción pueda propagar cambios de la base a la variante.",
                },
            ],
            "Costeo Producto Detalle": [
                {
                    "fieldname": "clonado_de_material_id",
                    "label": "Clonado de (material_id de la base)",
                    "fieldtype": "Data",
                    "insert_after": "material_id",
                    "hidden": 1,
                    "description": "Igual que Etapas Costeo.clonado_de_stage_id, pero para la asignación de materia prima a una operación (tabla_materiales_etapa).",
                },
            ],
        },
        ignore_validate=True,
        update=True,
    )
    frappe.clear_cache(doctype="Etapas Costeo")
    frappe.clear_cache(doctype="Costeo Producto Detalle")

    _backfill_variantes_existentes()


def _backfill_variantes_existentes():
    variantes = frappe.get_all(
        "Costeo Producto",
        filters={"variante_talla_de": ["is", "set"]},
        fields=["name", "parent", "finished_item", "variante_talla_de"],
    )
    if not variantes:
        return

    por_costeo = {}
    for v in variantes:
        por_costeo.setdefault(v.parent, []).append(v)

    for costeo_name, filas in por_costeo.items():
        doc = frappe.get_doc("Costeo", costeo_name)
        tocado = False
        for v in filas:
            etapas_base = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == v.variante_talla_de]
            etapas_var = [e for e in doc.tabla_etapas_costeo if e.producto_terminado == v.finished_item]
            for e_base, e_var in zip(etapas_base, etapas_var):
                if e_var.get("clonado_de_stage_id") != e_base.stage_id:
                    e_var.clonado_de_stage_id = e_base.stage_id
                    tocado = True

            mats_base = [d for d in doc.costeo_producto_detalle if d.finished_item == v.variante_talla_de]
            mats_var = [d for d in doc.costeo_producto_detalle if d.finished_item == v.finished_item]
            for d_base, d_var in zip(mats_base, mats_var):
                if d_var.get("clonado_de_material_id") != d_base.material_id:
                    d_var.clonado_de_material_id = d_base.material_id
                    tocado = True

        if tocado:
            doc.flags.ignore_permissions = True
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_validate_update_after_submit = True
            doc.save()

    frappe.db.commit()
