# Plan — Producción por pantallas, pasos y roles (diseño v2)

> **Para la siguiente sesión:** este documento es la fuente de verdad. Léelo completo antes de tocar código.
>
> - **Mockup v2 (el que vale):** [`docs/mockups/produccion.html`](mockups/produccion.html). Ábrelo en el navegador: es interactivo, con datos reales de la chamarra.
>   - Se navega con el menú izquierdo, el stepper del lote y la barra de abajo.
>   - Abre los paneles laterales con clic en las filas.
>   - **Copia su HTML y sus clases**: es el sistema de diseño.
> - Rama: `fix/listo-produccion`. Base: commit `27f5b59` (todo lo anterior ya commiteado).
> - Fecha del plan: 2026-10-06. Diseño v2 pedido por el usuario el mismo día: "app moderna y minimalista, paso a paso, acciones y siguiente siempre en el mismo lugar".
> - Estado: **aprobado; sin código todavía.**

---

## 0. Decisiones ya tomadas por el usuario (no volver a preguntar)

| # | Decisión | Respuesta |
|---|---|---|
| 1 | La orden de manufactura (OM) sale del lote y sube a Producción; la comparten las OV del costeo y las tallas se calculan por OV | **Sí** |
| 2 | Commit de lo pendiente antes de empezar | **Hecho** (`27f5b59`) |
| 3 | Vistas propias de **Envíos** y de **Facturas** | **Sí** (a nivel Producción, como "bandejas", con filtro por lote) |
| 4 | **Un rol por cada vista** ("pestaña padre"). Quien necesite dos vistas recibe los dos roles | **Sí** |
| 5 | Mantener todo lo que hoy se muestra. **No omitir ningún dato ni acción** | Regla dura; ver §9 |
| 6 | **Diseño v2:** app moderna, minimalista, todo paso a paso; los botones de acción y de "siguiente" siempre en el mismo lugar | **Sí**, ver §4 y el mockup |

### Por qué Envíos y Facturas viven a nivel Producción y no dentro del lote
Verificado con datos reales:
- **La factura de maquila es por taller, no por lote.** Se factura contra la OC del taller, que cubre todos sus lotes.
  - `maquila_pendiente` es el mismo número en Lote 1 y Lote 2. Ejemplo: corte = $18,330 en ambos.
  - Dentro del lote se vería duplicado.
- **El sobrante es por almacén del taller** (`sub_saldo_talleres(costeo)`).
- **Almacén trabaja por lo que hay que mover hoy**, sin importar el lote.

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
- **Código muerto detectado:** `components/LoteCard.vue` no se usa en ninguna página. Se borra en la Fase 7.

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

## 4. Diseño v2: estructura y sistema de diseño

### 4.1 Principios (obligatorios; revisar cada pantalla contra esto)
1. **Paso a paso.** Todo lo que tiene orden se muestra como **stepper**, siempre el mismo componente:
   - la Preparación (3 pasos);
   - el lote (4 pasos);
   - cada taller (4 pasos);
   - cada documento de compra (OC → Recibo → Factura).

   El paso actual va en naranja con halo; los hechos, verde con ✓; los facturados, índigo; los bloqueados, rojo.
2. **Las acciones viven en un solo lugar:**
   - En la página, en la **barra de acciones fija abajo**.
   - En un panel lateral, en el **pie del panel**: misma altura y misma disposición que la barra de abajo.
   - **No hay botones de acción principales dentro de tarjetas ni tablas.** Única excepción: acciones por fila que no avanzan el flujo, como "Registrar devolución".
3. **El botón de la derecha siempre avanza.**
   - Si el paso tiene algo pendiente, es esa acción ("Validar factura", "Enviar al taller").
   - Si ya terminó, es **"Siguiente: <paso> →"**.
   - A su izquierda, las secundarias ("Guardar", "Revisar transferencia", "Generar las 6").
   - A la izquierda de la barra, **"← <anterior>"** y una línea de estado con su punto de color, que explica por qué el botón está como está.
4. **Listas que solo muestran el estado; el detalle se abre en un panel lateral** (drawer, 560 px; pantalla completa en celular) para documentos sueltos, o en una sub-pantalla para trabajo de varios pasos (un taller).
5. **Minimalismo:**
   - Fondo `surface`, tarjetas blancas con borde de 1 px.
   - Puntos de estado de 8 px en vez de bloques de color.
   - El naranja de marca solo para lo principal (botón principal, paso actual, conteos urgentes).
   - Textos de ayuda en una línea gris (`lede`/`meta`).
   - Lo avanzado o poco usado va colapsado (`<details>`) o en "⋯".
6. **Mismo vocabulario de estado en todas partes:**

   | Color | Significado |
   |---|---|
   | Verde | Hecho |
   | Índigo | Facturado |
   | Ámbar | Pendiente o borrador |
   | Naranja | Lo que sigue |
   | Rojo | Bloqueado o falta |
   | Gris | En espera |

7. **Nada se pierde:** todo dato o acción actual tiene lugar (§9). Lo que no cabe a la vista va en `<details>`, en "⋯" o en el panel.

### 4.2 Estructura de pantalla (Producción, paso 5 del costeo)
```
┌ encabezado de la app ─────────────────────────────────────────────────────┐
├ stepper del costeo (sin cambios): Costear · … · PRODUCCIÓN · Enviar · …  ┤
├──────────────┬────────────────────────────────────────────────────────────┤
│ MENÚ (248px) │  eyebrow  · título · una línea de ayuda                    │
│ [OV activa ▾]│  [stepper de la vista, si aplica]                         │
│ Tablero      │                                                            │
│ PREPARAR     │  contenido (listas, tablas, formularios)                   │
│ ● Preparación│                                                            │
│ ● OM         │                                                            │
│ LOTES        │                                                            │
│ ● Lote 1     │                                                            │
│ ● Lote 2     │                                                            │
│ + Nuevo lote │                                                            │
│ BANDEJAS     ├────────────────────────────────────────────────────────────┤
│ Envíos   (1) │ ← Anterior   ● estado en una línea     [secundaria] [PRIMARIA →] │ ← barra fija
│ Facturas(12) │                                                            │
└──────────────┴────────────────────────────────────────────────────────────┘
```

**Menú izquierdo** (`ProduccionMenu.vue`). Reemplaza la sub-navegación, el `ActiveSOSelector` de este paso y el riel de lotes del stepper. Contiene:
- **Tarjeta "Orden de venta"** arriba: nombre, cantidades por producto, número de lotes y ⌄ para cambiar. Es el `ActiveSOSelector` rediseñado; en los pasos 6–8 se queda como está hoy.
- **Tablero.**
- **Preparar:** Preparación (n/3) · Orden de manufactura (n capturadas / total).
- **Lotes:** uno por renglón, con su punto de estado y a la derecha el paso actual ("1 · Materia prima" o "entregado"); **+ Nuevo lote** abre un panel lateral.
- **Bandejas:** Envíos y Facturas, con conteo naranja de pendientes.
- Solo muestra lo que el rol permite (§6).
- **Celular** (<1024 px): el menú se vuelve un `<select>` arriba del contenido.
- **El riel de lotes del stepper del costeo (`CosteoStepper`) se quita**, porque ahora vive en el menú. El paso "Producción" del stepper sigue igual.

**Barra de acciones** (`BarraAcciones.vue`, sticky abajo del área principal, 64 px):
- **Izquierda:** botón fantasma "← <anterior>". Se oculta si no hay anterior.
- **Centro:** punto de color + una línea de estado (truncada; oculta en celular).
- **Derecha:** 0–2 secundarias + 1 primaria.
- **La configuración la da cada vista** con un computed `barra = { atras:{texto, ir}, estado:{color, texto}, acciones:[{texto, tipo, deshabilitado, motivo, accion}] }`. Ver la tabla §4.6.

**Panel lateral** (`PanelLateral.vue`):
- **Encabezado:** eyebrow, título, meta, pill de estado, "⋯" (acciones raras) y ✕.
- **Stepper opcional** del documento.
- **Cuerpo** con scroll.
- **Pie de 64 px:** a la izquierda, enlaces (Vista previa, Descargar, Imprimir, ERPNext ↗); a la derecha, secundaria + primaria.
- Esc o clic fuera lo cierra. Uno a la vez.
- **Adentro va el contenido actual de `PurchaseDocPanel` / `FacturaCompraPanel`, sin sus botones:** los botones se suben al pie del panel. Agregar a esos componentes una prop `sinAcciones` y exponer sus acciones con eventos. No duplicar lógica.

### 4.3 Componentes nuevos (todos en `frontend/src/components/produccion/`)

| Componente | Qué es |
|---|---|
| `ProduccionLayout.vue` | Menú + área principal + barra de acciones; slot por vista |
| `ProduccionMenu.vue` | §4.2 |
| `BarraAcciones.vue` | §4.2 |
| `PanelLateral.vue` | §4.2 |
| `Pasos.vue` | Stepper genérico: `pasos=[{clave, texto, estado: hecho/facturado/actual/bloqueado/espera}]`, `seleccionado`, `navegable` (emite `ir`). Modo compacto (solo números) para filas de lista |
| `FilaLista.vue` | Punto de estado · título + meta · slot derecho (pasos compactos o pills) · chevron. Clic = abrir |
| `Segmentado.vue` | Control segmentado (filtros de lote o producto, secciones de bandejas) |
| `EstadoPunto.vue` / `Pill.vue` | Vocabulario de §4.1.6 |
| `VacioEstado.vue` | Icono gris + título + una línea |

Las clases base están en el `<style>` del mockup:
- `.panel`, `.row`, `.eyebrow`, `.h1`, `.lede`, `.meta`, `.btn-*`, `.seg`, `.pill-*`, `.dot-*`, `.step*`, `.field`, `.ro`, `.tbl`.
- Pasarlas a `style.css` dentro de `@layer components` **con prefijo `p-`** (`.p-panel`, `.p-row`…) para no chocar con `.field-input` y las demás clases existentes.

### 4.4 Mapa de vistas

| Vista (clave URL) | Dónde en el menú | Stepper | Rol (§6) |
|---|---|---|---|
| `tablero` | Tablero | — | Tablero |
| `preparacion` | Preparar · Preparación | Plan · Materia prima · Órdenes a talleres | Preparación |
| `om` | Preparar · Orden de manufactura | — (sub-menú de secciones) | OM |
| `lote` + `paso=materia` | Lotes · Lote N | **1 Materia prima** · 2 Flujo · 3 Talleres · 4 Entrega | Materia Prima |
| `lote` + `paso=flujo` | 〃 | 1 · **2 Flujo** · 3 · 4 | Flujo |
| `lote` + `paso=talleres` | 〃 | 1 · 2 · **3 Talleres** · 4 | Talleres |
| `lote` + `paso=talleres` + `parada=` | 〃 (sub-pantalla) | Encargo · Envío · Recibo · Factura | Talleres |
| `lote` + `paso=entrega` | 〃 | 1 · 2 · 3 · **4 Entrega** | Entrega |
| `envios` | Bandejas · Envíos | — (segmentado) | Envíos |
| `facturas` | Bandejas · Facturas | — (segmentado) | Facturas |

**Ya no hay pestaña "Resumen" del lote.** Sus piezas se repartieron:
- El "siguiente paso del lote" lo dice la barra de acciones.
- El avance lo da el stepper del lote.
- Los accesos a Envíos y Facturas están en el menú con sus conteos.
- El panorama de todos los lotes está en el Tablero.

**Al abrir un lote** se cae en su **paso actual** (el primero no terminado).

### 4.5 URL (query params, sin tocar el router)
```
?step=5&ov=SAL-ORD-2026-00009&vista=tablero|preparacion|om|envios|facturas|lote
   &prep=1|2|3                                   (preparación)
   &lote=Lote%202&paso=materia|flujo|talleres|entrega
   &parada=<parada_id>&pieza=<pieza>&tpaso=encargo|envio|recibo|factura   (taller)
   &panel=<tipo>:<nombre>                         (panel lateral abierto, p. ej. oc:PUR-ORD-2026-00246)
   &filtro_lote=Lote%201&seg=salidas              (bandejas)
```
- Composable `useProduccionRuta.js`: lee y escribe con `router.replace`.
- `?ov=` manda si pertenece al costeo.
- `localStorage`: `costeo_ultima_vista_<costeo>_<ov>`.
- Al cambiar de OV: ir al Tablero y limpiar lote, paso, parada y panel.
- `?highlight=` según §7.3.

### 4.6 Barra de acciones por vista (estados; textos exactos)
La primaria siempre a la derecha. "→" solo cuando navega.

| Vista / estado | ← Anterior | Estado (punto) | Secundarias | Primaria |
|---|---|---|---|---|
| Tablero | — | primer pendiente de "Por hacer" (su color) | — | "Ir a <primer pendiente> →" |
| Preparación · Plan sin validar | Tablero | ámbar "Plan en borrador" | Obtener materias primas · Guardar | Validar plan |
| Preparación · Plan validado | Tablero | verde | Orden de trabajo (si se usa) | Siguiente: Materia prima → |
| Preparación · Solicitud sin crear | Plan | ámbar | — | Crear solicitud de material |
| Preparación · Solicitud en borrador | Plan | ámbar o rojo si `mrLotesInvalidos` (texto del aviso actual) | Guardar | "Validar solicitud" o "Validar y dividir en N lotes" (deshabilitada si lotes inválidos) |
| Preparación · Solicitud validada | Plan | verde | — | Siguiente: Órdenes a talleres → |
| Preparación · Sin OC de taller | Materia prima | ámbar | — | Crear órdenes a talleres |
| Preparación · OC de taller sin validar | Materia prima | ámbar "Faltan N por validar" | — | Abrir la siguiente → (panel) |
| Preparación · Todo listo, sin lotes | Materia prima | verde | — | Abrir primer lote → (panel Nuevo lote) |
| Preparación · Todo listo, con lotes | Materia prima | verde | — | Siguiente: Orden de manufactura → |
| OM | Preparación | ámbar "Cambios sin guardar" / verde "Guardada" | Ver cómo la recibe un taller | Guardar · o Siguiente: Lote N → si ya está guardada |
| Lote · Materia prima | Tablero | "N proveedores sin orden" / "N por recibir" / "N facturas en borrador" | Generar las N (si hay más de 1 sin OC) | la acción del primer proveedor pendiente (abre su panel) · o Siguiente: Flujo → |
| Lote · Flujo, sin selección | Materia prima | "N listas para encargar" / "Nada listo: esperan a X" | — | Siguiente: Talleres → |
| Lote · Flujo, con selección | Materia prima | "N piezas en M talleres" | Limpiar | Crear M órdenes |
| Lote · Flujo, confección lista | Materia prima | verde "Todas las piezas listas" | — | Encargar confección |
| Lote · Talleres (lista) | Flujo | lo del primer taller pendiente | — | Abrir <taller pendiente> → |
| Taller · Encargo (sin encargo) | Talleres | — | — | Encargar a <taller> · o, con piezas: "Elige las piezas en Flujo →" |
| Taller · Encargo (borrador) | Talleres | ámbar | Guardar | Validar encargo |
| Taller · Envío | Talleres | rojo "No alcanza X" / naranja | Revisar transferencia | Enviar al taller (deshabilitado con motivo si falta, **ver decisión pendiente §10**) |
| Taller · Envío, transferencia en borrador | Talleres | ámbar | Guardar | Validar envío |
| Taller · Recibo | Talleres | ámbar "Costos adicionales obligatorios" si faltan | Guardar | Validar recibo |
| Taller · Factura | Talleres | "Por facturar $X" | Guardar | Crear factura / Validar factura |
| Taller · Todo hecho | Talleres | verde | — | Siguiente taller → · o Siguiente: Entrega → si era el último |
| Lote · Entrega | Talleres | "Esperando fin de producción" / "N prendas por entregar" / verde "Todo en remisión" | Ver remisión (si existe) | Crear remisión del Lote N (deshabilitada si no está lista) · o Siguiente: Lote N+1 → |
| Envíos | Tablero | "N salidas, M entradas…" | — | Atender el primero → |
| Facturas | Tablero | "N pendientes" | — | Capturar la siguiente → (abre panel) |
| Panel · OC material | (pie) Vista previa · ERPNext | — | Jalar precios · Guardar | Enviar a revisión / Revisar / Validar (según la doble validación y `permisosValidacion`) |
| Panel · Recibo de compra | (pie) | — | Guardar | Validar recibo (exige costo de envío) |
| Panel · Factura | (pie) Descargar · Imprimir · ERPNext | — | Guardar | Validar factura · o Crear factura |
| Panel · Nuevo lote | — | — | Cancelar | Abrir lote |

### 4.7 Varios productos
- **Filtro de producto** (`Segmentado`: Todos · Producto A · Producto B) a la derecha del título del lote. Solo aparece si el lote tiene más de un producto con cantidad > 0.
- Afecta a **Flujo**, **Talleres** y **Entrega**. Materia prima no (es compartida).
- **Menú y Tablero:** cantidades por producto en la meta ("Chamarra 1,440 · XXL-3XL 88").
- **OM:** una tarjeta por producto base, como hoy.

---

## 5. Especificación por vista
> Cada vista indica:
> - **Contenido**, con referencia al bloque actual (§2). Todos los textos de ayuda actuales se conservan, en `lede`/`meta` o en `<details>`.
> - **Estado vacío.**
> - **Detalle de la barra** (§4.6).

### 5.1 Tablero
- **Encabezado:** "Producción" / "Tablero" / "Todo lo de esta orden de venta…".
- **Tres indicadores** (rejilla de 3, separadores de 1 px): materia prima recibida (`materiaPrimaPct`), maquila recibida (`subcontratacionPct` + "N de M encargos" de `prodComplete`), entregado (`related.delivery_per_delivered`, hoy solo visible en el paso 6). Reemplazan a `ProductionProgressBar` en este paso.
- **Lotes:** `FilaLista` por lote. Punto de estado, "Lote N · fecha", cantidades por producto, `Pasos` compacto (4) y pill del paso actual. Clic: abre el lote en su paso actual.
- **Por hacer:** hasta 8 `FilaLista`, cada una con destino exacto (vista, lote, paso, parada, panel). Se calculan en el frontend:
  - Proveedores sin OC o con OC sin validar.
  - Recibos pendientes.
  - Celdas listas para encargar.
  - Encargos sin enviar (marcados en rojo si `materialesSco` tiene `falta`).
  - Enviados sin recibir.
  - Facturas en borrador.
  - Maquila por facturar (una por taller).
  - Lotes listos para remisión.
  - Sobrantes con la producción terminada.
- **Vacío** (sin plan): `VacioEstado` "Aún no has creado el plan de producción" + primaria "Ir a Preparación →".

### 5.2 Preparación (stepper de 3 pasos; navegable)
- **Paso 1 · Plan:** G4 (vacío con "Preparar producción", que va a la primaria), G3 (resultado de la preparación, solo después de prepararla) y G5 completo.
  - Datos de G5: almacén editable, OV, total, cantidad a producir (+5% con borde rojo), materias primas a comprar, producción interna (Orden de trabajo).
  - **Los botones de G5 se van a la barra:** Obtener materias primas · Guardar · Validar plan.
  - Validado: tarjeta compacta con todo en solo lectura.
- **Paso 2 · Materia prima:**
  - **G6** (solicitud completa: fecha editable, tabla con ±5% y proveedor editable, textos "±5%" y "UDM y precio en la OC").
  - **G7** (lotes de entrega, el editor completo mientras no se valide; validada, tarjetas compactas por lote).
  - Botones de G6 y G7 a la barra: Crear solicitud · Guardar · Validar / Validar y dividir en N lotes.
  - Las acciones de edición de G7 ("+ Lote", quitar, "Repartir en partes iguales") se quedan dentro del editor: son edición, no avance.
- **Paso 3 · Órdenes a talleres:**
  - Lista de OC de maquila (`FilaLista`): taller, OC, total, estado.
  - Clic → panel lateral con la OC (`PurchaseDocPanel` sin botones; doble validación, enviar, vista previa) y, debajo, **la OM que recibe ese taller** (`OmTallerView`, o `OrdenManufacturaForm` legacy si no hay OM general).
  - Sin OC: primaria "Crear órdenes a talleres" (`crearSubcontratos` + revisar/validar, igual que `crearSubcontratosDesdeLote`).
- **G8 "Continuar a producción"** desaparece como tarjeta: es la primaria del paso 3 ("Abrir primer lote →").
- **Panel "Nuevo lote"** (G9-d): cantidades por producto con "pendiente N" o "Valida antes la 1ª OC de este producto", fecha, avisos de stock y "Revisando materia prima…".
  - Pie: Cancelar · **Abrir lote**.
  - Se abre desde el menú (+ Nuevo lote), desde la primaria de Preparación y desde el Tablero.
  - G9-a (cargando) se muestra dentro del panel.
  - G9-b y G9-c (faltan OC de taller) **mandan a Preparación · paso 3** con un mensaje, en vez de duplicar esa pantalla.

### 5.3 Orden de manufactura
- Encabezado + una tarjeta por producto base (nombre, "incluye variantes", "N talleres · N prendas en esta OV", pill Capturada / Sin capturar).
- **Editor dentro de la tarjeta, con sub-menú de secciones a la izquierda** (General · Tallas · Procesos · Observaciones · Tablas de medidas · Diagramas); el clic hace scroll a la sección.
  - Los 9 campos y las 4 marcas van como pills seleccionables.
  - Tallas en solo lectura, como fichas.
  - Procesos, observaciones, tablas (plantilla o en blanco, columnas y filas) y diagramas (subir, miniatura, descripción), cada uno con "Para" (`ParaTalleres`).
- Aviso azul si hay más de una OV: "La ficha la comparten las N órdenes de venta; las tallas son las de la OV activa".
- **"Ver cómo la recibe un taller"** (secundaria): panel con `OmTallerView` del taller elegido.
- **Guardar** es la primaria de la barra; hoy el botón está dentro del editor.

### 5.4 Lote · encabezado común
- eyebrow "Producción · Lotes", título "Lote N", meta "fecha · cantidades por producto".
- Filtro de producto a la derecha (§4.7).
- **Stepper navegable** de 4 pasos con su estado:
  - **Materia prima:** hecho si todas las OC del lote tienen recibo validado.
  - **Flujo:** hecho si no quedan celdas ni tarjetas sin encargar.
  - **Talleres:** hecho si todas las paradas tienen recibo validado. Índigo si además todo está facturado.
  - **Entrega:** hecho si `entrega.pendiente == 0` y `producido > 0`.
- **El paso "actual" (naranja)** es el primero no hecho. El "seleccionado" es el que se ve.

### 5.5 Lote · 1 Materia prima
- Una línea de ayuda.
- **Aviso azul de neteo** (`neteoOc`), una línea por material, con su texto.
- **Lista de proveedores** (`proveedoresLote`), cada uno en una `FilaLista`:
  - Punto de estado.
  - Proveedor.
  - Meta con materiales ("Gabardina naranja · 2,871.55 m"; si son varios, separados con "·").
  - A la derecha, mini-camino "Orden de compra › Recibo › Factura" con el actual en pill.
- **Clic → panel lateral** del proveedor:
  - **Stepper:** OC · Recibo · Factura. Navegable a pasos hechos o actuales.
  - **Cuerpo:** `PurchaseDocPanel` de la OC (proveedor y UDM editables, Jalar precios, ayuda de la OC, doble validación, vista previa) / del recibo (almacén, costo de envío obligatorio, texto de IVA) / `FacturaCompraPanel`.
  - **Menú "⋯":** "Pedir cotización" (solicitud de cotización) y "Registrar presupuesto del proveedor" (`toggleLoteDoc` 'rfq' / 'sq'). Si ya existen, se ven como enlaces en la meta del panel.
  - **Sin el rol Facturas**, el paso Factura se ve en solo lectura y el pie dice "La captura la hace Facturas".
- La lógica de abrir y crear es la de `toggleLoteDoc` (crea el documento si no existe). La primaria de la barra = la acción del primer proveedor pendiente. Secundaria "Generar las N" (crea todas las OC de los proveedores sin OC, en secuencia con `generarOcLote`).

### 5.6 Lote · 2 Flujo
- Una línea de ayuda y pills de contadores (`contadoresRamas`).
- **Matriz** dentro de un panel con `overflow-x-auto`.
  - **Columnas:** número, título, taller, "$ por prenda" y botón "Listas (N)" / "Quitar".
  - **Filas:** pieza, "N pzas" o "×N · total".
  - **Celdas:**

    | Estado | Cómo se ve |
    |---|---|
    | No aplica | "—" |
    | Lista | Casilla |
    | Encargada / enviada | Fondo naranja suave con punto |
    | Recibida | Verde |
    | Facturada | Índigo |
    | En espera | Borde punteado |

  - **Al marcar celdas** la barra cambia a "Limpiar" + "Crear M órdenes" (`crearOrdenesSeleccion`). Muestra "N piezas en M talleres" en el estado.
  - El detalle por taller de la selección actual (`gruposSel`: "taller · etapa · piezas") va en la línea de estado o en un popover sobre la barra.
- **"Después de las piezas"** (`cadenaFinal`): `FilaLista` estáticas con número, título, "arma la prenda", taller, barra "N de M piezas listas" o "recibe la prenda armada de X", y pill de estado.
  - El botón de la tarjeta de hoy se vuelve la primaria de la barra cuando su estado es "listo" ("Encargar confección").
  - En los demás estados, clic en la fila → taller.
- **Clic en una celda o fila no lista** → sub-pantalla del taller con esa pieza (`abrirCelda`).
- **Sin piezas** (`tracksLote`): carriles por producto con tarjetas de parada y el producto terminado al final (imagen, nombre, cantidad, Terminado / En proceso). Clic → taller.

### 5.7 Lote · 3 Talleres
- **Lista** de paradas (`FilaLista`):
  - Número de orden, título, meta "taller · N piezas · N prendas".
  - `Pasos` compacto (Encargo, Envío, Recibo, Factura).
  - Pill del estado actual ("Falta material" rojo / "Por enviar" / "Por recibir" / "Por facturar $X" / "Facturado" / "En espera").
- **Sub-pantalla de un taller** (clic en la fila):
  - eyebrow "Lote N · Talleres · i de N", título "<Etapa> · <TALLER>", meta "piezas · prendas · servicios $ por prenda".
  - A la derecha, botones secundarios **Orden de compra** y **Orden de manufactura** (abren panel).
  - **"Viendo"** (segmentado): Todas las piezas / cada pieza de la parada (`piezasDeParada`). Cambia la celda abierta (`celdaRef`), igual que hoy.
  - **Stepper:** Encargo · Envío · Recibo · Factura, con estado según `pasoHecho()`. Navegable.
  - **Encargo:**
    - Lista de encargos (referencia, folio, prendas, estado) y "+ Otro encargo" (formulario actual) como enlace.
    - Chips de sub-ensamblajes.
    - `EncargoResumen`.
    - Los 6 campos del encargo, colapsados en `<details>` "Datos del encargo".
    - "Costos adicionales (registro anterior)" en `<details>`.
    - Estados vacíos actuales: con piezas → "Elige las piezas en Flujo" con enlace; sin piezas → primaria "Encargar a X"; sin cantidad → campo de cantidad sugerida + aviso.
  - **Envío:**
    - Tarjeta "Se le manda al taller" (origen → destino, tabla material / a enviar / UDM / disponible, rojo si falta) + aviso de pie.
    - `<details>` "Detalle de la transferencia" con TODO lo actual: origen por defecto + "Usar recomendado en todas" + "Aplicar a todas las filas", destino, tabla agrupada editable con almacén por fila y "Ya en el taller", avisos ámbar y rojo, costos adicionales con transportista y "distribuir por".
    - Si ya hay transferencia en borrador, el `<details>` arranca abierto.
  - **Recibo:** almacenes aceptado / rechazado / del taller, tabla aceptado / rechazado / UOM, costos adicionales obligatorios con transportista y "distribuir por". Todo visible: es el paso de captura.
  - **Factura:** `FacturaCompraPanel` sin botones; pendiente = `maquila_pendiente`.
  - Lo que hoy dice `guiaParada` (título y detalle) va en la línea de estado de la barra, y su acción en la primaria; la "alterna" va como secundaria.

### 5.8 Lote · 4 Entrega
- **Tabla:** Producto · Almacén (`entrega.productos[item].almacen`; hoy no se muestra) · Producido · En remisión · Por entregar.
- **"Remisiones"** como pills con enlace al paso 6.
- **Vacío:** `VacioEstado` "Todavía no hay prendas terminadas · faltan N talleres".
- **Lote entregado:** tarjeta de éxito arriba ("Lote terminado y entregado · N prendas · remisión X validada").
- **Primaria:** "Crear remisión del Lote N (X prendas)" (`crearRemisionLote`, lleva al paso 6 como hoy) / deshabilitada "Esperando fin de producción" / "Siguiente: Lote N+1 →".

### 5.9 Envíos (bandeja)
- **Segmentado de secciones**, cada una con su conteo:
  - **Entradas:** OC de material validadas sin recibo validado → panel de recibo.
  - **Salidas:** encargos validados sin transferencia validada → sub-pantalla del taller en el paso Envío.
  - **Regresos:** transferidos sin recibo de maquila → taller, paso Recibo.
  - **Sobrantes:** L1 completo: avisos y "Registrar devolución" por taller.
  - **Historial:** movimientos validados con lote, documento, taller o proveedor y enlace.
- **Segmentado de lote:** Todos / Lote N.
- **Al entrar**, se elige la primera sección con pendientes.
- **Datos:** `lotesProduccion` + `talleresSaldo`. Para el Historial, agregar la fecha del documento en `get_lotes_produccion` **sin tocar `_lote_paradas`**; si la fecha vive ahí, preguntar.

### 5.10 Facturas (bandeja)
- **Tres indicadores:** Por facturar (maquila recibida) · En borrador · Validadas, con importes.
- **Segmentados:** Pendientes / Validadas / Todas · Todo / Material / Maquila · filtro de lote.
- **Una sola lista ordenada por importe** (`FilaLista`):
  - Material: "Proveedor · Material · Lote N · recibo X".
  - Maquila: "Taller · Maquila · servicio · Lotes 1 y 2 · OC".
  - Importe y pill (Borrador / Sin factura / Validada índigo).
- **Clic → panel** con `FacturaCompraPanel`:
  - Stepper OC ✓ · Recibo ✓ · Factura (material).
  - Aviso "trabajo recibido sin facturar" (maquila).
  - Pie: Descargar · Imprimir · ERPNext ↗ | Guardar · Validar factura (o Crear factura).
- **Datos:** `get_facturas_compra(costeo, sales_order)` + `lote_ref` (material) + `lotes` (maquila) (Fase 0).

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

**Ya no existe un "Resumen" del lote** (diseño v2, §4.4). Un lote aparece en el menú si el usuario tiene al menos una de las 4 vistas de lote.

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
- `permisosValidacion.vistas` (array) → helper `puedeVer(clave)`.
- **Menú izquierdo:**
  - Solo muestra las vistas permitidas.
  - Los lotes aparecen si el usuario tiene **alguna** vista de lote (materia, flujo, talleres, entrega).
  - **Al abrir un lote, el stepper muestra los 4 pasos**, pero los no permitidos se ven con candado y no son navegables.
  - El lote se abre en el primer paso permitido que esté pendiente.
- **Acceso por URL a una vista sin permiso:** `VacioEstado` "No tienes acceso a <vista>" con el rol que falta; primaria "Ir a <primera vista permitida> →".
- **Pasos que pertenecen a otra vista** (Factura dentro de Materia prima o de un taller; Recibo de compra para quien solo tiene Envíos, etc.): se ven en **solo lectura** y la barra o el pie dicen "La captura la hace <vista>" sin botones.
- **Paso 5 del stepper del costeo:** oculto si el usuario no tiene ninguna vista de Producción.
- **El backend es la autoridad.**

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
> - Recorrido en sandbox (§8) **comparando contra el mockup**.
> - Foto de regresión de `get_lotes_produccion`, `get_facturas_compra` y `get_oms_generales` (todos los costeos de YP, sin importar el orden).
> - Aviso corto al usuario.
>
> Sin commits salvo que el usuario lo pida.

### Fase 0 — Backend: OV y tallas (H1–H4)
1. `get_lotes_produccion`: filtro por plan, con respaldo de OV única (H1).
2. `get_facturas_compra(costeo, sales_order=None)`: filtro + `lote_ref` (material) + `lotes` (maquila) (H2).
3. `get_oms_generales(costeo, sales_order=None)` y `om_de_oc`: tallas por OV (H3).
4. Frontend mínimo: mandar `activeSOName` a esos endpoints.
5. Prueba con 2 OV (§3) y desmontarla.
- **Criterio de aceptación:** con dos OV, cada una ve solo lo suyo; con una OV, la foto es idéntica.

### Fase 1 — Roles
1. `roles.py` (§6.1–6.2), patch `v0_2_47`, `get_permisos_validacion_yelke` con `vistas`.
2. Guardas en los endpoints (§6.2).
3. Prueba con un usuario de YP que tenga solo Envíos. Crearlo con contraseña de prueba guardada en un script del proyecto; no repetirla en el chat.
- **Criterio de aceptación:** nadie pierde acceso tras el patch; el usuario de un solo rol queda limitado y ve mensajes en español.

### Fase 2 — Sistema de diseño y armazón
1. Clases `p-*` en `style.css` (§4.3), copiadas del mockup.
2. Componentes base: `Pasos`, `FilaLista`, `Segmentado`, `EstadoPunto`, `Pill`, `VacioEstado`, `PanelLateral`, `BarraAcciones`.
3. `ProduccionLayout` + `ProduccionMenu` + `useProduccionRuta`.
4. `CosteoDetailPage.vue`: el paso 5 pasa a ser `<ProduccionLayout>`; se quita el riel de lotes de `CosteoStepper` (emit `select-lote`/`create-lote` ya no se usa en el paso 5).
5. **Estado compartido:** `provide('produccion', {...})` desde la página con el objeto de `useProduccion` más las funciones de página de §2.5. Ver el riesgo de los watchers en §10.
6. En esta fase cada vista puede montar **los bloques actuales tal cual** dentro del layout nuevo, para que todo siga funcionando mientras se rediseñan una por una.
- **Criterio de aceptación:** la navegación (menú, URL, cambio de OV, abrir lote en su paso actual) funciona y todo lo de hoy sigue accesible.

### Fase 3 — Preparación, OM y Nuevo lote
- §5.2 y §5.3, el panel "Nuevo lote" y la barra por estado (§4.6).
- `PurchaseDocPanel` y `FacturaCompraPanel` con la prop `sinAcciones` + eventos, para que sus botones vivan en el pie del panel.

### Fase 4 — Lote: Materia prima, Flujo, Entrega
- §5.4–§5.6 y §5.8.

### Fase 5 — Talleres
- §5.7: lista + sub-pantalla con stepper, "Viendo", y los `<details>` de transferencia y encargo.

### Fase 6 — Bandejas y Tablero
- §5.9, §5.10, §5.1 ("Por hacer" con destinos exactos) y los conteos del menú.

### Fase 7 — Pulido
- Celular: menú como `<select>`, panel a pantalla completa, tablas con scroll.
- Teclado: Esc cierra el panel; foco visible.
- Borrar código muerto (`LoteCard.vue`, la sub-navegación vieja, el riel de lotes del stepper y los bloques ya migrados de `CosteoDetailPage.vue`).
- Actualizar el manual (`erp.yelke.com.mx/manual-costeo`): Producción y roles.

### 7.3 Tabla de highlight (`?highlight=&doctype=`)

| Doctype | Destino |
|---|---|
| Purchase Order de material | Lote · Materia prima + panel del proveedor en el paso OC |
| Purchase Order de maquila | Preparación · paso 3 + panel de esa OC |
| Purchase Receipt | Lote · Materia prima + panel del proveedor en el paso Recibo |
| Material Request | Preparación · paso 2 |
| Subcontracting Order | Lote (`lote_ref`) · Talleres · sub-pantalla de la parada · paso Encargo con ese encargo |
| Stock Entry (envío a subcontratista) | 〃 · paso Envío |
| Subcontracting Receipt | 〃 · paso Recibo |
| Purchase Invoice | Facturas + panel de esa factura |
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
Al terminar la Fase 6, recorrer esta lista y marcar cada elemento en su nuevo lugar.

| Elemento actual | Nuevo lugar |
|---|---|
| G1 selector de OV | Tarjeta "Orden de venta" del menú |
| G2 barra de avance | Tablero (3 indicadores; se suma el % de entregado) |
| G3 resultado de la preparación | Preparación · paso 1 |
| G4 estado vacío + Preparar producción | Preparación · paso 1 (primaria) + vacío del Tablero |
| G5 plan (almacén, OV, total, cantidades +5%, materias primas, Obtener / Guardar / Validar, Orden de trabajo) | Preparación · paso 1 (botones en la barra) |
| G6 solicitud (fecha, tabla ±5%, proveedor, textos, Crear / Guardar / Validar) | Preparación · paso 2 (botones en la barra) |
| G7 lotes de entrega (editor completo, materiales estimados, pendiente, repartir, avisos) | Preparación · paso 2 |
| G8 Continuar a producción | Primaria de Preparación · paso 3 ("Abrir primer lote →") |
| G9-a cargando | Panel Nuevo lote |
| G9-b/c faltan OC de taller (OC + OM del taller) | Preparación · paso 3 (lista + panel con OC y OM) |
| G9-d cantidades, fecha y avisos | Panel Nuevo lote |
| Riel de lotes del stepper + "+" | Menú · Lotes + "Nuevo lote" |
| L0 encabezado del lote | Encabezado común del lote (§5.4) |
| L1 material en talleres + devolución | Envíos · Sobrantes (+ "Por hacer" del Tablero) |
| L2 neteo | Lote · Materia prima (aviso azul) |
| L2 grupos por proveedor + Solicitud de cotización / Presupuesto / OC / Recibo / Factura + paneles | Lote · Materia prima (lista + panel con stepper; cotización y presupuesto en "⋯") |
| L3 OM general | Orden de manufactura |
| L4 matriz completa, contadores, Listas / Quitar, selección, Crear órdenes | Lote · Flujo (crear en la barra) |
| L4 cadena final con sus estados y botón | Lote · Flujo, "Después de las piezas" (botón en la barra) |
| L4 carriles sin piezas + producto terminado | Lote · Flujo (variante sin piezas) |
| L5 entrega del lote | Lote · Entrega (+ columna Almacén) |
| L6 siguiente paso (`guiaParada`) | Barra de acciones de la sub-pantalla del taller |
| L6 OC del taller + OM del taller | Botones "Orden de compra" / "Orden de manufactura" del taller (panel) |
| L6 encargos, + Otro encargo, sub-ensamblajes, `EncargoResumen`, 6 campos, costos anteriores, estados vacíos, cantidad sugerida | Taller · Encargo |
| L6 transferencia completa | Taller · Envío (tarjeta + `<details>`) |
| L6 recibo de maquila completo | Taller · Recibo |
| L6 factura de maquila | Taller · Factura + bandeja Facturas |
| L7 lote sin paradas | Preparación · paso 3 / vacío de Talleres con enlace |
| Factura de material | Panel del proveedor · paso Factura + bandeja Facturas |
| Recibo de compra | Panel del proveedor · paso Recibo + Envíos · Entradas |
| Highlight por doctype | §7.3 |
| `localStorage` último lote | Última vista por costeo + OV |

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
- **`abrirNuevoLote`** se dispara desde 3 lugares (menú "+ Nuevo lote", primaria de Preparación · paso 3, Tablero). Un solo punto que abre el panel "Nuevo lote". Si faltan OC de taller (G9-b/c), manda a Preparación · paso 3.
- **Botones movidos a la barra o al pie del panel:** la lógica sigue en las mismas funciones (`guardarPlan`, `validarSolicitud`, `validarDocCompra`, etc.). Solo cambia dónde está el botón. No duplicar handlers.
- **Rendimiento:** no recargar `get_lotes_produccion` al cambiar de pestaña; solo después de acciones, como hoy.
- **Despliegue a producción** (cuando el usuario lo pida; memoria `deploy-produccion-qnap`):
  1. Fase 0 (backend, corrige bugs).
  2. Fase 1 (roles: avisar al usuario que el patch asigna todos los roles a todos y que luego hay que quitarlos).
  3. Fases 2–6 juntas o por partes.

---

## 11. Al iniciar la siguiente sesión
1. Leer este plan completo y abrir el mockup v2 `docs/mockups/produccion.html` en el navegador (panel de navegador: `file://` o arrastrar el archivo). Recorrer todas las vistas y abrir los paneles laterales.
2. `git log --oneline -3`: debe aparecer el commit del plan v2 (posterior a `27f5b59`).
3. Revisar la memoria: `plan-ui-produccion`, `om-general-por-producto`, `punto-de-ensamble`, `flujo-por-pieza-probado`, `materia-prima-por-lote-editable-oc`, `roles-y-flujos-aprobacion`.
4. Empezar por la **Fase 0** y avisar al usuario al cerrar cada fase.
