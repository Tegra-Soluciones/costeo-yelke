# Plan de acción — Producción por pantallas

Rama: `fix/listo-produccion` · Fecha: 2026-10-05 · Estado: **propuesta, sin código**

---

## 1. Qué encontré en el código

### Cómo está hecho hoy
- **Todo Producir vive en una sola página.** Es `CosteoDetailPage.vue`, de 6,471 líneas. El paso Producir ocupa ~1,140 de ellas (líneas 1435–2577); del lote en adelante es ~830 (1742–2577).
- **Los datos y acciones están en un solo lugar.** Viven en `useProduccion.js` (~1,900 líneas), así que partir la pantalla no obliga a reescribir la lógica.
- **Solo hay un documento "abierto" a la vez.** `subPo`, `scoSel`, `docCompra`, `reciboPr`, `transDoc` y `scr` son uno solo cada uno. Eso encaja bien con un panel lateral, que también muestra un documento a la vez.
- **Navegación:**
  - `activeStep` más `?step=` y `?lote=` en la URL.
  - El último lote abierto se recuerda en el navegador (localStorage).
  - No existen sub-rutas: dentro del lote, lo que está abierto depende de `loteDocOpen`, `subStepOpen` y `loteParadaActiva`, que se pierden al recargar.
- **La pantalla del lote apila, de arriba abajo:**
  1. Material en talleres.
  2. Materia prima del lote: un grupo por proveedor, cada uno con 5 botones (Solicitud de cotización → Cotización → OC → Recibo → Factura) que se despliegan ahí mismo.
  3. Órdenes de manufactura (recién agregado).
  4. Flujo del lote: matriz pieza × etapa, ramas y cadena final.
  5. Entrega del lote.
  6. Detalle de la parada: "Siguiente paso" más 5 pasos (OC, Encargo, Transferencia, Recibo, Factura). Cada paso tiene sus encargos, costos adicionales y la OM.

  Son 3 niveles de cosas que se despliegan una dentro de otra en una sola columna.
- **Ya existe la idea de "Siguiente paso"**, pero solo dentro de una parada (`guiaParada`). No existe a nivel lote ni a nivel Producir.

### OV activa — cómo funciona y qué falla
- `ActiveSOSelector` aparece en Producir, Enviar, Facturar y Reporte. Al cambiar de OV se recarga todo.
- **El plan es por OV** (`_get_plan_for_so`). `produccion_completa`, las remisiones, la factura y el reporte final sí filtran por OV.
- ⚠ **`get_lotes_produccion(plan)` NO filtra por OV.** Usa el plan solo para saber el costeo y luego trae todo lo del costeo:
  - Solicitudes de material.
  - OC de material.
  - Solicitudes de cotización y cotizaciones de proveedor.
  - OC de maquila.
  - Encargos.

  Con dos OV en el mismo costeo, por ejemplo una réplica de pedido, la OV-B mostraría los lotes y documentos de la OV-A. Además, el siguiente "Lote N" se numera contando las dos.

  Para filtrar sí hay con qué:
  - `Material Request Item.production_plan`.
  - `Purchase Order Item.production_plan` en las OC de maquila (lo pone `plan_crear_subcontratacion`).
  - `Purchase Order Item.sales_order` en las OC de material.

  En sandbox no existe ningún costeo con 2 OV, así que **está sin probar**. Es lo primero que hay que reproducir.
- ⚠ **Las tallas de la OM general salen del costeo, no de la OV** (`om_general.tallas_de_producto`). Una réplica con otra cantidad imprimiría tallas equivocadas en la orden de maquila.

### Multi-producto — qué implica para la pantalla
- Un lote trae `productos[]`, cada uno con su cantidad.
- **Las paradas se comparten:** un mismo taller y paso puede cubrir varios productos.
- **La materia prima no es de un producto.** La solicitud de material cubre todo el costeo y una OC de material puede servir a varios productos.
- La OM es **una por producto base**, con su variante de talla adentro.
- **Conclusión:** no conviene hacer "una pestaña por producto", porque compras y talleres son compartidos. Lo que conviene es un **filtro de producto** (Todos / Chamarra / Pantalón…) en Flujo, Talleres y Envíos, y mostrar "para qué productos" en cada compra.

---

## 2. Estructura propuesta

```
Costeo   Costear · Cotizar · Vender · Alta · Flujo · PRODUCIR · Enviar · Facturar · Reporte
                                                        │
PRODUCIR ───────────────────────────────────────────────┘
│  ┌──────────────────────────────────────────────────────────────────┐
│  │ OV activa: SO-0012 ▾   (todo lo de abajo es de esta OV)         │  ← fija arriba
│  └──────────────────────────────────────────────────────────────────┘
├─ Tablero               avance de la OV, lotes como tarjetas, pendientes
├─ Preparación           plan, solicitud de material, definir lotes, validar OC de maquila
├─ Orden de manufactura  una por producto base (ficha del costeo, tallas de la OV)
└─ Lotes:  Lote 1 · Lote 2 · +        (de ESTA OV)
           │
           LOTE 1 ─ Resumen · Materia prima · Flujo · Talleres · Envíos · Facturas · Entrega
```

### Qué pasa con la OV activa en cada nivel
| Nivel | Depende de la OV | Nota |
|---|---|---|
| Tablero, Preparación, Lotes | Sí | Hoy ya es así, salvo el bug de `get_lotes_produccion` |
| Orden de manufactura: ficha (modelo, tela, procesos, archivos…) | No | La comparten todas las OV del costeo; se avisa "la usan N OV" |
| Orden de manufactura: tallas | Sí | Se calculan con la cantidad de la OV de cada OC |
| Pestañas del lote | Sí | El lote pertenece a una OV |

**Si cambias de OV estando dentro de un lote**, te regresa al Tablero, porque ese lote no existe en la otra OV.

### La URL lleva todo el contexto
```
?step=5&ov=SO-0012&vista=lote&lote=Lote%201&tab=talleres&parada=<id>&paso=recibo
```
- Recargar la página o compartir el enlace deja a la persona en el mismo lugar.
- Va con query params, sin tocar el router.
- Lo que se recuerda en el navegador pasa a guardarse por costeo **y por OV**.

---

## 3. De dónde sale cada pestaña

### Nivel Producir
| Pantalla | Contenido | Viene de (CosteoDetailPage.vue) |
|---|---|---|
| Tablero | Barra de avance + una tarjeta por lote (MP %, maquila %, entregado) + lista "por hacer" con enlace directo | `ProductionProgressBar` (1440) + `LoteCard` existente + nuevo cálculo de pendientes |
| Preparación | Resultado de la preparación, plan, solicitud de material, lotes de entrega, validar OC de maquila y su OM legacy | 1447–1740 |
| Orden de manufactura | `OmGeneralEditor` | Hoy está dentro del lote (1905); se mueve aquí |

### Nivel Lote
| Pestaña | Quién la usa | Contenido | Viene de |
|---|---|---|---|
| **Resumen** | Todos | Productos y cantidades, avance por etapa, **un solo "Siguiente paso" del lote** | Encabezado (1748) + `guiaParada` llevado a nivel lote |
| **Materia prima** | Compras | Tabla con una fila por proveedor: materiales, para qué productos, y los indicadores OC · Recibo · Factura. Clic → **panel lateral** con el documento. Solicitud de cotización y cotización ocultas salvo que se usen | 1785–1902 |
| **Flujo** | Jefe de producción | Matriz y ramas como mapa, selección para "Crear orden". Clic en una parada → Talleres | 1912–2088 |
| **Talleres** | Jefe de producción | Lista con una fila por parada: taller, etapa, productos, piezas, y los indicadores OC · Encargo · Envío · Recibo · Factura. Clic → detalle con sub-pestañas: **Encargo · OM del taller · Envío · Recibo · Factura** (y OC si falta validar) | 2131–2560 |
| **Envíos** | Almacén | Todo lo que sale a talleres y lo que regresa, por fecha, y "Material en talleres" (sobrantes y devolución) | 1758–1784 + transferencias y recibos de las paradas |
| **Facturas** | Contabilidad | Lista única de facturas del lote (material y maquila): proveedor, importe, folio, estado. Se validan aquí o se va al paso de origen | Datos que ya trae `get_lotes_produccion` (`factura`, `facturado`) |
| **Entrega** | Ventas / almacén | Remisión del lote; se habilita cuando la maquila termina | 2090–2129 |

Cada pestaña muestra un indicador: ✓ completa, un número de pendientes o ⚠ bloqueada.

En Flujo, Talleres y Envíos hay un **filtro de producto** cuando el lote tiene más de uno.

### Reglas de interacción
1. **Un solo "Siguiente paso" por pantalla**, calculado del estado real.
2. **Las listas solo muestran el estado; el formulario se abre en un panel lateral o sub-pestaña.** Ya no se despliega en medio de la página.
3. **Lo opcional va escondido en "Más opciones":** costos adicionales, solicitud de cotización, otro encargo y el registro anterior.
4. **Mismos colores que hoy:** verde = hecho, índigo = facturado, ámbar = pendiente, rojo = bloqueado.

---

## 4. Fases

### Fase 0 — Bases (backend, antes de tocar la pantalla)
- **0a. Filtrar lotes por OV** en `get_lotes_produccion`:
  - Solicitudes de material por `production_plan`.
  - OC de maquila por `Purchase Order Item.production_plan`.
  - OC de material, solicitudes de cotización y cotizaciones de proveedor por su solicitud de material o `sales_order`.
  - El siguiente "Lote N" se cuenta solo dentro de la OV.

  ⚠ **Se cambia lo que recibe `_lote_paradas`, pero `_lote_paradas` mismo no se toca.** Si resultara necesario modificarlo, lo pregunto antes.
- **0b. Tallas de la OM por OV:** `om_de_oc` toma la OV de la OC y calcula con esas cantidades. Si la OV es réplica con otra cantidad, se reparte proporcional, igual que el reporte final.
- **0c. Prueba con 2 OV en YELKE PRUEBAS:**
  1. Duplicar la OV de un costeo de prueba.
  2. Preparar las dos.
  3. Abrir un lote en cada una.
  4. Confirmar que no se mezclan.
- **Entregable:** el bug reproducido antes del cambio y corregido después, más la "foto" de regresión de todos los costeos sin cambios.

### Fase 1 — Esqueleto (sin cambiar comportamiento)
- Sacar Producir de `CosteoDetailPage.vue` a componentes:
  - `produccion/ProducirShell.vue`: OV activa + sub-navegación + lectura y escritura de la URL.
  - `ProducirTablero.vue`
  - `ProducirPreparacion.vue`
  - `ProducirOm.vue`
  - `LoteShell.vue`: encabezado + pestañas.
- Las pestañas del lote, al inicio, solo muestran los bloques actuales cortados por sección. Mismo comportamiento, ya separado.
- Todos comparten la misma instancia de `useProduccion`.
- **Entregable:** misma funcionalidad, pantallas separadas, URL con contexto. Se verifica recorriendo la chamarra 00022 y un costeo multi-producto.

### Fase 2 — Lote: Resumen, Materia prima, Flujo
- `LoteResumen` con "Siguiente paso" a nivel lote: la primera cosa pendiente entre materia prima → envío → maquila → factura → entrega.
- `LoteMateriaPrima`: tabla por proveedor + panel lateral reutilizando `PurchaseDocPanel` y `FacturaCompraPanel`.
- `LoteFlujo`: la matriz actual; el clic lleva a Talleres.

### Fase 3 — Talleres y Envíos
- `LoteTalleres`: lista de paradas + detalle con sub-pestañas, reutilizando `EncargoResumen`, `OmTallerView` y `FacturaCompraPanel`.
- `LoteEnvios`: vista por fecha + material en talleres.

### Fase 4 — Facturas, Entrega y Tablero
- `LoteFacturas` (lista consolidada), `LoteEntrega` (lo de hoy) y el Tablero con la lista de pendientes.

### Fase 5 — Pulido
- Filtro de producto, versión móvil, quitar el código que quede muerto en `CosteoDetailPage.vue`.
- Opcional: pestaña inicial según el rol (almacén → Envíos).

**En cada fase:**
- `vite build`.
- Recorrido completo en sandbox (chamarra con variante XXL, camisola multi-lote y la prueba de 2 OV).
- Sin despliegue hasta que me digas.

---

## 5. Riesgos y cuidados
- **Hay mucho trabajo sin commit en la rama** (OM general, facturas en el lote, etc.). Conviene hacer commit **antes** de la Fase 1 para poder comparar y revertir.
- **Documentos "únicos" en `useProduccion`:** el panel lateral solo puede mostrar uno a la vez. Es aceptable, pero cambiar de pestaña debe cerrarlo.
- **Lotes de antes sin `production_plan` en sus líneas:** la Fase 0 necesita un respaldo (si el costeo tiene una sola OV, se muestra todo como hoy).
- **El cambio de frontend en producción es grande.** Se despliega por fases: 0 primero (es backend y corrige un bug), luego 1–2 y luego 3–5.

---

## 6. Decisiones pendientes
1. **OM a nivel Producir, compartida por las OV del costeo, con tallas por OV.** Recomendado.
2. **Envíos:** pestaña propia para almacén, además del paso dentro de cada taller. Recomendado.
3. **Facturas:** pestaña consolidada por lote. Recomendado.
4. **Roles:** ¿alguien debe ver solo su pestaña, o basta con que entre directo a ella?
5. **¿Hago commit de lo actual** antes de empezar?
