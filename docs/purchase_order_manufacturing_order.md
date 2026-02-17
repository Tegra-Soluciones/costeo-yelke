# Orden de Manufactura en Purchase Order subcontratada

## Objetivo
Agregar una pestaña adicional en `Purchase Order` cuando `is_subcontracted = 1` para capturar
especificaciones de manufactura (cortes, tallas, procesos, observaciones, medidas y archivos).

## Estructura
- Tab: `Orden de Manufactura`
- Bloques:
  - `Info General`
  - `Informacion mas detallada`
  - `Tallas Caballero`
  - `Tallas Dama`
  - `Tabla de procesos`
  - `Observaciones`
  - `Tablas de medidas y equivalencias` (flexible)
  - `Diagramas y archivos`

## Comportamiento automatico
- `om_fecha_requerida` se sincroniza con `schedule_date` o `transaction_date`.
- En tablas de tallas:
  - se fuerza 1 sola fila fija con `linea = Cantidad`
  - no se pueden agregar/eliminar filas
  - se calcula `total` por fila
  - se actualiza total general de prendas en caballero/dama (debajo de cada tabla)
  - Tallas caballero: `28, 30, 32, 34, 36, 40, 42, 44`
  - Tallas dama: `5, 7, 9, 11, 13, 15, 17`
- En tabla de procesos:
  - `proceso` se numera automaticamente como `Proceso 1`, `Proceso 2`, etc.
- En tablas flexibles:
  - la UI es un `HTML builder` con botones `+ Tabla`, `+ Columna`, `+ Fila`
  - no se muestran nombres de fila/columna en la interfaz (tipo hoja en blanco)
  - la persistencia se guarda en `om_tablas_flexibles` (tabla backend)

## Archivos y puntos de extension
- JS de comportamiento:
  - `costeo_yelke/public/js/purchase_order_manufacturing_order.js`
- Patch de custom fields:
  - `costeo_yelke/patches/v0_0_4/add_purchase_order_manufacturing_order_fields.py`
  - `costeo_yelke/patches/v0_0_5/add_purchase_order_flexible_tables_html_builder.py`
  - `costeo_yelke/patches/v0_0_6/update_purchase_order_manufacturing_order_layout.py`
- Hook de carga JS:
  - `costeo_yelke/hooks.py` (`doctype_js["Purchase Order"]`)
- Doctypes child table:
  - `Orden Manufactura Talla Caballero`
  - `Orden Manufactura Talla Dama`
  - `Orden Manufactura Proceso`
  - `Orden Manufactura Tabla Flexible`
  - `Orden Manufactura Archivo`

## Despliegue
1. `bench --site <sitio> migrate`
2. `bench --site <sitio> clear-cache`
3. recarga fuerte del navegador (Ctrl/Cmd + Shift + R)
