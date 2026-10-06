# Plan — Producción por pantallas, pestañas y roles

> **Para la siguiente sesión:** este documento es la fuente de verdad. Léelo completo antes de tocar código.
>
> - Mockups: [`docs/mockups/produccion.html`](mockups/produccion.html). Ábrelo en el navegador; usa datos reales de la chamarra.
> - Rama: `fix/listo-produccion`.
> - Base: commit `27f5b59` (todo lo anterior ya commiteado).
> - Fecha del plan: 2026-10-06.
> - Estado: **aprobado por el usuario, sin código todavía.**

---

## 0. Decisiones ya tomadas por el usuario (no volver a preguntar)

| # | Decisión | Respuesta |
|---|---|---|
| 1 | La orden de manufactura (OM) sale del lote y sube a Producir; la comparten las OV del costeo y las tallas se calculan por OV | **Sí** |
| 2 | Commit de lo pendiente antes de empezar | **Hecho** (`27f5b59`) |
| 3 | Pestañas propias de **Envíos** y de **Facturas** | **Sí** |
| 4 | **Un rol por cada vista** ("pestaña padre"). Quien necesite dos vistas recibe los dos roles | **Sí** |
| 5 | Mantener todo lo que hoy se muestra. **No omitir ningún dato ni acción** | Regla dura; ver §9, matriz de trazabilidad |

### Ajuste de diseño respecto a la primera propuesta (explicárselo al usuario si pregunta)
**Envíos** y **Facturas** quedan a nivel **Producir** (de la OV activa), con filtro por lote, y **no** dentro de cada lote. Hay cuatro razones, todas verificadas en datos reales:

- **La factura de maquila es por taller, no por lote.** Se factura contra la OC del taller, que cubre todos sus lotes.
  - `maquila_pendiente` es el mismo número en Lote 1 y Lote 2. Ejemplo: corte ALEJANDRO TORRES = $18,330 en ambos.
  - Dentro de un lote se vería duplicado.
- **El sobrante en talleres es por almacén del taller**, no por lote (`sub_saldo_talleres(costeo)`).
- **Almacén trabaja por lo que hay que mover hoy**, sin importar el lote.
- **Desde el lote no se pierde nada:** su Resumen muestra los conteos de Envíos y Facturas de ese lote, con enlace a la vista ya filtrada.

---

## 1. Reglas del proyecto (obligatorias)

### Entorno
- Rama `fix/listo-produccion`. **Sin commits ni despliegue a producción hasta que el usuario lo pida.**
- Sitio de pruebas: `sandbox.local` (127.0.0.1:8001). SPA en `/costeo-yelke/costeo/<name>`.
- Compañía de pruebas: **YELKE PRUEBAS (YP)**. No tocar datos de YELKE TEXTILES ni de Tegra.

### Cómo correr y construir
- Scripts: desde `frappe-bench-v15/sites`, con `../env/bin/python script.py`, `frappe.init(site="sandbox.local", sites_path=".")` y `frappe.connect()`. Para pruebas, `frappe.db.rollback()` al final.
- Patches: `bench --site sandbox.local execute costeo_yelke.patches.vX.Y.execute`, y agregarlos a `patches.txt`.
- DocTypes nuevos: `frappe.reload_doc(...)`. Print formats: `frappe.reload_doc(module, "Print Format", name, force=True)`. Después, `bench --site sandbox.local clear-cache`.
- Frontend: `cd frontend && ./node_modules/.bin/vite build`. Los assets compilados **sí se commitean** (`costeo_yelke/public/costeo-app`).

### Restricciones
- **`_lote_paradas` NUNCA se modifica sin instrucción explícita del usuario.** Se puede cambiar lo que se le pasa, no la función.
- **No sobre-diseñar.** Reutilizar los componentes y funciones existentes (lista en §2.5). Esto es un reacomodo, no una reescritura.
- **UDM y precio de las compras solo se editan en la OC**, nunca en la solicitud de material.
- **Español** en todo lo que ve el usuario. El mismo tono y los mismos textos de ayuda que hoy, copiados tal cual salvo que el plan diga otra cosa.

### No romper
- **Varios productos por costeo:** un lote trae `productos[]`, cada uno con cantidad; las paradas pueden cubrir varios productos; la base y su variante de talla son 2 productos.
- **OV activa:** todo Producir se filtra por ella.
- **Piezas:** la matriz pieza × etapa, el punto de ensamble y la cadena final.
- **Doble validación de OC:** Revisor → Aprobador.

---

## 2. Cómo está hoy (inventario exacto)

Archivo principal: `frontend/src/pages/CosteoDetailPage.vue`, de 6,471 líneas.

**Estado y acciones:** `frontend/src/composables/useProduccion.js`, de ~1,900 líneas. Una sola instancia, desestructurada en la página (~línea 3540–3569).

**Pasos del stepper:**

| Índice | Paso |
|---|---|
| 0 | Costear |
| 1 | Cotizar |
| 2 | Vender |
| 3 | Alta de Productos |
| 4 | Flujo de Producción |
| 5 | **Producción** |
| 6 | Enviar (remisión) |
| 7 | Facturar (solo venta) |
| 8 | Reportar |

- `activeStep` controla cuál se ve. La URL acepta `?step=`, `?lote=`, `?highlight=` y `?doctype=`.
- El último lote abierto se guarda en `localStorage["costeo_ultimo_lote_<costeo>"]`.

### 2.1 Paso 5 · Producción, vista general (sin lote abierto) — líneas 1435–1740

| # | Bloque | Líneas | Qué muestra | Acciones |
|---|---|---|---|---|
| G1 | `ActiveSOSelector` | 1438 | Selector "OV activa" de las OV del costeo | Cambiar OV, que recarga todo (`watch(activeSOName)` ~4130) |
| G2 | `ProductionProgressBar` | 1440 | % materia prima recibida (`materiaPrimaPct`), % maquila (`subcontratacionPct`) y texto "X/Y lotes recibidos" (`prodComplete`); envío = null | — |
| G3 | Resultado de la preparación | 1448–1456 | Lista `prepSteps`: ✓ o ⚠, etiqueta y detalle ("ya existía" / "N creado(s)") | — |
| G4 | Estado vacío "Aún no has creado el plan" | 1458–1465 | Texto explicativo | **Preparar producción** (`prepararProduccion`) |
| G5 | Plan de producción (`<details>`, se colapsa solo al validarse) | 1469–1541 | Nombre del plan, estado, enlace a ERPNext, almacén de materias primas (editable antes de validar), OV, cantidad total planeada, **Cantidad a producir** por artículo (editable, máximo +5%, borde rojo al pasarse), texto del +5%, **Materias primas a comprar** (artículo × cantidad UDM, almacén) o "Sin faltantes…" | **Obtener materias primas**, **Guardar**, **Validar plan**; ya validado: **Orden de trabajo** (producción interna, opcional, con "N creada(s)") |
| G6 | Materia prima (solicitud de material) | 1544–1649 | Vacío: "Aún no has creado la solicitud…". Con solicitud: nombre, estado, ERPNext, Tipo, **Fecha requerida** (editable), Estatus, tabla Artículo / Cantidad (±5%, borde rojo) / UOM / Proveedor (editable), textos "±5%" y "UDM y precio en la OC" | **Crear solicitud de material**, **Guardar**, **Validar solicitud** o "Validar y dividir en N lote(s)" (deshabilitado si `mrLotesInvalidos`) |
| G7 | Lotes de entrega (opcional, antes de validar la solicitud) | 1592–1640 | Por lote: nombre editable, fecha requerida, piezas por producto (borde rojo si se excede), "Materiales estimados" (`mrLotesPreview`); al pie, pendiente sin asignar por producto (rojo si excede, ámbar si falta) y mensaje de error | **+ Lote**, quitar lote, **Repartir en partes iguales** |
| G8 | "Continuar a producción" | 1656–1664 | Solo si la solicitud está validada, no hay lotes y el formulario está cerrado | **Continuar** (`abrirNuevoLote`) |
| G9 | Nuevo lote de producción | 1667–1738 | (a) cargando "Preparando el lote…"; (b) sin OC de maquila: texto + **Crear órdenes de subcontrato**; (c) prerrequisito "valida la OC de maquila de cada taller": `PurchaseDocPanel` de la OC del taller (doble validación, enviar, vista previa) + texto "una sola ficha técnica" + `OmTallerView` u `OrdenManufacturaForm` legacy; (d) formulario: por producto cantidad + "pendiente N" o "Valida antes la 1ª OC…", fecha, avisos "limitado por stock" y "Revisando materia prima…" | **Cancelar**, **Abrir lote** (`crearNuevoLote` → `lote_abrir`) |

**Stepper** (`CosteoStepper.vue`):
- Debajo de "Producción" hay un riel de lotes con un chip por lote (punto de color, ✓ si `done`) → `select-lote`.
- El botón **+** → `create-lote` abre G9.

### 2.2 Paso 5 · Pantalla de un lote — líneas 1742–2575

| # | Bloque | Líneas | Qué muestra | Acciones |
|---|---|---|---|---|
| L0 | "Volver a Producir" + encabezado | 1744–1756 | `lote_ref` · fecha; renglón de productos "Nombre: qty · Nombre: qty" | Volver |
| L1 | **Material en talleres** | 1763–1783 | Aviso ámbar si la producción terminó, o texto de "sobró al redondear"; por taller, materiales libres (nombre, cantidad, UDM) | **Registrar devolución** (`devolverMaterialTaller` → `sub_devolver_material`) |
| L2 | **Materia prima de este lote** | 1786–1903 | Ver detalle abajo | Ver detalle abajo |
| L3 | **Órdenes de manufactura** (`OmGeneralEditor`) | 1906–1910 | Ver §2.4 | Ver §2.4 |
| L4 | **Flujo de este lote** | 1915–2088 | Ver detalle abajo | Ver detalle abajo |
| L5 | **Entrega del lote al cliente** | 2093–2128 | Sin producción: "Se habilita cuando…". Con producción: tabla Producto / Producido / Ya en remisión / Por entregar, y chips "Remisiones de este lote: NOMBRE · validada/borrador" | Botón con 3 estados: "Crear remisión del Lote N (X prendas)" / "Todo el lote ya está en remisión" / "Esperando fin de producción" (`crearRemisionLote` → `crear_remision(lote_ref)`, salta al paso 6). Clic en un chip → `irARemision` |
| L6 | Detalle de la **parada** (taller) abierta | 2130–2562 | Ver detalle abajo | Ver detalle abajo |
| L7 | Lote sin ninguna parada | 2569–2573 | Texto | **Crear órdenes de subcontrato** (`crearSubcontratosDesdeLote`, que además revisa y valida las OC) |

**L2 · Materia prima de este lote:**
- **Aviso azul de neteo** (`neteoOc`): por material, "la solicitud pide X / ya tienes Y / se compran Z", más un texto sobre el lote de tintura.
- **Un grupo por proveedor** (`proveedoresLote(lote)`):
  - Encabezado y materiales (código × cantidad UDM).
  - Cinco botones-acordeón (`toggleLoteDoc`), cada uno con su estado de color: verde = validado, índigo = facturado, ámbar = factura en borrador, naranja = abierto.
    1. **Solicitud de cotización**: crea o abre la solicitud. Muestra su nombre y ✓.
    2. **Presupuesto de proveedor**: crea o abre la cotización del proveedor.
    3. **Orden de compra**: "Generar orden de compra" o su nombre; " · enviado" si `enviado_el`.
    4. **Recibo de compra**: deshabilitado si la OC no está validada.
    5. **Factura de compra**: deshabilitada sin recibo validado; tooltip; "· borrador".
  - Paneles:
    - **Solicitud de cotización / Presupuesto / OC** → `PurchaseDocPanel`:
      - Editables: UDM y proveedor solo en OC; cantidad solo en solicitud y presupuesto.
      - **Jalar precios** (solo OC).
      - Texto de ayuda largo de la OC.
      - Doble validación (revisar / aprobar).
      - Enviar, vista previa en línea.
    - **Recibo** → `PurchaseDocPanel`: almacén, "IVA aplicado…", "Validar recibo", **costo de envío obligatorio** (toast si falta).
    - **Factura** → `FacturaCompraPanel`.

**L4 · Flujo de este lote:**
- **Con piezas** (`loteActivo.ramas`):
  - Título con productos (`paradaProductosTexto`) y contadores por estado (`contadoresRamas`: recibidas / listas para encargar / encargadas / en espera).
  - **Matriz pieza × etapa** (`rama_etapas`):
    - Cada columna: orden, título, taller, **$ por prenda** y botón "Listas (N)" / "Quitar" (`toggleColumna`).
    - Cada fila: pieza, "×N por prenda · total pzas" o "N pzas".
    - Cada celda: "no aplica", o botón con checkbox si está lista, ✓ verde (recibido) o índigo (facturado). Muestra el servicio y el estado (`pasoEstadoTexto`/`pasoEstadoColor`).
    - Clic: si está lista, `marcarCelda`; si no, `abrirCelda`.
  - **Barra de selección**: por taller, "TALLER · etapa" y las piezas; **Limpiar**; **Crear orden / Crear N órdenes** (`crearOrdenesSeleccion` → `parada_registrar_entrega`). Si no hay selección, se ve el texto de ayuda.
  - **Cadena final** (`cadenaFinal`):
    - Tarjetas numeradas: título, taller, "· facturado".
    - Si arma la prenda: "N de M piezas listas" con barra. Si no: "Recibe la prenda armada de …".
    - Botón con estados: Encargar confección / Encargar / Confección recibida / Recibido / Faltan N piezas / Espera el paso anterior / Ver encargo (`abrirConfeccion`).
- **Sin piezas** (`tracksLote`): un carril por producto con sus paradas (título, taller, cantidad, estado), flecha y **tarjeta del producto terminado** (imagen, nombre, cantidad, Terminado / En proceso). Clic → `seleccionarParada`.

**L6 · Detalle de parada:**
- **Siguiente paso** (`guiaParada`): fondo de color, título, detalle, acción principal y alterna.
  - Casos: OC sin validar / bloqueado / listo con piezas / listo sin piezas / encargado ("Enviar al taller" + "Revisar la transferencia antes") / enviado ("Ir al recibo") / recibido.
  - En recibido: "Facturar maquila de TALLER ($)" si hay pendiente; si no, lista de lo que sigue en el lote.
- **Cinco botones** (`subStepOpen`): Orden de compra / Orden de subcontratación / Transferencia / Recibo de subcontratación / **Factura de maquila**.
  - Habilitados en cadena. ✓ según `pasoHecho()`, que depende de la celda abierta. Índigo si `facturaParadaHecha`.
- **oc:**
  - Sin OC: **Crear órdenes de subcontrato**.
  - Con OC: aviso "Valida la OC de TALLER…", `PurchaseDocPanel` (doble validación, enviar, vista previa) y **OM del taller** (`OmTallerView` si origen = general, si no el `OrdenManufacturaForm` legacy).
- **sco:**
  - **Encargos a este taller**: lista con referencia, folio, "N prendas" y estado (recibido ✓ / enviado, falta recibir / por enviar). Clic → `verEntrega`.
  - **+ Otro encargo**: formulario con cantidad y "Todas las piezas / Solo X" (si hay sub-ensamblajes) o referencia; **Encargar** (`confirmarNuevaEntrega` → `parada_registrar_entrega`).
  - **Checklist de sub-ensamblajes** (chips verde/gris).
  - Sin encargo:
    - Título "TÍTULO · TALLER — Lote".
    - Texto con la cantidad del lote y la nota de sub-ensamblajes.
    - Con piezas: "Elige las piezas en la matriz…".
    - Sin piezas: **Encargar a TALLER** (`abrirParada` → `sub_crear_sco` + `sub_validar_sco`).
    - Lote sin cantidad: input de cantidad sugerida por stock (`sugerirPrimeraEtapaQty`), aviso ámbar y **Encargar**.
  - Con encargo:
    - **`EncargoResumen`**: se le manda (material, cantidad, UDM, sale de, disponible/enviado, falta en rojo); el taller entrega (pieza, cantidad, UDM, recibido); se le paga (servicio, cantidad, precio, importe, total sin IVA, nota de la pieza portadora).
    - Tarjeta SCO: nombre, estado, ERPNext; **6 campos**: almacén del taller, almacén destino, dirección del proveedor, contacto, dirección de envío, distribuir costos por.
    - "Costos adicionales (registro anterior)", solo lectura, con su nota.
    - Vista previa, **Guardar**, **Validar** o "Validada · continúa con la transferencia".
- **transfer:**
  - Sin transferencia: texto, `EncargoResumen` y "Al enviar, el recibo queda listo…". La acción vive en "Siguiente paso".
  - Con transferencia:
    - Nombre, estado, ERPNext.
    - **Almacén de origen** por defecto, con "Usar recomendado en todas (X)" y "Aplicar a todas las filas"; **almacén destino**.
    - Tabla agrupada por material (`transAgrupado`): material ("· para N piezas"), **cantidad editable**, almacén de origen por fila, disponible (rojo si no alcanza) o "Quedó en almacén", "Ya en el taller" (ámbar), UOM.
    - Aviso ámbar "Ya se descontó…", texto post-validación, aviso rojo de falta de stock.
    - **Costos adicionales**: descripción, transportista (obligatorio si importe > 0, tooltip de póliza), importe; **+ Costo**; distribuir por.
    - Vista previa, **Guardar**, **Validar** o "Material transferido · continúa con el recibo".
- **recibo:**
  - Sin recibo: **Crear recibo de subcontratación**.
  - Con recibo:
    - Nombre, estado, ERPNext.
    - **Almacén aceptado / rechazado / del taller**.
    - Tabla producto / aceptado / rechazado / UOM (editables).
    - **Costos adicionales obligatorios** (aunque sean $0), con transportista; distribuir por.
    - Vista previa, **Guardar**, **Validar recibo** (`onValidarScr`, recarga `prodComplete`) o "Recibido · producto en inventario".
- **factura:** `FacturaCompraPanel`, con pendiente = `maquila_pendiente` y habilitado si > 0.

### 2.3 Pasos 6 y 7 (fuera de Producción; solo se enlazan)
- **Paso 6 · Enviar** (2578–2718): `ActiveSOSelector`, `ProductionProgressBar` con % de envío, lista de remisiones, "Nueva remisión (otra dirección)", formulario de remisión (lote, prendas, total, direcciones, fecha, transportista y costo con póliza, tabla con almacén y disponible), acciones (Guardar, Validar, Enviar, Descargar, Imprimir, Asignar, ERPNext) y vista previa. **No cambia en este proyecto.**
- **Paso 7 · Facturar**: solo la factura de venta. **No cambia.**
- **Paso 8 · Reportar**: `ReporteFinalPanel`. **No cambia.**

### 2.4 `OmGeneralEditor` (hoy dentro del lote, L3)
- Una tarjeta por producto base: nombre, "· incluye variantes", "N talleres · N prendas", estado Capturada / Sin capturar, Capturar / Editar / Cerrar.
- Editor:
  - Info general: 9 campos + 4 marcas.
  - Tallas heredadas, solo lectura, con total.
  - Procesos, observaciones, tablas de medidas (plantilla o en blanco, columnas y filas) y diagramas o archivos (subir; miniatura o PDF; descripción). Cada uno con "Para" (`ParaTalleres`).
  - **Guardar orden de manufactura**.
- Backend: `costeo_yelke/api/om_general.py` (`get_oms_generales`, `guardar_om_general`, `om_de_oc`). Se imprime en el print format "Orden de Maquila" con el método jinja `om_de_oc` (hooks.py).

### 2.5 Funciones y componentes a REUTILIZAR (no reescribir)
- **Componentes:**
  - `PurchaseDocPanel`, `FacturaCompraPanel`, `EncargoResumen`
  - `OmGeneralEditor`, `OmTallerView`, `ParaTalleres`, `OrdenManufacturaForm` (legacy)
  - `ProductionProgressBar`, `ActiveSOSelector`, `DocStatusPill`, `LinkInput`, `CosteoStepper`
- **Página — lote:** `proveedoresLote`, `rfqDeProveedor`, `sqDeProveedor`, `toggleLoteDoc`, `loteDocOpen`, `loteDocBtnClass`, `marcarCelda`, `abrirCelda`, `celdaRef`, `celdaAbierta`, `pasoHecho`, `cadenaFinal`, `abrirConfeccion`, `guiaParada`, `contadoresRamas`, `celdaClass`, `pasoEstadoTexto`, `pasoEstadoColor`, `paradaBtnClass`, `paradaDotClass`, `paradaEstadoTexto`, `paradaEstadoColor`, `paradaProductosTexto`, `subStepOpen`, `subStepDefaultFor`, `openSubStepSco`, `maybeSugerirPrimeraEtapaQty`, `crearSubcontratosDesdeLote`.
- **Página — almacén:** `aplicarAlmacenOrigenATodos`, `cambiarAlmacenDeMaterial`, `refrescarDisponibleFila`.
- **Página — entrega y facturas:** `crearRemisionLote`, `irARemision`, `abrirFacturaFuente`, `abrirFacturaMaquila`, `crearFacturaInline`, `validarFacturaInline`, `facturaParadaHecha`, `guardarPinv`, `loadCompras`, `selectCompra`, `generarFacturaCompra`, `validarPinv`.
- **Página — navegación:** `triggerHighlight`, `prepararProduccion`, `goStep`.
- **`useProduccion.js`:** todo lo exportado. Plan, solicitud, lotes de entrega, compras, recibos, subcontratos, encargos, transferencias, recibos de maquila, OM, `lotesProduccion`, `loteActivoRef`, `loteParadaActiva`, `seleccionarLote`, `seleccionarParada`, `abrirNuevoLote`, `crearNuevoLote`, `crearOrdenesSeleccion`, `nuevaEntregaForm`, `talleresSaldo`, `devolverMaterialTaller`, `neteoOc`, `transAgrupado`, `prodComplete`, `materiaPrimaPct`, `subcontratacionPct`, `permisosValidacion`.
- **Código muerto detectado:** `components/LoteCard.vue` no se usa en ninguna página. Se borra en la Fase 6.

---

## 3. Hallazgos a corregir ANTES de la UI (Fase 0)

### H1 — `get_lotes_produccion(plan)` no filtra por OV (bug)
- `costeo_api.py` ~6237. Usa el plan solo para obtener el costeo y trae de **todo el costeo**:
  - Solicitudes de material (`Material Request` por `costeo`).
  - OC de material (`lote_ref`).
  - Solicitudes de cotización y cotizaciones de proveedor.
  - OC de maquila (`costeo`, `is_subcontracted=1`).
  - Encargos.
- Con 2 OV, la OV-B muestra lotes y documentos de la OV-A, y el siguiente "Lote N" cuenta los de las dos.
- **Para filtrar:**
  - Solicitudes de material: `Material Request Item.production_plan = plan`.
  - OC de maquila: `Purchase Order Item.production_plan = plan` (lo pone `plan_crear_subcontratacion`, ~9775). Alternativa: `Purchase Order Item.sales_order` (lo usa `produccion_completa` ~2080).
  - OC de material: `Purchase Order Item.material_request` dentro de las solicitudes del plan, o `Purchase Order Item.sales_order` (ver comentario ~5828: el mapeador copia `sales_order`, nunca `production_plan`).
  - Solicitudes de cotización y cotizaciones: por sus ítems `material_request`.
- **Respaldo para datos viejos:** si el costeo tiene **una sola OV**, comportamiento idéntico al actual (sin filtro).
- **No tocar `_lote_paradas`.** Se filtra antes, en las listas que se le pasan.

### H2 — Otros endpoints sin filtro por OV
Revisar y filtrar igual que H1. Todos reciben `costeo`; agregar `sales_order=None` opcional y mandarlo desde el frontend (`activeSOName`):
- `get_facturas_compra(costeo)` (~2877): materiales y maquila.
- `sub_saldo_talleres(costeo)`: el saldo es por almacén de taller. Basta con documentar que es del costeo.
- `get_subcontratos`.
- `get_recibos`.

### H3 — Tallas de la OM por OV
- `om_general.tallas_de_producto` usa cantidades del costeo.
- `om_de_oc(po)` debe tomar la OV de la OC (`Purchase Order Item.sales_order`) y calcular con las cantidades de esa OV, proporcional si es réplica.
- Mismo criterio que `get_reporte_final` (~9814–9840): "si la OV activa tiene otra cantidad (réplica), se recalcula proporcional".
- `get_oms_generales(costeo, sales_order=None)` también: el editor muestra las tallas de la OV activa.

### H4 — Highlight roto de Purchase Invoice
- `triggerHighlight` (~3148) usa `factTab = "compras"`, pestaña que ya no existe en el paso 7.
- En la UI nueva: Purchase Invoice → **Producir · Facturas** con esa factura abierta.
- Agregar también Subcontracting Order, Subcontracting Receipt y Stock Entry → **Lote · Talleres**, en la parada y el paso correctos.

### Prueba de H1–H3 (crear en sandbox, compañía YP)
1. Duplicar un costeo de prueba de YP o usar el de la camisola de YP. **No usar la chamarra 00022**: el usuario la está avanzando a mano.
2. Crear dos OV del mismo costeo con cantidades distintas.
3. Preparar producción en las dos.
4. Abrir "Lote 1" en cada una.
5. Verificar que cada OV ve solo sus lotes, OC, facturas y tallas.
6. Desmontar todo al final (borrado en cascada; patrón en la memoria `costeos-demo-coinsa`).

---

## 4. Nueva estructura

```
Stepper:  Costear · Cotizar · Vender · Alta · Flujo · PRODUCCIÓN · Enviar · Facturar · Reportar
                                                       └ riel: Lote 1 · Lote 2 · +   (se queda igual)

PRODUCCIÓN  (paso 5)
┌───────────────────────────────────────────────────────────────────────┐
│ OV activa: SAL-ORD-2026-00009 ▾        [barra de avance MP / maquila] │  ← fijo arriba
├───────────────────────────────────────────────────────────────────────┤
│ Tablero │ Preparación │ Orden de manufactura │ Envíos (3) │ Facturas (12) │  ← sub-navegación
└───────────────────────────────────────────────────────────────────────┘
     o, con un lote abierto (desde el riel o una tarjeta del Tablero):
┌ ← Producción   Lote 1 · 01/10/2026 · Chamarra 1,440 · XXL-3XL 87 ─────┐
│ Resumen │ Materia prima ✓ │ Flujo │ Talleres 2 │ Entrega               │
└───────────────────────────────────────────────────────────────────────┘
```

**Navegación:**
- **Sub-navegación de Producción** (sin lote abierto): Tablero · Preparación · Orden de manufactura · Envíos · Facturas.
- **Lotes:** se abren desde el riel del stepper (sin cambios) o desde las tarjetas del Tablero. No hay pestaña "Lotes" aparte.
- **Pestañas del lote:** Resumen · Materia prima · Flujo · Talleres · Entrega. El "← Producción" regresa a la sub-vista anterior.

**Indicadores en pestañas:**
- ✓ verde: todo hecho.
- Número: pendientes de esa pestaña.
- ⚠ ámbar: bloqueado o requiere atención.
- Índigo: facturado.

**Pestaña por defecto:**
- Producción: **Tablero**. Si el usuario no tiene ese rol, la primera vista que sí tenga.
- Lote: **Resumen**.
- Si el plan no existe o no está validado, Producción abre en **Preparación**, igual que hoy.

### 4.1 URL (query params, sin tocar el router)
```
?step=5&ov=SAL-ORD-2026-00009&vista=tablero|preparacion|om|envios|facturas
?step=5&ov=…&lote=Lote%201&tab=resumen|materia|flujo|talleres|entrega
        &prov=<supplier>&doc=rfq|sq|oc|recibo|factura          (materia prima: proveedor y documento abiertos)
        &parada=<parada_id>&pieza=<pieza>&paso=oc|sco|transfer|recibo|factura|om   (talleres)
        &filtro_lote=Lote%201                                    (envíos y facturas)
```
- Crear un composable **`useProduccionRuta.js`**: lee y escribe estos parámetros con `router.replace`, sin agregar historial por cada clic. Aplica el estado al montar.
- **`?ov=`** manda sobre la OV por defecto, si pertenece al costeo.
- **`localStorage`:** pasa a `costeo_ultimo_lote_<costeo>_<ov>` y se agrega `costeo_ultima_vista_<costeo>`.
- **Al cambiar de OV:** limpiar `lote`, `tab`, `parada` y `prov`, e ir al Tablero.
- `?highlight=` sigue funcionando. Ver H4 y la tabla en §7.3.

### 4.2 Varios productos
- **Encabezado del lote:** chips por producto con cantidad. Ya existe el texto; se pasa a chips.
- **Filtro de producto** (chips "Todos · Chamarra · XXL-3XL") en **Flujo**, **Talleres** y **Envíos**, solo si el lote tiene más de un producto.
  - Filtra paradas y celdas por `productos[].finished_item` con qty > 0.
  - Las paradas compartidas se ven en cualquier filtro que incluya alguno de sus productos.
- **Materia prima:** sin filtro (es compartida). Cada material muestra "para: Chamarra, XXL" cuando se puede deducir. Si no se puede sin trabajo extra en el backend, se omite: no inventar.
- **OM:** una tarjeta por producto base (ya es así); la variante se incluye.
- **Tablero:** las tarjetas de lote muestran las cantidades por producto.

---

## 5. Especificación por vista

> Formato:
> - **Rol**: el que da acceso a la vista.
> - **Muestra**: incluye la referencia al bloque actual (§2).
> - **Acciones**.
> - **Estados vacíos**.
> - **Indicador**: cómo se calcula el de la pestaña.
>
> Todos los textos de ayuda actuales se conservan.

### 5.1 Producción · **Tablero**
- **Rol:** `Producción Tablero Yelke`. Solo lectura.
- **Muestra:**
  - G1 (selector de OV) y G2 (barra de avance), arriba y comunes a toda la Producción. **Nuevo en G2:** pasar también `envio-pct` (`related.delivery_per_delivered`), que hoy solo se muestra en el paso 6.
  - **PROPUESTA, confirmar con el usuario antes de implementar:** "Enviar al taller" deshabilitado (tooltip "No alcanza el material") cuando algún material del encargo tiene `falta` (`materialesSco`). Hoy el botón se deja pulsar y el backend ajusta a la existencia (`_ajustar_a_existencia`), así que deshabilitarlo podría impedir envíos parciales legítimos. Si el usuario no lo confirma, se deja como hoy (habilitado + aviso rojo). El mockup lo muestra deshabilitado solo como propuesta.
  - Una **tarjeta por lote** (de `lotesProduccion`):
    - Nombre y fecha; productos y cantidades.
    - Mini-barras: **materia prima** (OC del lote recibidas / total de proveedores), **maquila** (paradas recibidas / total), **entregado** (`entrega.producido` vs entregado).
    - Chip de estado: En compras / En maquila / Listo para entregar / Entregado.
    - Clic → abre el lote en Resumen.
  - Tarjeta **"+ Nuevo lote"**: misma acción que el + del riel, `abrirNuevoLote`. Lleva a Preparación §5.2-d.
  - **Por hacer** (máximo 8 renglones, con enlace directo). Se calcula en el frontend a partir de `lotesProduccion`, `compras` y `talleresSaldo`:
    - OC de material sin validar, por proveedor y lote.
    - Recibo de compra pendiente (OC validada sin recibo validado).
    - Celdas o paradas "listas para encargar".
    - Encargos sin enviar (`encargado`).
    - Encargos enviados sin recibir.
    - Maquila por facturar (`maquila_pendiente` > 0 por taller, una vez por taller).
    - Facturas de compra en borrador.
    - Lotes listos para remisión (`entrega.lista`).
    - Sobrante en talleres con la producción terminada.
- **Vacío:** sin plan → tarjeta "Aún no has creado el plan de producción" con el botón **Ir a Preparación**.

### 5.2 Producción · **Preparación**
- **Rol:** `Producción Preparación Yelke`.
- **Muestra, sin omitir nada:**
  - **G3** (resultado de la preparación) y **G4** (estado vacío, botón **Preparar producción**).
  - **G5** (plan): conserva el colapso automático al validarse.
  - **G6** (solicitud de material) y **G7** (lotes de entrega).
  - **G8** ("Continuar a producción").
  - **G9** (nuevo lote), con sus 4 sub-estados:
    - (c) prerrequisito "valida la OC de maquila de cada taller": `PurchaseDocPanel`, más la OM del taller.
    - (d) formulario de cantidades y fecha.
- **Orden vertical:** igual que hoy, G3 → G9.
- **Indicador:** ✓ si plan validado + solicitud validada + todas las OC de maquila validadas. ⚠ si falta algo para abrir el primer lote.

### 5.3 Producción · **Orden de manufactura**
- **Rol:** `Producción Orden de Manufactura Yelke`.
- **Muestra:** `OmGeneralEditor` tal cual, movido desde L3. Cambios:
  - Aviso arriba: *"La ficha (modelo, tela, procesos, archivos) la comparten las N órdenes de venta de este costeo. Las tallas son las de la OV activa."* Solo si hay más de una OV.
  - Las tallas vienen de `get_oms_generales(costeo, sales_order)` (H3).
  - Debajo de cada producto: los talleres que la reciben, como chips de solo lectura (ya hay `talleres`).
  - Botón **"Ver cómo la recibe un taller"**: selector de taller → `OmTallerView` con `om_de_oc(po del taller)`. Sirve para verificar el "Para" antes de imprimir.
- **Indicador:** número de productos sin capturar; ✓ si todos capturados.

### 5.4 Lote · **Resumen**
- **Rol:** visible si el usuario tiene **cualquiera** de: Tablero, Materia Prima, Flujo, Talleres, Entrega, Envíos, Facturas.
- **Muestra:**
  - L0 (encabezado con chips de producto).
  - **Siguiente paso del lote**: una sola tarjeta con el mismo formato que `guiaParada` (título, detalle, acción). Se calcula en este orden y se toma lo primero pendiente:
    1. Materia prima sin OC o con OC sin validar → "Generar/validar OC de PROVEEDOR" → Materia prima.
    2. Recibo de compra pendiente → "Recibir material de PROVEEDOR" → Materia prima (recibo).
    3. Celdas o paradas listas → "Encargar X a TALLER" → Flujo.
    4. Encargo sin enviar → "Enviar material a TALLER" → Talleres (transfer).
    5. Enviado sin recibir → "Confirmar lo que entregó TALLER" → Talleres (recibo).
    6. Lote producido con pendiente por entregar → "Crear remisión del Lote N" → Entrega.
    7. Todo listo → "Lote terminado" + resumen.
  - **Avance por etapa:** fila de chips por `rama_etapas` + `cadenaFinal`, con el estado agregado (recibido / encargado / listo / en espera) y el conteo de piezas. El clic lleva a Talleres con esa parada.
  - **Accesos rápidos:** "Envíos de este lote: N pendientes" → Envíos con `filtro_lote`; "Facturas de este lote: N en borrador" → Facturas con `filtro_lote`; "Material en talleres: N talleres con sobrante" → Envíos.
- **Indicador:** ninguno; es la pestaña por defecto.

### 5.5 Lote · **Materia prima**
- **Rol:** `Producción Materia Prima Yelke`.
- **Muestra:** todo L2, reorganizado:
  - Aviso azul de neteo (`neteoOc`), igual.
  - **Tabla con una fila por proveedor:**
    - Columnas: Proveedor; Materiales (lista compacta "código × cantidad UDM", expandible si son más de 3); **Solicitud de cotización** (chip, solo si existe; si no, en "Más"); **Presupuesto** (igual); **OC** (chip: nombre / "Generar", verde si validada, "· enviado"); **Recibo** (chip); **Factura** (chip índigo / ámbar borrador / gris).
    - Clic en un chip → **panel lateral derecho** (drawer, ~560 px; pantalla completa en celular) con el mismo contenido que hoy: `PurchaseDocPanel` o `FacturaCompraPanel`, con las mismas props.
  - Menú **"Más ▾"** por fila: "Pedir cotización" (`toggleLoteDoc(...,'rfq')`) y "Registrar presupuesto del proveedor" (`'sq'`), para no perder estas dos acciones.
- **Reglas de los chips:** las mismas que los botones actuales, incluidos los deshabilitados con tooltip ("Primero valida el recibo de compra").
- **El drawer usa `loteDocOpen`** (proveedor + documento). Cerrarlo limpia `loteDocOpen`. Cambiar de pestaña lo cierra.
- **Factura:** si el usuario no tiene el rol Facturas, el chip se ve con su estado pero el panel abre en **solo lectura** (sin Crear/Guardar/Validar) con el texto "La captura la hace Facturas".
- **Recibo:** acción permitida a Materia Prima **o** Envíos (§6).
- **Indicador:** número de proveedores con algo pendiente (sin OC validada o sin recibo validado); ✓ si todos recibidos.

### 5.6 Lote · **Flujo**
- **Rol:** `Producción Flujo Yelke`.
- **Muestra:** todo L4:
  - Matriz, contadores, "Listas (N)" / "Quitar", celdas con todos sus estados.
  - Barra de selección con **Crear orden / Crear N órdenes**.
  - Cadena final con sus botones.
  - Versión sin piezas (`tracksLote`).
- **Cambio de comportamiento:** el clic en una celda **no** lista o el botón "Ver encargo" de la cadena **navega a Talleres** con `parada`, `pieza` y `paso` (usa `abrirCelda`; abre el paso que corresponde según `subStepDefaultFor`/estado). Ya no despliega el detalle debajo.
- **"Encargar confección"** (`abrirConfeccion` con estado listo) crea el encargo desde aquí, como hoy, y deja al usuario en Talleres con esa parada.
- Filtro de producto (§4.2).
- **Indicador:** número de celdas o tarjetas "listas para encargar".

### 5.7 Lote · **Talleres** (subcontratación)
- **Rol:** `Producción Talleres Yelke`.
- **Lista** (izquierda o arriba): una fila por **parada** (`loteActivo.paradas`, ordenadas por nivel y orden).
  - Columnas: orden, título, taller, productos (`paradaProductosTexto`), piezas (de `piezasDeParada`), $ por prenda.
  - **Chips de pasos:** OC ✓ / Encargo ✓ (N encargos) / Envío ✓ / Recibo ✓ / Factura (índigo si facturado, `$ pendiente` si `maquila_pendiente` > 0 y recibido).
  - Ejemplo de fila: "1 · Servicio De Corte +1 · ALEJANDRO TORRES AGUILERA · 9 piezas · $9.00/prenda".
- **Detalle** (derecha o abajo) de la parada seleccionada; lo mismo que hoy en L6:
  - **Siguiente paso** (`guiaParada`), con las mismas acciones.
  - **Sub-pestañas:** **Orden de compra · OM del taller · Encargos · Envío · Recibo · Factura**.
    - **Orden de compra:** `PurchaseDocPanel` de la OC del taller.
    - **OM del taller:** `OmTallerView`, o `OrdenManufacturaForm` legacy si `origen != general`. Se separa del panel de la OC para que no quede escondida.
    - **Encargos:** lista de encargos, + Otro encargo, checklist de sub-ensamblajes, `EncargoResumen`, tarjeta SCO con sus 6 campos, costos anteriores, Guardar/Validar; estados vacíos (con o sin piezas, sin cantidad).
    - **Envío:** todo el bloque de transferencia (almacenes, tabla agrupada, avisos, costos con transportista, Guardar/Validar).
    - **Recibo:** todo el bloque de recibo (3 almacenes, aceptado/rechazado, costos obligatorios, Validar recibo).
    - **Factura:** `FacturaCompraPanel` de maquila. En solo lectura si no tiene el rol Facturas.
  - Si se llega con `pieza` desde Flujo: la celda abierta (`celdaRef`) manda sobre los ✓ y la guía, como hoy (`pasoHecho`).
  - Aviso: la parada es compartida entre piezas (cuello y puños con el mismo taller). Mostrar "Viendo: Cuello" con selector de las piezas de esa parada (`piezasDeParada`) para cambiar de celda.
- **L7** (lote sin paradas): estado vacío con **Crear órdenes de subcontrato**.
- Filtro de producto (§4.2).
- **Indicador:** número de paradas con acción pendiente (encargo sin enviar o enviado sin recibir).

### 5.8 Lote · **Entrega**
- **Rol:** `Producción Entrega Yelke`.
- **Muestra:** todo L5:
  - Tabla producto / producido / ya en remisión / por entregar.
  - Chips de remisiones → paso 6.
  - Botón con 3 estados → `crearRemisionLote`, que salta al paso 6 como hoy.
- **Agregar:** almacén donde quedaron las prendas (`entrega.productos[item].almacen`, ya viene del backend; hoy no se muestra).
- **Indicador:** ✓ si todo entregado; número de prendas por entregar si `lista`.

### 5.9 Producción · **Envíos** (almacén)
- **Rol:** `Producción Envíos Yelke`.
- **Filtro:** lote (Todos / Lote 1 / Lote 2…, por defecto Todos o `filtro_lote`) y producto.
- **Secciones**, en este orden; cada fila con lote, taller o proveedor, documento, cantidades y acción:
  1. **Por recibir de proveedores (entradas):** OC de material validadas sin recibo validado. Acción **Recibir** → drawer con `PurchaseDocPanel` del recibo (el mismo de Materia prima, con costo de envío obligatorio).
  2. **Por enviar a talleres (salidas):** encargos validados sin transferencia validada. Muestra lo que se le manda (`EncargoResumen`, sección "Se le manda al taller", con "No alcanza" en rojo). Acciones **Enviar al taller** (`enviarMaterialTaller`) y **Revisar transferencia** (drawer con el bloque de transferencia completo).
  3. **Enviado, por recibir del taller (regresos):** transferencia validada sin recibo de maquila validado. Acción **Recibir del taller** → drawer con el bloque de recibo completo.
  4. **Material en talleres (sobrantes):** L1 completo, con avisos y **Registrar devolución**.
  5. **Historial** (colapsado): movimientos ya validados (recibos de compra, transferencias y recibos de maquila) con fecha y enlace.
- **Datos:**
  - Todo sale de `lotesProduccion` (`material_pos`, `paradas[].entregas[]` con `transfer_done`/`receipt_validated`) y `talleresSaldo`.
  - **No crear endpoint nuevo** salvo que falte la fecha del movimiento. Si falta, agregar `fecha` a `entregas[]` y `receipt` en `get_lotes_produccion`, sin tocar `_lote_paradas`; si vive dentro de `_lote_paradas`, preguntar.
  - El drawer reutiliza `selectSco`/`loadTrans`/`loadScr` (cargan **un** documento a la vez; al abrir otro se reemplaza).
- **Indicador:** número total de filas en las secciones 1–3.

### 5.10 Producción · **Facturas** (de compra)
- **Rol:** `Producción Facturas Yelke`.
- **Filtro:** lote (afecta a materiales; la maquila muestra "cubre Lote 1, Lote 2"), tipo (Material / Maquila) y estado (Sin factura / Borrador / Validada).
- **Tablas:**
  - **Material** (`compras.materiales`): proveedor, recibo de compra, **lote** (de la OC; se agrega `lote_ref` en `get_facturas_compra`), subtotal (`base_net_total`), factura (nombre / borrador / validada índigo), acción.
  - **Maquila** (`compras.maquila`): taller, OC, total de la OC, **lotes que cubre**, **pendiente por facturar** (`pendiente_facturar`), facturas (lista `invoices`), acción.
- **Acción:** clic → drawer con `FacturaCompraPanel`, con las mismas props que hoy: folio, fecha, vencimiento, condiciones, subtotal/total, Guardar/Validar, descargar/imprimir/ampliar/ERPNext, vista previa y aviso "trabajo recibido sin facturar".
- **Totales al pie:** subtotal facturado, en borrador y por facturar.
- **Datos:** `get_facturas_compra(costeo, sales_order)` (H2) más `lote_ref` por fila de material y `lotes` por OC de maquila.
- **Indicador:** número en borrador + sin factura con recibo validado.

---

## 6. Roles por vista

### 6.1 Roles nuevos
Se agregan en `costeo_yelke/roles.py` como **`ROLES_VISTA_PRODUCCION`**, que pasa a ser la única fuente de los nombres.

| Clave de vista | Rol | Descripción |
|---|---|---|
| `tablero` | Producción Tablero Yelke | Ve el tablero de producción de la OV (solo lectura). |
| `preparacion` | Producción Preparación Yelke | Prepara producción: plan, solicitud de material, lotes de entrega, OC de maquila y apertura de lotes. |
| `om` | Producción Orden de Manufactura Yelke | Captura la orden de manufactura general por producto. |
| `materia` | Producción Materia Prima Yelke | Compra la materia prima de cada lote: cotizaciones, OC y recibo. |
| `flujo` | Producción Flujo Yelke | Ve la matriz del lote y crea los encargos a talleres. |
| `talleres` | Producción Talleres Yelke | Lleva cada taller: encargos, envío de material, recibo del trabajo. |
| `envios` | Producción Envíos Yelke | Almacén: recibe material, envía a talleres, recibe de talleres, devoluciones. |
| `facturas` | Producción Facturas Yelke | Captura y valida las facturas de compra (material y maquila). |
| `entrega` | Producción Entrega Yelke | Crea la remisión de cada lote terminado. |

**Pase libre** (ven y hacen todo): `System Manager`, `Director Yelke` y `Supervisor Yelke`.

**El Resumen del lote** no tiene rol propio: se ve con cualquiera de los anteriores.

### 6.2 Backend
- **En `roles.py`:**
  - `VISTAS_PRODUCCION = {clave: rol}`.
  - `vistas_produccion(user=None) -> list[str]`: claves permitidas; todas si tiene pase libre.
  - `requiere_vista(*claves)`: lanza `frappe.PermissionError` con mensaje en español si el usuario no tiene **ninguna** de las claves. Ejemplo: "Necesitas el rol Producción Talleres Yelke para esto".
- **`get_permisos_validacion_yelke`** (~1812) agrega `"vistas": vistas_produccion()`. El frontend ya lo carga en `loadPermisosValidacion`.
- **Patch `v0_2_47/roles_vistas_produccion.py`:**
  1. Crea los 9 roles (`desk_access=1`), con el mismo patrón que `v0_2_21`.
  2. **Para no dejar a nadie fuera al desplegar**, asigna los 9 roles a todo usuario habilitado de tipo System User (excluyendo Administrator y Guest). El usuario después quita los que no correspondan.
  3. Agregarlo a `patches.txt`.
- **Guardas en endpoints que escriben:** solo al inicio de la función. Las lecturas no se restringen en esta fase.

| Clave(s) | Endpoints |
|---|---|
| `preparacion` | `preparar_produccion`, `guardar_plan`, `plan_obtener_materias_primas`, `plan_crear_solicitud_material`, `guardar_solicitud_material`, `mr_dividir_en_lotes_por_piezas`, `plan_crear_ordenes_trabajo`, `plan_crear_subcontratacion`, `lote_abrir`, `guardar_om` (OM legacy del prerrequisito) |
| `om` | `om_general.guardar_om_general` |
| `materia` | `mr_crear_rfq`, `mr_crear_presupuesto_proveedor`, `mr_generar_oc_lote`, `mr_crear_oc`, `oc_jalar_precios`, `guardar_documento_compra` (si el doctype es RFQ, SQ o PO de material) |
| `materia` o `envios` | `crear_recibo_oc`, `guardar_documento_compra` (si el doctype es Purchase Receipt) |
| `flujo` o `talleres` | `parada_registrar_entrega` |
| `talleres` | `sub_crear_sco`, `sub_guardar_sco`, `sub_validar_sco` |
| `talleres` o `envios` | `sub_transferir_material`, `sub_enviar_material`, `sub_guardar_transferencia`, `sub_validar_transferencia`, `sub_crear_recibo`, `sub_guardar_recibo` |
| `envios` o `talleres` | `sub_devolver_material` |
| `facturas` | `crear_factura_compra`, `actualizar_factura_compra` |
| `entrega` | `crear_remision` **solo cuando trae `lote_ref`**. Sin `lote_ref` es el paso 6, que no se restringe |

- **`validar_documento` / `marcar_revisado_documento`** (genéricos) exigen la vista según el doctype:

| Doctype | Vista requerida |
|---|---|
| Production Plan, Material Request | `preparacion` |
| Purchase Order con `is_subcontracted=0` | `materia` |
| Purchase Order con `is_subcontracted=1` | `preparacion` o `talleres` |
| Purchase Receipt | `materia` o `envios` |
| Subcontracting Order | `talleres` |
| Stock Entry de subcontratación | `talleres` o `envios` |
| Subcontracting Receipt | `talleres` o `envios` |
| Purchase Invoice | `facturas` |
| Costeo, Quotation, Sales Order, Delivery Note, Sales Invoice | Sin cambio |

  **Se suma** a la doble validación existente (Revisor/Aprobador), no la reemplaza.
- **Ojo con las acciones encadenadas:**
  - `abrirNuevoLote` llama a `plan_crear_subcontratacion` + `marcar_revisado_documento` + `validar_documento` (PO subcontratada): con `preparacion` basta.
  - `validarDocCompra` llama a `crear_recibo_oc` después de validar la OC: con `materia` basta, porque `crear_recibo_oc` acepta `materia`.

### 6.3 Frontend
- `permisosValidacion.vistas` (array).
- Helper `puedeVer(clave)`. `tieneAlgunaVista` para el Resumen.
- **Sub-navegación y pestañas:** solo se muestran las vistas permitidas.
- **Acceso por URL a una vista sin permiso:** pantalla "No tienes acceso a esta vista" con el nombre del rol que falta y botón a la primera vista permitida.
- **Acciones que viven en una vista pero requieren otro rol:** por ejemplo, Factura dentro de Materia prima o de Talleres. Se muestran en **solo lectura** con una nota.
- **Riel de lotes del stepper:** visible si tiene alguna vista de lote.
- **Paso 5 completo:** oculto si el usuario no tiene ninguna vista de Producción.
- **El backend es la autoridad;** el frontend solo evita botones que van a fallar.

### 6.4 Relación con los roles de proceso existentes
- `roles.py` ya tiene `ROLES_PROCESO`: Comprador, Almacenista, Coordinador de Maquila, Planeador, Embarques, Facturador… **Hoy no controlan nada.**
- **No se borran ni se reutilizan.** Las vistas usan sus roles nuevos, como pidió el usuario.
- Documentar en el manual (sección 10) la equivalencia sugerida para asignar:

| Rol de proceso | Roles de vista sugeridos |
|---|---|
| Planeador | Preparación + Flujo + OM |
| Comprador | Materia Prima |
| Almacenista | Envíos |
| Coordinador de Maquila | Talleres + Flujo |
| Embarques | Entrega |
| Facturador | Facturas |
| Director | Todo |

---

## 7. Fases y tareas

> Cada fase termina con:
> - `vite build` sin errores.
> - Recorrido manual en sandbox (§8).
> - Foto de regresión: comparar `get_lotes_produccion`, `get_facturas_compra` y `get_oms_generales` antes y después para todos los costeos de YP, ignorando el orden.
>
> Sin commits salvo que el usuario lo pida. Al terminar cada fase, avisar al usuario con un resumen corto.

### Fase 0 — Backend: OV y tallas (H1–H4)
1. `get_lotes_produccion`: filtro por plan, con respaldo de OV única (H1).
2. `get_facturas_compra(costeo, sales_order=None)`: filtro + `lote_ref` en materiales + `lotes` en maquila (H2, §5.10).
3. `get_oms_generales(costeo, sales_order=None)` y `om_de_oc`: tallas por OV (H3).
4. Frontend mínimo: mandar `activeSOName` a esos endpoints (`loadCompras`, `OmGeneralEditor`).
5. Prueba con 2 OV (§3). Desmontar.
- **Criterio de aceptación:** con dos OV, cada una ve solo lo suyo. Con una OV, la foto es idéntica a la de antes.

### Fase 1 — Roles (backend + frontend mínimo)
1. `roles.py` (§6.1–6.2), patch `v0_2_47`, `get_permisos_validacion_yelke` con `vistas`.
2. Guardas en los endpoints de la tabla §6.2.
3. Prueba:
   - Usuario de prueba de YP con solo `Producción Envíos Yelke` (crearlo con contraseña de prueba guardada en un fixture o script de la carpeta del proyecto; no repetirla en el chat).
   - Debe poder transferir y recibir del taller; no puede crear una OC de material (PermissionError con mensaje en español).
   - Con todos los roles, el flujo sigue igual.
- **Criterio de aceptación:** ningún usuario actual pierde acceso tras el patch.

### Fase 2 — Esqueleto de navegación (sin cambiar contenido)
1. Crear `frontend/src/components/produccion/`:
   - `ProduccionShell.vue`: OV, barra de avance, sub-navegación con indicadores, `<slot>`. Si hay lote abierto, el encabezado del lote con pestañas.
   - `ProduccionNav.vue`: pestañas genéricas con indicador `{clave, etiqueta, badge, estado}`.
   - `DrawerPanel.vue`: panel lateral reutilizable (título, cerrar, slot; Esc cierra; ancho completo en celular).
2. `composables/useProduccionRuta.js` (§4.1).
3. Mover cada bloque actual **tal cual** a su vista, como componentes que reciben el estado por props/provide:

   | Componente | Contenido |
   |---|---|
   | `ProduccionTablero.vue` | Nuevo, §5.1 |
   | `ProduccionPreparacion.vue` | G3–G9 |
   | `ProduccionOm.vue` | `OmGeneralEditor` |
   | `ProduccionEnvios.vue` | §5.9; en esta fase puede empezar solo con L1 y las secciones 2–3 |
   | `ProduccionFacturas.vue` | §5.10 |
   | `LoteResumen.vue` | Nuevo |
   | `LoteMateriaPrima.vue` | L2 |
   | `LoteFlujo.vue` | L4 |
   | `LoteTalleres.vue` | L6 + L7 |
   | `LoteEntrega.vue` | L5 |

   - **Estado compartido:** usar `provide('produccion', {...})` desde la página con el objeto de `useProduccion` más las funciones de página listadas en §2.5, para no pasar 80 props.
   - Las funciones que hoy viven en la página y se usan solo en una vista **se pueden mover** a esa vista o a un composable `useLoteVista.js`. Sin cambiar su lógica.
4. `CosteoDetailPage.vue`: el bloque `activeStep === 5` queda como `<ProduccionShell>` con la vista activa. Debe bajar ~1,100 líneas.
5. `triggerHighlight`: actualizar a vistas y pestañas (tabla §7.3).
- **Criterio de aceptación:** recorrer la chamarra (Lote 1 completo, Lote 2 en curso) y la camisola de YP; todo lo de la §9 aparece y funciona; recargar la página conserva la vista.

### Fase 3 — Lote: Resumen, Materia prima (tabla + drawer), Flujo
- `LoteResumen` con siguiente paso del lote, avance y accesos (§5.4).
- `LoteMateriaPrima` como tabla con chips + drawer + menú "Más" (§5.5).
- `LoteFlujo` con navegación a Talleres en vez de despliegue (§5.6).

### Fase 4 — Talleres
- Lista de paradas con chips + detalle con sub-pestañas, incluida la OM del taller separada (§5.7).
- Selector de pieza dentro de una parada compartida.

### Fase 5 — Envíos, Facturas, Entrega y Tablero completo
- §5.9, §5.10, §5.8 y la lista "Por hacer" del Tablero (§5.1).
- Indicadores de todas las pestañas.

### Fase 6 — Pulido
- Filtro de producto (§4.2), celular (drawer a pantalla completa, tablas con `overflow-x-auto`), borrar `LoteCard.vue`.
- Actualizar el manual (`erp.yelke.com.mx/manual-costeo`; ver la memoria `manual-costeo-yelke-artifact`): sección de Producción y sección 10 de roles.

### 7.3 Tabla de highlight (`?highlight=&doctype=`)

| Doctype | Destino |
|---|---|
| Purchase Order de material | Lote · Materia prima, drawer de la OC de ese proveedor |
| Purchase Order de maquila | Lote · Talleres, parada de esa OC, sub-pestaña Orden de compra (el lote es el primero que la usa) |
| Purchase Receipt | Lote · Materia prima, drawer del recibo |
| Material Request | Producción · Preparación |
| Subcontracting Order | Lote del encargo (`lote_ref`) · Talleres · parada · Encargos con ese encargo |
| Stock Entry (envío a subcontratista) | Lote · Talleres · Envío |
| Subcontracting Receipt | Lote · Talleres · Recibo |
| Purchase Invoice | Producción · Facturas, drawer de esa factura |
| Delivery Note | Paso 6 (sin cambio) |

---

## 8. Escenarios de prueba (cada fase)

1. **Chamarra `CST-FERROCARRIL-MEXI-2026-00022`** (OV `SAL-ORD-2026-00009`, plan `MFG-PP-2026-00010`). **Solo lectura**; el usuario la avanza a mano.
   - **Lote 1** (1,440 + 87 XXL-3XL): todo recibido y entregado (`MAT-DN-2026-00008`); 6 facturas de material en borrador (`ACC-PINV-2026-00011…16`); maquila sin facturar ($18,330 / $21,378 / $22,905 / $16,797 / $95,196 / $10,689).
   - **Lote 2** (1,440 + 88): corte encargado (`SC-ORD-2026-00102`), sin OC de material; las demás celdas en espera.
   - **Talleres:** ALEJANDRO TORRES (corte, 9 piezas, $9/prenda), Serigrafía Creativa CDMX, MANUEL LEMUS (2 paradas: frente izq. y manga der.), ALFREDO ORTEGA (reflejante, 2 encargos en Lote 1), JESUS MOLINA (confección, arma la prenda), MAQUILA SUR (acabado, terminal).
   - **Sobrantes:** ALFREDO 0.92 m de reflejante; ALEJANDRO 0.551 m de gabardina y 0.448 m de forro.
2. **Costeo sin piezas declaradas:** vista de carriles (`tracksLote`). Buscar uno en YP o crear un duplicado y desmontarlo.
3. **Costeo con 2 OV** (Fase 0).
4. **Usuario con un solo rol** (Fase 1).
5. **Celular:** ancho de 400 px en el panel de navegador (`resize_window` mobile).

---

## 9. Matriz de trazabilidad (que no se pierda nada)
Al terminar la Fase 5, recorrer esta lista y marcar cada elemento en su nuevo lugar.

| Elemento actual | Nuevo lugar |
|---|---|
| G1 selector OV | Shell (todas las vistas de Producción) |
| G2 barra de avance | Shell |
| G3 resultado de la preparación | Preparación |
| G4 estado vacío + Preparar producción | Preparación (y aviso en el Tablero) |
| G5 plan completo (almacén, OV, total, cantidades +5%, materias primas, Obtener / Guardar / Validar, Orden de trabajo) | Preparación |
| G6 solicitud de material completa (fecha, tabla ±5%, proveedor, textos, Guardar / Validar) | Preparación |
| G7 lotes de entrega (nombre, fecha, piezas, materiales estimados, pendiente, repartir) | Preparación |
| G8 Continuar a producción | Preparación |
| G9 nuevo lote (4 sub-estados, OC de taller + OM, formulario) | Preparación (+ "Nuevo lote" en el Tablero y el + del riel) |
| Riel de lotes del stepper | Sin cambio |
| L0 encabezado del lote | Encabezado del lote (chips) |
| L1 material en talleres + devolución | Envíos §4 (+ acceso en el Resumen) |
| L2 neteo | Materia prima |
| L2 grupos por proveedor + 5 documentos + paneles | Materia prima (tabla + drawer + Más) |
| L3 OM general | Orden de manufactura |
| L4 matriz, contadores, Listas / Quitar, selección, Crear órdenes, cadena final, carriles sin piezas | Flujo |
| L5 entrega del lote | Entrega |
| L6 siguiente paso | Talleres (detalle) + Resumen (versión de lote) |
| L6 OC del taller + OM del taller | Talleres · Orden de compra / OM del taller |
| L6 encargos, + Otro encargo, sub-ensamblajes, estados vacíos, cantidad sugerida | Talleres · Encargos |
| L6 `EncargoResumen` + tarjeta SCO (6 campos) + costos anteriores + Guardar / Validar | Talleres · Encargos |
| L6 transferencia completa | Talleres · Envío (+ Envíos §2 en drawer) |
| L6 recibo de maquila completo | Talleres · Recibo (+ Envíos §3 en drawer) |
| L6 factura de maquila | Talleres · Factura (solo lectura sin rol) + Facturas |
| Factura de material | Materia prima (chip / drawer) + Facturas |
| Recibo de compra | Materia prima (chip / drawer) + Envíos §1 |
| L7 sin paradas | Talleres (estado vacío) |
| Highlight por doctype | §7.3 |
| `localStorage` último lote | Por costeo + OV, + última vista |

---

## 10. Riesgos y cómo evitarlos
- **Estado único en `useProduccion`:** `subPo`, `scoSel`, `docCompra`, `reciboPr`, `transDoc`, `scr` y `pinvDoc` son de un documento a la vez.
  - El drawer y las sub-pestañas muestran un documento a la vez.
  - Al cambiar de vista o de pestaña, cerrar el drawer y limpiar `loteDocOpen` y `celdaRef`.
- **Watchers de la página:**
  - `watch(loteActivoRef)` limpia `celdaRef`.
  - `watch(lote::parada)` fija `subStepOpen`.
  - `watch(celdaAbierta.scos[0])` sigue al encargo.

  Al mover código a componentes, **mover también el watcher** o dejarlo en la página. Probar el caso "cuello vs puños, mismo taller" (memoria `flujo-por-pieza-probado`).
- **El paso 6 depende de `crearRemisionLote`** (`activeStep = 6` + `selectDn`): mantener.
- **`abrirNuevoLote`** se dispara desde 3 lugares (riel +, Continuar, Tablero): un solo punto que además cambie `vista=preparacion`.
- **Rendimiento:** no recargar `get_lotes_produccion` al cambiar de pestaña; solo después de acciones, como hoy.
- **Despliegue a producción** (cuando el usuario lo pida; memoria `deploy-produccion-qnap`):
  1. Fase 0 (backend, corrige bugs).
  2. Fase 1 (roles: avisar al usuario que el patch asigna todos los roles a todos y que luego hay que quitarlos).
  3. Fases 2–6 juntas o por partes.

---

## 11. Al iniciar la siguiente sesión
1. Leer este plan y abrir los mockups `docs/mockups/produccion.html`.
2. `git log --oneline -3`: debe aparecer `27f5b59` o posteriores.
3. Revisar la memoria: `plan-ui-produccion`, `om-general-por-producto`, `punto-de-ensamble`, `flujo-por-pieza-probado`, `materia-prima-por-lote-editable-oc`, `roles-y-flujos-aprobacion`.
4. Empezar por la **Fase 0** y avisar al usuario al cerrar cada fase.
