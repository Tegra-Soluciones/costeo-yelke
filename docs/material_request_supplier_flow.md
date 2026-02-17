# Flujo de proveedor para materias primas (Costeo + Plan de Produccion + MR)

## Objetivo
Agregar y propagar el proveedor de cada materia prima desde Costeo hasta:
- la tabla `mr_items` (Materias primas) del Plan de Produccion embebido en Costeo
- la tabla `items` de `Material Request`
- la creacion de `Purchase Order` desde `Material Request` (una OC por proveedor)

## Cambios de esquema (empaquetados en la app)
Patch: `costeo_yelke.patches.v0_0_3.add_material_request_supplier_fields`

Custom Fields agregados:
- Doctype: `Material Request Plan Item`
  - `supplier` (Link -> `Supplier`)
- Doctype: `Material Request Item`
  - `supplier` (Link -> `Supplier`)

## Flujo en Costeo (Plan de Produccion embebido)
Archivo: `costeo_yelke/costeo_yelke/doctype/costeo/modules/37_production_plan_tab.js`

1. Se construye un mapa `item_code -> supplier` desde `costeo_producto_detalle`, filtrando solo filas de tipo `Materia Prima`.
2. Ese mapa se aplica a `mr_items` al ejecutar:
   - `Desbloquear y Prellenar Plan de Produccion`
   - `Obtener Materias Primas para Comprar` (`get_items_for_mr`)
3. Si hay el mismo item con proveedores diferentes en Costeo, se muestra advertencia y se usa el primer proveedor.

## Flujo backend al crear Solicitud de Materia Prima
Archivo: `costeo_yelke/costeo_yelke/doctype/costeo/costeo.py`

`pp_make_material_request` ahora:
1. Mapea proveedor por materia prima desde Costeo.
2. Asigna `supplier` en `pp.mr_items`.
3. Crea `Material Request` replicando la logica de ERPNext y copiando `supplier` a `Material Request Item` cuando el custom field existe.

## Creacion de OC por proveedor desde Material Request
Hook: `override_whitelisted_methods` en `costeo_yelke/hooks.py`
Metodo override:
`erpnext.stock.doctype.material_request.material_request.make_purchase_order`
-> `costeo_yelke.overrides.material_request.make_purchase_order`

Comportamiento:
- Si todas las filas pendientes tienen `supplier`, crea una OC por proveedor de forma automatica.
- Si no aplica (sin supplier, supplier parcial, default supplier explicito, etc.), usa el flujo estandar de ERPNext.

## Despliegue
1. `bench --site <tu_sitio> migrate`
2. `bench --site <tu_sitio> clear-cache`
3. recargar el navegador (hard refresh)
