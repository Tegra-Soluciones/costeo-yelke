# Costeo - Arquitectura Frontend

Este doctype concentra la mayor parte de su logica de UI en JavaScript del lado cliente.
Para mejorar mantenibilidad, `costeo.js` ahora se arma desde modulos en `modules/`.

## Estructura de archivos

- `costeo.js`: archivo cargado por Frappe para el doctype (artefacto ensamblado).
- `build_costeo_js.sh`: script de ensamblado del archivo final.
- `modules/00_constants.js`: constantes de campos, doctypes e item groups.
- `modules/10_main_form_events.js`: eventos del formulario principal de `Costeo`.
- `modules/20_filters_and_cleanup.js`: filtros dinamicos y limpieza de filas huerfanas.
- `modules/30_automation_documents.js`: automatizacion de Quotation, Sales Order y Production Plan.
- `modules/35_validations.js`: validaciones de negocio del formulario.
- `modules/37_production_plan_tab.js`: replica funcional del flujo de Plan de Produccion dentro de Costeo.
- `modules/38_production_plan_child_events.js`: eventos de tablas hijas usadas por el tab de Plan de Produccion.
- `modules/40_bom_creation.js`: logica de creacion secuencial de BOMs.
- `modules/50_subcontracting_bom_creation.js`: logica de Subcontracting BOMs.
- `modules/60_child_table_events.js`: eventos de child tables `Costeo Producto`, `Detalle` y `Etapas`.
- `modules/70_tree_view.js`: render HTML del arbol de costos y binding de eventos.
- `modules/80_detail_editor_modal.js`: modal de edicion de desglose (etapas/materiales/envio).
- `modules/90_calculations.js`: conversiones, agregados y recalculos de costos/margenes.
- `modules/99_utils_and_styles.js`: utilidades de mensajes/formato e inyeccion de CSS.

## Flujo funcional

1. `refresh` configura filtros, botones, opciones y render del arbol.
2. El modal "Editar Desglose" escribe en tablas tecnicas (`costeo_producto_detalle`, `tabla_etapas_costeo`) y costo de envio en `costeo_producto`.
3. `calculate_aggregates` recalcula por producto:
   - materiales desde detalle
   - servicios desde etapas (precio por etapa)
   - envio desde el campo en `Costeo Producto`
4. Se actualizan overhead, costo total, precio de venta, margen y totales.
5. Las automatizaciones generan documentos ERPNext sin cambiar datos base del costeo.
6. El tab de Plan de Produccion permanece bloqueado hasta ejecutar el boton:
   `Desbloquear y Prellenar Plan de Producción` (en el grupo de automatizacion de la primera pestaña).

## Reglas de mantenimiento

- Editar siempre en `modules/`.
- Regenerar `costeo.js` despues de cualquier cambio:

```bash
./costeo_yelke/costeo_yelke/doctype/costeo/build_costeo_js.sh
```

- Evitar logica duplicada entre modal/arbol/child tables.
- No cambiar nombres de campos definidos en `DB` sin migracion de doctype.
