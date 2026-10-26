# 04 · Mapa de la pantalla

Cómo se parte `frontend/src/pages/CosteoDetailPage.vue` (9,116 líneas). Números de línea al
15-oct-2026; **búscalos por el comentario de sección**, no por número (cambian).

## 1. Estado actual

- Template: líneas 1–3264. Script (`<script setup>`): 3266–9064. Estilos: 9066–fin.
- 58 `ref`, 91 `computed`, 11 `watch`, 332 funciones, 79 llamadas al servidor, un solo
  `provide("produccion", …)` (línea ~4455) que comparte `useProduccion.js` con los hijos.
- Pasos (`activeStep`): 0 Costear · 1 Cotizar · 2 Vender · 3 Alta de productos · 4 Flujo de
  producción · 5 Producir · 6 Enviar · 7 Facturar. Ojo: el stepper visual (`CosteoStepper.vue`)
  usa otro orden (`ORDER` vs `STEPS`); no mezclar los índices.

### Template

| Líneas | Comentario de sección | Destino |
|---|---|---|
| 1–151 | encabezado, stepper, menú del documento | cascarón `CosteoDetailPage.vue` |
| 152–634 | `STEP 0 · COSTEAR` (incluye variante de talla 564–634) | `pasos/PasoCostear.vue` + `componentes/costeo/{ProductosEditor,MaterialesEditor,EtapasEditor,VarianteTallaModal}.vue` |
| 635–840 | `STEP 1 · COTIZAR` | `pasos/PasoCotizar.vue` |
| 841–1207 | `STEP 2 · VENDER` | `pasos/PasoVender.vue` |
| 1208–1283 | `STEP 3 · ALTA DE PRODUCTOS` | `pasos/PasoAltaProductos.vue` |
| 1284–1542 | `STEP 4 · FLUJO DE PRODUCCIÓN` | `pasos/PasoFlujo.vue` |
| 1543–1628 | `STEP 5 · PRODUCIR` (armazón) + `TABLERO` | `pasos/produccion/PasoProducir.vue` + `VistaTablero.vue` |
| 1629–1927 | `PREPARACIÓN` (Plan 1650, Materia prima 1752, OM 1913) | `produccion/VistaPreparacion.vue` (+ `TarjetaPlan`, `TarjetaMateriaPrima`, `TarjetaOrdenManufactura`) |
| 1928–1958 | `ÓRDENES A TALLERES` | `produccion/VistaTalleres.vue` |
| 1959–2664 | `LOTE` | `produccion/VistaLote.vue` (+ subcomponentes por paso del lote) |
| 2665–2720 | `ENVÍOS (bandeja)` | `produccion/VistaEnvios.vue` |
| 2721–2754 | `FACTURAS (bandeja)` | `produccion/VistaFacturas.vue` |
| 2755–3075 | paneles laterales: Remisión, Proveedor de MP, Orden a taller, Ficha de manufactura, Factura de compra, Nuevo lote | `produccion/paneles/Panel*.vue` (uno por panel) |
| 3076–3080 | `STEP 6 · ENVIAR` | `pasos/PasoEnviar.vue` |
| 3081–3264 | `STEP 7 · FACTURAR` (+ modales finales) | `pasos/PasoFacturar.vue` |

### Script

| Líneas | Comentario de sección | Destino |
|---|---|---|
| 3266–3730 | imports, estado base, carga del costeo | cascarón + `useCosteoDoc.js` |
| 3731–3822 | `OC del cliente` | `useVenta.js` |
| 3823–4196 | `Cantidades confirmadas por talla`, `Desglose por talla`, almacenes/compañía | `useVenta.js` (tallas) + `useCosteoDoc.js` (almacenes) |
| 4197–4660 | `PRODUCCIÓN v2 · armazón`, `Estado de cada paso del lote`, `Navegación`, `Datos del menú`, `Encabezado y stepper de cada vista`, `Filtro de producto`, `Tablero` | `produccion/useProduccionNavegacion.js` |
| 4661–4870 | `Bandeja de Envíos`, `Bandeja de Facturas` | `produccion/useBandejas.js` |
| 4871–5165 | paneles `Orden a un taller`, `Nuevo lote`, pasos del lote (entrega, flujo, materia prima) | `produccion/usePanelesLote.js` |
| 5166–5515 | `Panel "Remisión"` | `useEntregas.js` |
| 5516–5702 | `Talleres` (matriz, sub-pantalla, tira de piezas, paneles del taller) | `produccion/useTalleres.js` |
| 5703–6583 | `LA BARRA DE ACCIONES` | `useBarraAcciones.js` |
| 6584–6727 | `Computed` (incluye `headerDoc`, el documento del menú por paso) | `useBarraAcciones.js` / cascarón |
| 6728–6912 | `Helpers`, `Filters`, `Reparto de un material entre varias etapas` | `calculo/*.js` (funciones puras) |
| 6913–7578 | `Product / detail / stage`, `Tipo de materia prima`, `UDM reales`, cálculos de costo | `useCosteoDoc.js` + `calculo/costeo.js` (puras: costos, reparto, UDM, redondeos) |
| 7579–7745 | `Validate / payload` | `useCosteoDoc.js` |
| 7746–7890 | `Notas de remisión` | `useEntregas.js` |
| 7891–7983 | `Facturas de compra` | `useFacturacion.js` |
| 7984–8364 | `Flujo de Producción (paso 4)` | `useFlujoProduccion.js` |
| 8365–8440 | `Borrador local (localStorage)` | `useCosteoDoc.js` |
| 8441–8708 | `Advance`, `Acciones específicas de cada paso`, `Validar / borrador` | `useBarraAcciones.js` + `useDocumentos.js` |
| 8709–8902 | `Materializar Producto Terminado`, `Checklist de materialización` | `useAltaProductos.js` |
| 8903–8985 | `Kebab` (menú del documento) | cascarón |
| 8986–9064 | `Lifecycle` | cascarón |

`useProduccion.js` (2,125 líneas) se parte en la F5–F6 con el mismo criterio:
plan · materia prima · OM · talleres · lotes · envíos · facturas.

## 2. Estructura destino

```
frontend/src/
  pages/costeo/
    CosteoDetailPage.vue          cascarón (≤ 600 líneas)
    pasos/
      PasoCostear.vue  PasoCotizar.vue  PasoVender.vue  PasoAltaProductos.vue
      PasoFlujo.vue    PasoEnviar.vue   PasoFacturar.vue
      produccion/
        PasoProducir.vue  VistaTablero.vue  VistaPreparacion.vue  VistaTalleres.vue
        VistaLote.vue     VistaEnvios.vue   VistaFacturas.vue
        paneles/PanelRemision.vue PanelProveedorMp.vue PanelOrdenTaller.vue
                PanelFicha.vue PanelFacturaCompra.vue PanelNuevoLote.vue
  componentes/costeo/             editores reutilizables del paso Costear
  composables/costeo/
    contexto.js                   provide/inject: claves y helper useContextoCosteo()
    useCosteoDoc.js useVenta.js useAltaProductos.js useFlujoProduccion.js
    useEntregas.js useFacturacion.js useBarraAcciones.js useDocumentos.js
    produccion/                   partes de useProduccion.js
    calculo/                      funciones PURAS (sin Vue ni servidor) → con pruebas Vitest
```

- Cada paso se carga con `defineAsyncComponent(() => import("./pasos/PasoX.vue"))`.
- Los composables se crean **una vez** en el cascarón y se comparten con `provide`. Un paso nunca
  crea su propia copia del estado del costeo.
- Rutas, `?vista=`, `?tpaso=` y demás parámetros de URL **no cambian** (los usa
  `useProduccionRuta.js` y los enlaces del manual).
- Sin cambios visuales. El objetivo es el mismo DOM con otra organización del código.

## 3. Pantallas duplicadas (F8)

| Pantalla | Líneas | Debe reutilizar |
|---|---|---|
| `CotizacionDetailPage.vue` | 1,445 | `PasoCotizar.vue` (modo independiente) + `useVenta.js` |
| `SalesOrderDetailPage.vue` | 1,024 | `PasoVender.vue` + `useVenta.js` |
| `SalesInvoiceDetailPage.vue` | 780 | `PasoFacturar.vue` (venta) + `useFacturacion.js` |
| `PurchaseOrderDetailPage.vue` | 719 | `PurchaseDocPanel.vue` (ya existe) |

Antes de unificar, F8 compara qué hace cada pantalla independiente que el paso no hace (y al
revés) y lo anota. Si hay diferencias de comportamiento, se pregunta al usuario cuál gana.

## 4. Escritorio de ERPNext (F9)

`costeo_yelke/costeo_yelke/doctype/costeo/costeo.js` + `modules/*.js` (~8,300 líneas) es el
formulario del Costeo dentro de ERPNext, anterior a la SPA. Retirarlo **requiere decisión del
usuario** (¿alguien lo usa? ¿los botones del escritorio deben seguir?). F9 solo prepara el
inventario y la propuesta; no borra nada sin el sí del usuario.
