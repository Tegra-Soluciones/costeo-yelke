# Plan — Panel de Dirección, aprobaciones y línea de tiempo

> Estado: **APROBADO** (2026-10-19). El usuario aceptó las recomendaciones D1, D2, D4, D5 y D6, **amplió D3** con Cotización, Orden de Venta y Factura de compra, y **metió D7 (delegación) al alcance**: "es muy importante y debe ser fácil de hacer". Bench arreglado y cambios de seguridad commiteados (`da6adc2`). Sigue la Fase 0 (mockup).
> Referencias: `docs/plan-ui-produccion.md` (sistema de diseño `p-*`), `docs/mockups/produccion.html`.

## Estado de ejecución (2026-10-19)

| Fase | Estado | Verificación |
|---|---|---|
| 0 · Mockup | ✅ aprobado | `docs/mockups/direccion.html` |
| 1 · Motor de aprobación | ✅ | `prueba_aprobaciones.py` **58/58**, en una transacción revertida. Regresión `e2e.py` **20/20**. |
| 2 · Notificaciones | ✅ | Campana + correo (el sandbox no tiene cuenta saliente: el correo se probó interceptando `sendmail`). Recordatorio diario. |
| 3 · Actividad y comentarios | ✅ | Cotización, OV, OC, factura de venta, costeo y paneles de Producción (OC de material, OC a taller, factura de compra). |
| 4 · Panel de Dirección | ✅ | Recorrido en Chrome con 4 usuarios de prueba, 0 errores de página. |
| 5 · Proyectos y resumen | ✅ | Datos reales: los proyectos 00027 y 00028 salen como atrasados. |
| 6 · Celular | ✅ | 390×844 sin scroll horizontal. Escritorio 1440. |
| 7 · Delegación | ✅ | Incluida en las 58 pruebas: activa, programada, terminada, cruzada, a uno mismo y "en nombre de". |
| 8 · Cierre | ⏳ | Falta el manual, la Matriz de Alcance, el deploy y **asignar los roles en producción** (el usuario dice quién lleva cada rol). |

**Cambios respecto al plan, ya hechos:**
- **Campana:** el contador se refresca cada 30 s y al volver a la pestaña, sin socket. El SPA no tiene cliente de socket.io y meterlo detrás del nginx de producción no valía el riesgo.
- **Producción:** las OC a taller las **envía a aprobación** quien no puede aprobar. El lote se abre cuando Dirección las aprueba (`useProduccion.validarOcsTallerPendientes`).
- **Paneles de Producción:** la actividad va como sección plegable al final del panel, no como un segundo panel encima.

**Pendiente para producción (Fase 8):**
- El perfil **CEO** debe llevar `Director Yelke`, `Aprobador de Documentos Yelke` y `Aprobador de Precios Yelke`, y además **`Enviar Documentos`**, que es lo que da lectura sobre `Costeo` en producción. Sin este último, "Abrir el documento completo" de un costeo le marcaría "sin permiso".
- **Sin estos roles asignados, nadie podrá validar Cotización, OV, OC ni Factura de compra** (fuera de System Manager). Desplegar y asignar roles tiene que ir **en el mismo momento**.

## 0. Qué se pidió

1. Una pantalla **solo para el CEO**: aprobaciones pendientes primero. Aprobar o **regresar a corregir** rápido y ver bien cada documento. Además, el **progreso de los proyectos** y una **vista general**.
2. **Que funcione en el celular.** Se diseña primero para celular y luego se adapta a escritorio.
3. Conectada a las **notificaciones** del CEO.
4. Los **revisores** (el paso intermedio) tienen un acceso más limitado: solo su **lista de pendientes**.
5. Al **regresar** un documento, el empleado **recibe un aviso** y sabe qué corregir. El comentario es **obligatorio**.
6. **Comentarios y línea de tiempo**, como los de ERPNext, en **todos los documentos** de la app.

---

## 1. Lo que hay hoy (revisado en el código y en sandbox.local)

| Tema | Estado real |
|---|---|
| Documentos con aprobación | Solo **Costeo** (Simple: rol `Aprobador de Documentos Yelke`) y **Orden de Compra**, de materia prima o de maquila (Doble: `Revisor de Documentos Yelke` → `Aprobador de Documentos Yelke`), en `costeo_api.validar_documento` / `marcar_revisado_documento` y en `purchase_order_api`. Los **precios acordados** se validan aparte con el rol legado `CEO` (`item_api._es_ceo`). |
| "Pendiente de aprobar" | **No existe como estado.** Un documento en borrador puede estar a medio capturar o listo para aprobarse, y no hay forma de distinguirlos. La OC solo tiene `revisado_yelke` / `revisado_por_yelke` / `revisado_en_yelke`. |
| Regresar a corregir | **No existe.** Tampoco hay motivo ni aviso. |
| Notificaciones de aprobación | **No existe ninguna.** No hay Notification, Workflow ni Server Script para aprobaciones, y en el código solo se crea `Notification Log` para el vencimiento de precios acordados. **Al CEO hoy no le llega ningún aviso cuando algo espera su aprobación.** Producción no lo pude revisar (no tengo permiso de lectura); falta confirmarlo ahí. |
| Campana del SPA | Ya existe en `AppNavbar.vue` y lee `Notification Log`, pero los avisos abren `/app/...` (escritorio de ERPNext), no el SPA. |
| Comentarios / línea de tiempo | El SPA no muestra ninguno. `HistorialModal.vue` es otra cosa: la cadena de revisiones del costeo. `Costeo` tiene `track_changes = 0`, así que hoy ni siquiera guarda versiones; `Purchase Order` sí las guarda. |
| Roles asignados (sandbox) | Nadie tiene `Director Yelke`, `Aprobador de Documentos Yelke`, `Revisor de Documentos Yelke` ni `CEO`. En producción existe el perfil de rol `CEO`, sin usuarios (memoria del 2026-10-08). |
| Celular | `App.vue` siempre pinta `AppSidebar` con ancho fijo (`w-52`, 208 px). En un teléfono de 390 px el contenido se queda con ~180 px. **Hoy el SPA no se puede usar en celular**; solo el menú de Producción tiene versión `movil`. |
| Diseño | El sistema `p-*` de Producción (`style.css`: `p-h1`, `p-eyebrow`, `p-panel`, `p-pill-*`, `p-dot-*`, `p-btn-*`, `p-tbl`…) y los componentes de `components/produccion/` (`PanelLateral`, `BarraAcciones`, `Pill`, `EstadoPunto`, `FilaLista`, `VacioEstado`, `Segmentado`) se reutilizan tal cual. |

### Por qué NO usar el Workflow nativo de ERPNext

Era la primera opción (ver la nota de no sobre-diseñar), pero choca con la app:

- Con un Workflow activo, Frappe **valida cada `save`/`submit` contra las transiciones** (`frappe.model.workflow.validate_workflow`). La app guarda y valida documentos por código en muchos puntos: auto-validación de la OC recién creada, `sub_validar_sco`, sincronización de cantidades, etc. Todos tendrían que conocer el Workflow o tronarían.
- Se podría poner Workflow en un solo doctype, pero `Purchase Order` lo crean y validan los flujos de Producción.

**Lo que sí se usa de ERPNext tal cual:** `Comment` para los comentarios, que ERPNext muestra en su timeline de `/app`; `Version` para los cambios; `Communication` para los correos ya enviados; `Notification Log` para la campana y el aviso en tiempo real, porque su `after_insert` ya hace `publish_realtime`; y `frappe.sendmail` para el correo. El estado de aprobación es un campo propio, con un motor chico que vive en un módulo nuevo.

---

## 2. Decisiones (recomendación ⇒ confirmar con el usuario)

| # | Decisión | Recomendación |
|---|---|---|
| D1 | ¿Qué rol abre el Panel de Dirección? | **`Director Yelke`**, más `System Manager` como acceso de desarrollador. Ver **ver** el panel y **aprobar** son cosas distintas: aprobar lo sigue decidiendo `Aprobador de Documentos Yelke`, que es lo que ya revisa el backend. El perfil de rol **`CEO`** de producción lleva los cuatro: `Director Yelke`, `Aprobador de Documentos Yelke`, `Aprobador de Precios Yelke` y `CEO` (legado). Así, un delegado futuro puede aprobar sin ver los números de la empresa. |
| D2 | ¿Qué ve el revisor? | Quien tiene `Revisor de Documentos Yelke` y no tiene `Director Yelke` ve **solo "Por revisar"**: lista, detalle, "Marcar revisado" y "Regresar". No ve proyectos ni resumen. |
| D3 | ¿Qué documentos pasan por aprobación? | ✅ **Decidido.** Los que ya la tenían: **Costeo** (Simple), **OC de materia prima** y **OC de maquila** (Doble) y **precios acordados** (Simple, CEO). Se agregan **Cotización**, **Orden de Venta** y **Factura de compra**, en Simple. La lista vive en `roles.py` (`DOCUMENTOS_CON_APROBACION`, con el doctype y su nivel). El candado va en **un hook `before_submit`** para que no lo salte ninguna puerta: `validar_documento`, `submit_quotation`, `submit_sales_order`, `submit_purchase_order` ni las que validan desde Producción. La Factura de venta se queda fuera porque es solo contable; la oficial se emite en otro sistema. |
| D4 | ¿Cómo entra algo a la bandeja? | Con un paso explícito **"Enviar a aprobación"** de quien captura (rol `Enviar Documentos Yelke`, que ya existe con ese fin). Sin ese paso, el CEO vería todos los borradores a medio capturar. Quien puede aprobar sigue teniendo "Validar" directo y no se le obliga a enviárselo a sí mismo. |
| D5 | ¿Qué pasa si editan un documento ya enviado? | **No se bloquea**, porque bloquearlo rompería los guardados automáticos. Sigue pendiente, pero se marca **"Cambió después de enviarse"**, el cambio aparece en la línea de tiempo y, en la OC (Doble), **se borra la revisión** para que vuelva a revisarse. |
| D6 | ¿Por dónde llega el aviso? | **Campana del SPA** (tiempo real) y **correo** con el formato de Yelke y un enlace directo al documento en el panel. No se aprueba desde el correo con un clic, por seguridad: el enlace abre el panel. WhatsApp queda fuera de este plan. |
| D7 | ¿Delegación del CEO (vacaciones)? | ✅ **Incluida (Fase 7)** y debe ser **fácil**: desde el panel, "Delegar" → a quién → desde/hasta → listo. Se termina sola en la fecha, se puede cancelar antes y el delegado recibe aviso al empezar y al terminar. |

---

## 3. Modelo de aprobación

### 3.1 Estados (campo `estado_aprobacion_yelke`, Select)

```
Borrador ──Enviar a aprobación──▶ Pendiente ──(Doble) Marcar revisado──▶ Revisado
   ▲                                │                                      │
   │                                └──────────── Aprobar ◀────────────────┘ (Simple: directo desde Pendiente)
   │                                                 │
   └──── Corregir y reenviar ◀── Devuelto ◀── Regresar (comentario OBLIGATORIO, desde Pendiente o Revisado)
                                                     ▼
                                                 Aprobado (= docstatus 1, por validar_documento)
```

- **Aprobar** llama a la puerta que ya existe (`validar_documento` o `validar_precios_acordados_costeo`), así que todos los candados actuales se conservan: OC del cliente adjunta, revisión previa de la OC, vistas de Producción. El motor solo agrega el estado, el comentario y los avisos.
- **Validar directo** (quien ya puede aprobar y nunca envió el documento) también lo marca `Aprobado`, por el hook `on_submit`, para que la bandeja nunca muestre algo ya validado.
- Cancelar un documento aprobado no cambia este modelo.

### 3.2 Campos nuevos (Custom Field por patch, en cada doctype de `DOCUMENTOS_CON_APROBACION`)

`estado_aprobacion_yelke` · `enviado_aprobacion_por` · `enviado_aprobacion_en` · `ultimo_motivo_devolucion` (texto corto, para mostrarlo sin consultar los comentarios) · `cambio_tras_envio` (Check).
En la OC se **reutilizan** `revisado_yelke` / `revisado_por_yelke` / `revisado_en_yelke`; no se duplican.
Los precios acordados no son un documento con docstatus. Su estado se toma de lo que ya existe (`precio_acordado_validado`) y la devolución queda como `Comment` sobre el Costeo.

### 3.3 Backend: módulo nuevo `costeo_yelke/api/aprobaciones.py`

Va en un módulo nuevo y no en `costeo_api.py` (11 mil líneas), para alinearse con `docs/refactor/01-ARQUITECTURA-DESTINO.md`.

| Endpoint | Quién | Qué hace |
|---|---|---|
| `enviar_a_aprobacion(doctype, name, comentario=None)` | `Enviar Documentos Yelke` / dueño | Borrador o Devuelto → Pendiente. Avisa a los revisores (Doble) o a los aprobadores (Simple). Si hay comentario, lo guarda. |
| `marcar_revisado(doctype, name, comentario=None)` | Revisor | Envuelve `marcar_revisado_documento` → Revisado. Avisa a los aprobadores. |
| `aprobar(doctype, name, comentario=None)` | Aprobador | Llama a `validar_documento` → Aprobado. Avisa a quien lo envió. |
| `regresar(doctype, name, motivo)` | Revisor o Aprobador | `motivo` obligatorio → Devuelto. Borra la revisión de la OC, guarda `Comment` y avisa a quien lo envió (o al `owner`). |
| `get_bandeja()` | Revisor / Aprobador | Pendientes del usuario, ya filtrados por su rol, con los datos de la tarjeta (ver §4.3). Pocas consultas en bloque, no una por renglón. |
| `get_resumen_documento(doctype, name)` | Revisor / Aprobador | Ficha normalizada para el detalle: encabezado, montos, renglones, adjuntos y alertas. |
| `get_mis_devueltos()` | Cualquiera | Lo que le regresaron al usuario y sigue sin reenviar. |
| `get_panel_direccion()` | `Director Yelke` | Proyectos y resumen (§4.4). Reutiliza `dashboard_metrics` y las lecturas de progreso que ya existen. |

Reglas comunes: las mismas que `validar_documento`, es decir, `_exigir_doctype_del_flujo`, el guard de uso interno de `security.py` y `requiere_vista` cuando aplique. Todo cambio de estado deja un `Comment` de tipo `Info` ("Enviado a aprobación", "Revisado por…", "Regresado: …").

---

## 4. Panel de Dirección (SPA)

### 4.1 Ruta y acceso
- Ruta nueva **`/direccion`**, con su entrada en `AppSidebar` ("Dirección" y un contador). Solo se muestra con D1 o D2; si alguien entra por URL sin el rol, ve "No tienes acceso", con el patrón de Producción.
- Al abrir el SPA, `Director Yelke` aterriza en `/direccion` y no en `/inicio`.
- Parámetros en la URL (`?tab=aprobar&doc=Purchase Order/PUR-ORD-…`), para que el enlace del correo y de la campana abra el documento exacto.

### 4.2 Diseño para celular (se diseña primero)

```
┌──────────────────────────┐         Escritorio (≥1024 px)
│ Dirección        🔔 3    │         ┌────────┬───────────────────┬──────────────┐
│ Buenos días, ⟨nombre⟩    │         │ menú   │ Por aprobar (lista)│ Detalle      │
│ 5 por aprobar · 2 hoy    │         │ app    │  tarjetas          │ (PanelLateral│
├──────────────────────────┤         │        │                    │  fijo)       │
│ [Costeo] [OC] [Precios]  │ ← filtro├────────┴───────────────────┴──────────────┤
│ ┌──────────────────────┐ │         └ barra de acciones fija del detalle ───────┘
│ │● OC maquila  $48,200 │ │
│ │ Taller Ruiz · Lote 2 │ │
│ │ Revisó Ana · hace 2h │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │● Costeo  margen 31%  │ │
│ │ FERROMEX · Camisola  │ │
│ └──────────────────────┘ │
├──────────────────────────┤
│ ✓ Aprobar │ ▦ Proyectos │ ◔ Resumen │  ← barra inferior fija (tabs)
└──────────────────────────┘
```

- **Armazón propio**: por debajo de 768 px, `/direccion` no pinta `AppSidebar`. Tiene su propio encabezado y una **barra de tabs inferior**, con `env(safe-area-inset-bottom)` para el iPhone. El resto del SPA no se toca en esta fase (ver §6, "No incluido").
- **Detalle del documento** = hoja a pantalla completa en celular y `PanelLateral` en escritorio. Arriba lleva lo que decide la aprobación (monto, contraparte, margen o costo y la alerta si hay). Después, los renglones **colapsados** ("Ver 12 renglones"), los adjuntos (PDF de la factura, OC del cliente) y la **línea de tiempo** (§5) con las últimas 3 entradas y "Ver todo".
- **Barra de acciones fija** abajo del detalle, con la regla de oro de Producción: la primaria a la derecha. **[Regresar]** abre una hoja con el comentario obligatorio. **[Aprobar]** pide confirmación cuando el monto pasa un umbral.
- Todo lo que se toca mide ≥ 44 px. En celular los montos van compactos ($1.2 M) y en escritorio completos.
- **Se oculta en celular:** columnas secundarias de las tablas, el desglose por talla (va detrás de "Ver detalle"), las gráficas del resumen (quedan los indicadores) y la línea de tiempo completa (queda colapsada).

### 4.3 Tab "Por aprobar" (CEO) / "Por revisar" (revisor)
- Tarjeta por documento: tipo (con su pill), folio, contraparte, monto, a qué costeo o lote pertenece, quién lo envió y **hace cuánto espera**. Si aplica, también **"Revisado por…"** y **"Cambió después de enviarse"**.
- Se agrupa por tipo y se ordena por antigüedad. Si espera más de 48 h, la tarjeta lleva un aviso.
- Lo que se muestra en cada tipo de documento:
  - **Costeo**: cliente, producto, cantidad, costo unitario, precio, margen, comparación con la versión anterior si es una revisión, y la cotización ligada.
  - **OC materia prima**: proveedor, total y moneda (con su tipo de cambio), renglones, lote y costeo, y fecha de entrega.
  - **OC maquila**: taller, servicios por prenda ($/prenda, como en el formato "Orden de Maquila"), cantidad y lotes.
  - **Precios acordados**: cliente, artículo, precio contra costo (margen) y vigencia.
  - **Cotización**: cliente, total, margen contra el costeo, vigencia y diferencia con la cotización anterior si es una revisión.
  - **Orden de Venta**: cliente, total, cantidades por producto o talla, fecha de entrega y la OC del cliente adjunta (con vista previa).
  - **Factura de compra**: proveedor, total con IVA o retenciones, la OC y el recibo que la respaldan (y si cuadran), y el PDF/XML adjunto.
- Estado vacío: "Todo al día ✓".
- Lo que aprobó o regresó hace poco queda en "Hoy aprobados (n)", colapsado, para poder deshacer una confusión con contexto.

### 4.4 Tabs "Proyectos" y "Resumen" (solo `Director Yelke`)
- **Proyectos**: una tarjeta por costeo activo, con el stepper compacto del ciclo (Costeo → Cotización → OV → Producción → Entrega → Factura), las prendas producidas sobre las vendidas, los lotes y la fecha de entrega. Muestra **alertas** de lo que está atascado: lote sin movimiento N días, OC esperando aprobación y factura pendiente. Al tocarla se abre el costeo en el SPA. Filtros: "Activos · Atrasados · Por cobrar".
- **Resumen**: 4 a 6 indicadores que **ya calcula** `dashboard_metrics` (embudo comercial, vendido o facturado del mes, cobrado, por cobrar, margen promedio) y la lista "requiere tu atención". **No se inventan métricas nuevas** sin pedirlas.

---

## 5. Comentarios y línea de tiempo en todos los documentos

### 5.1 Backend (en `aprobaciones.py`, o en `actividad.py` si crece)
- `get_actividad(doctype, name)` arma una lista ordenada con:
  - creación y quién lo creó;
  - `Version` con el diff **en palabras**: etiqueta del campo y valor antes → después, con renglones agregados o quitados resumidos;
  - `Comment` de tipo `Comment`, `Info`, `Attachment` y `Attachment Removed`;
  - `Communication` (correos enviados desde la app);
  - validado y cancelado.
  También trae los documentos ligados de un salto, por ejemplo el recibo o la factura de una OC (opcional, tras "Ver relacionados").
- `agregar_comentario(doctype, name, texto)` crea un `Comment` de tipo `Comment`, el **mismo** que crea ERPNext, así que también aparece en `/app`. Soporta @menciones con el mecanismo nativo, que genera un `Notification Log` "Mention".
- Permisos: los de las pantallas del SPA (usuario interno y doctype del flujo), porque los roles por vista no tienen lectura sobre los doctypes (`produccion-v2-decisiones`).
- `Costeo.track_changes = 1` (en `costeo.json` y en el patch). Se revisa también que los otros doctypes del flujo la tengan.

### 5.2 Frontend
- Componente **`ActividadDocumento.vue`**: línea de tiempo vertical con el estilo de `HistorialModal`/`p-*`, avatar e iniciales, fecha relativa y una caja de comentario abajo. Pinta resaltados el comentario de devolución y el de aprobación.
- Botón **"Actividad · 💬 n"** en el encabezado de cada documento, que abre el componente en un `PanelLateral`. Dónde va:
  - `CosteoDetailPage` (encabezado general);
  - `CotizacionDetailPage`, `SalesOrderDetailPage`, `PurchaseOrderDetailPage` y `SalesInvoiceDetailPage`;
  - en Producción, los paneles de documentos: `PurchaseDocPanel` (OC, recibo y factura de proveedor), `FacturaCompraPanel` y los pasos del taller (SCO, envío y recibo de maquila);
  - el detalle del Panel de Dirección.
- **Aviso de devolución dentro del documento**: si está `Devuelto`, aparece una franja ámbar arriba con "Regresado por ⟨nombre⟩: ⟨motivo⟩", el botón **"Ya lo corregí → Reenviar"** y el enlace a la conversación.

---

## 6. Notificaciones

| Evento | A quién | Campana (Notification Log) | Correo |
|---|---|---|---|
| Enviado a aprobación (Simple) | Aprobadores | ✓ | ✓ |
| Enviado a aprobación (Doble) | Revisores | ✓ | ✓ |
| Revisado | Aprobadores | ✓ | ✓ |
| **Regresado** | Quien lo envió (o el `owner`) | ✓ | ✓ con el motivo en el cuerpo |
| Aprobado | Quien lo envió | ✓ | — (configurable) |
| Comentario nuevo / @mención | Participantes / mencionado | ✓ (nativo) | nativo |
| Recordatorio diario: pendientes > 48 h | Aprobadores | ✓ | ✓ resumen, 1 correo al día |

- Los `Notification Log` se crean con `type="Alert"` y `link` al **SPA** (`/costeo-yelke/direccion?doc=…`, o la pantalla del documento para el empleado). Frappe no manda correo con los "Alert", así que el correo lo manda la app con `frappe.sendmail` y el membrete de Yelke. Así no salen correos duplicados ni el formato genérico de Frappe.
- `AppNavbar`: la campana abre el enlace del SPA cuando existe; si no, sigue abriendo `/app`. Se suscribe al evento realtime `notification` para que el contador suba sin recargar. Al aprobar o regresar, los avisos de ese documento se marcan como leídos.
- Los destinatarios se calculan con `Has Role` **y** con los **Role Profile** (trampa conocida: `perfil-de-rol-manda`). Los usuarios deshabilitados se excluyen.
- El recordatorio diario se agrega a `scheduler_events`, como `revisar_vigencias_precio_acordado`.

---

## 7. Fases

Cada fase termina verificada en sandbox y con aviso al usuario. Sin deploy hasta el final, salvo que se pida.

### Fase 0 — Preparación y mockup
- ✅ Bench arreglado (2026-10-19): se cambió la ruta vieja `/Users/trabajo/Documents/...` en 103 archivos de `env/` y `config/` y se rehicieron los 15 enlaces de `sites/assets`.
- ✅ Cambios de seguridad commiteados (`da6adc2`, solo local, sin push).
- ✅ Decisiones D1–D7 confirmadas.
- ✅ **APROBADO 2026-10-19** ("hazlo tal cual"), con un solo cambio: **sin vista de celular para el empleado**, porque siempre trabaja en computadora. La franja de devolución, la actividad y "Reenviar" van en sus pantallas de escritorio (§5.2). El celular es solo para el CEO, el delegado y el revisor. **Mockup HTML** `docs/mockups/direccion.html` con datos reales del sandbox: celular de 390 px (bandeja, detalle, hoja de "Regresar", proyectos y resumen), escritorio y la vista del revisor. **Aprobación del usuario antes de escribir código.**

### Fase 1 — Motor de aprobación (backend)
> ✅ **Hecha 2026-10-19 (backend de las Fases 1 y 2).** `api/aprobaciones.py`, `roles.py`, patch `v0_2_60.campos_aprobacion`, hooks `before_insert`/`before_submit`/`on_submit`/`on_update` y recordatorio diario. Prueba con 3 usuarios sin System Manager: **46/46** (en una transacción revertida). Regresión `e2e.py`: **20/20**. Cambios respecto al plan:
> - **Al enviar** se exige lo que de todos modos impediría validar, es decir, la OC del cliente en la OV y el PDF en la factura de compra. Así, al CEO no le llega algo que no puede aprobar.
> - **Ni revisar ni aprobar piden la vista de Producción**, para que un revisor o un delegado puedan hacerlo (`costeo_api._marcar_revisado`).
> - **`before_insert` deja todo documento nuevo en Borrador**, porque `frappe.copy_doc` ignora `no_copy` y una revisión de costeo nacía "Aprobada".
> - **Sin cuenta de correo saliente** (el sandbox no tiene), el correo se omite en silencio y la campana sigue funcionando.
> - **Pendiente para la Fase 4:** `useProduccion.validarOcsTallerPendientes` revisa y valida solas las OC a taller. Para quien no puede aprobar, tiene que **enviarlas a aprobación**.
- `roles.py`: `DOCUMENTOS_CON_APROBACION`, `puede_ver_panel_direccion()` y destinatarios por rol (con perfiles).
- Patch `v0_2_xx`: crear los Custom Field (§3.2), `track_changes` en Costeo y un backfill. Los documentos ya validados quedan `Aprobado` y los borradores quedan `Borrador`; **ningún borrador existente aparece en la bandeja.**
- `aprobaciones.py`: los endpoints de §3.3 y, en `hooks.py` → `doc_events` de cada doctype de la lista, tres hooks:
  - `before_submit`: el **candado único**. Exige que el documento esté aprobado o que el usuario pueda aprobar.
  - `on_submit`: lo marca como Aprobado.
  - `on_update`: pone la marca de D5.
- **Auditar antes cada `submit()` por código** de Quotation, Sales Order y Purchase Invoice (hoy pasan por `quotation_api.submit_quotation`, `sales_order_api.submit_sales_order`, `validar_documento` y los paneles de Producción). Ninguno debe quedar bloqueado por el candado sin que se haya decidido así. Si un flujo automático valida por código a propósito, se marca con `flags.aprobacion_yelke_sistema` y queda anotado en la línea de tiempo.
- `_es_ceo()` acepta también `Director Yelke` y `Aprobador de Precios Yelke` (hoy solo `CEO`).
- **Pruebas** con 3 usuarios del sandbox (empleado, revisor y CEO): las 4 transiciones, los rechazos por rol, el motivo vacío rechazado y validar directo. Regresión: la prueba integral (`docs/refactor/semillas/e2e.py`) debe seguir dando **20/20**.

### Fase 2 — Notificaciones
- Avisos de §6, correo con plantilla Yelke, recordatorio diario, campana del SPA con enlace al SPA y tiempo real, y "marcar leído al resolver".
- Prueba: cada evento genera exactamente 1 aviso por destinatario, sin duplicar correos (revisar la `Email Queue` del sandbox).

### Fase 3 — Línea de tiempo y comentarios
- `get_actividad` / `agregar_comentario` y `ActividadDocumento.vue`.
- Botón "Actividad" en **todas** las pantallas de §5.2 y franja de devolución con "Reenviar".
- Prueba: un comentario hecho en el SPA se ve en `/app/<doctype>/<name>`, y uno hecho en `/app` se ve en el SPA.

### Fase 4 — Panel de Dirección: bandeja y detalle
- Ruta `/direccion`, armazón para celular, tab "Por aprobar", detalle con acciones y la vista limitada del revisor (D2).
- Botón **"Enviar a aprobación"** en todas las pantallas que hoy tienen "Validar" para algún documento de la lista: Costeo, Cotización, OV, OC (pantalla propia y Producción) y Factura de compra (bandeja de Facturas y panel del proveedor). Quien no puede aprobar ve "Enviar" en lugar de un "Validar" deshabilitado.
- "Devueltos a mí": contador en la campana y lista corta en `/inicio` para el empleado.

### Fase 5 — Proyectos y resumen
- `get_panel_direccion()` con consultas en bloque y los tabs "Proyectos" y "Resumen" (§4.4).

### Fase 6 — Pulido para celular
- Recorrido con Playwright a 390×844 y 768×1024, más escritorio: sin desbordes horizontales, barras fijas que no tapen contenido, teclado abierto en "Regresar" y modo oscuro si aplica.
- Rendimiento: con 50 pendientes, la bandeja carga en menos de 1 s en el sandbox.

### Fase 7 — Delegación por vacaciones (incluida, prioridad alta)
**Lo que ve el CEO**, en el panel → menú "⋯" o tarjeta en Resumen:
"Delegar mis aprobaciones" → elegir persona → **desde / hasta** → motivo opcional → [Delegar]. Son tres campos en una hoja que cabe en el celular.

Mientras está activa, una franja en el panel dice "⟨Ana⟩ aprueba por ti hasta el 30-oct · [Terminar ahora]".

**Cómo funciona por dentro:**
- DocType **"Delegación de Aprobación Yelke"**: de, a, desde, hasta, motivo y estado (Programada / Activa / Terminada / Cancelada). Solo `Director Yelke` (o `Supervisor Yelke` como respaldo) la crea o la cancela.
- **No se le dan ni se le quitan roles al delegado.** `puede_aprobar_documentos()` y `puede_revisar_documentos()` revisan además si el usuario tiene una delegación activa **hoy**. Así no se dispara la trampa del Role Profile ([[perfil-de-rol-manda]]), no hace falta un job para quitar el permiso (vence solo por fecha) y "Terminar ahora" surte efecto al instante.
- El delegado ve **"Por aprobar"** con acciones, sin los tabs de proyectos y resumen (D1).
- Avisos:
  - durante la delegación, los pendientes nuevos le llegan **al delegado y al CEO**;
  - un job diario avisa al delegado que la delegación "empieza hoy" y "termina hoy".
- Línea de tiempo: "Aprobado por ⟨Ana⟩ **en nombre de** ⟨CEO⟩ (delegación del 20 al 30-oct)".
- Validaciones: no se puede delegar a uno mismo, ni a un usuario deshabilitado, ni con fechas cruzadas. Solo puede haber una delegación activa a la vez por persona que delega.
- Pruebas: una delegación programada para mañana todavía no da permiso; una activa sí; vencida o cancelada ya no. El candado `before_submit` respeta la delegación.

### Fase 8 — Cierre
- Prueba de punta a punta por rol, en el sandbox:
  - **OC:** el empleado la envía, el revisor la revisa, el CEO la regresa desde el celular, el empleado recibe el aviso, la corrige y la reenvía, y el CEO la aprueba. La línea de tiempo muestra todo.
  - Lo mismo con un Costeo, una Cotización, una OV, una Factura de compra y un precio acordado.
  - Una vez con delegación activa.
- Manual (sección de roles y aprobaciones), Matriz de Alcance (2.5), commit solo de las rutas propias (hay sesiones en paralelo), build del SPA y deploy con `update_costeo.sh`.
- **En producción**: crear o asignar los usuarios al perfil `CEO`, al rol de revisor y a `Enviar Documentos Yelke`. Antes, el usuario debe indicar qué persona lleva qué rol.

---

## 8. Riesgos y cómo se cubren

| Riesgo | Mitigación |
|---|---|
| Romper un flujo que guarda o valida por código | No se usa Workflow nativo, no se bloquean ediciones (D5) y "Aprobar" reutiliza `validar_documento`. Regresión e2e 20/20 en cada fase. |
| Los avisos no les llegan a usuarios con Role Profile | Los destinatarios se calculan también desde los perfiles, y se prueba con un usuario con perfil. |
| La bandeja se llena de borradores viejos | El backfill deja `Borrador`. Solo entra lo enviado explícitamente (D4). |
| Correos duplicados o con el formato de Frappe | `type="Alert"` y el correo propio. Se revisa la `Email Queue`. |
| Choque con la otra sesión o con el refactor | Módulo nuevo `aprobaciones.py` (fuera de `costeo_api.py`), componentes nuevos y cambios mínimos en las páginas grandes. Commit por rutas, nunca `git add -A`. |
| Datos financieros a la vista de un delegado o revisor | El panel completo exige `Director Yelke` (D1) y el backend lo revisa en `get_panel_direccion`. |

## 9. No incluido (salvo que se pida)
- Hacer usable en celular **todo** el SPA. Solo `/direccion` y la vista del revisor quedan listas para celular; las demás pantallas siguen pensadas para escritorio.
- Notificaciones push nativas o por WhatsApp.
- Aprobar desde el correo con un clic.
- Aprobación por montos (doble firma arriba de $X) y cambios al esquema Simple/Doble actual, más allá de la lista configurable.
