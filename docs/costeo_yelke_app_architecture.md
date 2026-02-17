# Costeo Yelke - Analisis de App y Doctypes

## Alcance revisado

Se reviso todo el contenido de la app en:

- `costeo_yelke/hooks.py`
- `costeo_yelke/modules.txt`
- `costeo_yelke/patches.txt`
- `costeo_yelke/costeo_yelke/doctype/**`
- `costeo_yelke/costeo_yelke/doctype/costeo/**`
- `costeo_yelke/templates/**`
- inicializadores `__init__.py`

## Mapa funcional de la app

- App pequena con un modulo principal: `Costeo Yelke`.
- Doctypes:
  - `Costeo` (documento principal).
  - `Costeo Producto` (child table de productos terminados).
  - `Costeo Producto Detalle` (child table tecnica de materiales/consumos/proveedor/precios).
  - `Etapas Costeo` (child table tecnica de etapas/servicios/subensambles).

## Backend

- `costeo_yelke/costeo_yelke/doctype/costeo/costeo.py`
  - Limpia filas huerfanas en validate (`cleanup_orphan_children`).
  - Mantiene consistencia entre `costeo_producto` y tablas tecnicas.

- `costeo_yelke/costeo_yelke/doctype/costeo/calculations.py`
  - Calcula agregados del lado servidor sin sobrescribir envio ingresado por usuario.
  - Calcula overhead, costo total, precio venta y total venta.

## Frontend (Costeo)

- `costeo_yelke/costeo_yelke/doctype/costeo/costeo.js`
  - Registro de eventos del form y child tables.
  - UI de arbol de costos.
  - Modal de edicion de desglose.
  - Automatizacion para crear:
    - BOM
    - Subcontracting BOM
    - Quotation
    - Sales Order
    - Production Plan

## Refactor aplicado

- Se modularizo `costeo.js` en `costeo_yelke/costeo_yelke/doctype/costeo/modules/`.
- Se agrego `build_costeo_js.sh` para ensamblar el archivo final cargado por Frappe.
- Se agrego un tab de `Plan de Produccion` dentro de `Costeo`, con campos/tablas equivalentes a `Production Plan`.
- Se agrego flujo de desbloqueo:
  - el tab de Plan de Produccion inicia bloqueado
  - se habilita y prellena desde el boton `Desbloquear y Prellenar Plan de Producción`
  - usa los datos de la primera pestaña y la orden de venta relacionada
- Se implementaron automatizaciones separadas para:
  - creacion de Work Orders
  - creacion de Subcontracting Purchase Orders
  - creacion de Material Request
- Se documento la arquitectura frontend en:
  - `costeo_yelke/costeo_yelke/doctype/costeo/README.md`

## Notas de mantenimiento

- El comportamiento funcional se conserva.
- Para cualquier cambio de UI/logica cliente:
  1. Editar modulo correspondiente en `modules/`.
  2. Ejecutar build:
     `./costeo_yelke/costeo_yelke/doctype/costeo/build_costeo_js.sh`
  3. Validar en formulario `Costeo` (refresh, modal, calculos y automatizaciones).
