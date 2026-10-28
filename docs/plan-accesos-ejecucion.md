# Plan de ejecución: accesos por vista y reglas de captura

*2026-10-28. Diseño y decisiones en `docs/plan-accesos-por-vista.md` (§9 decisiones, §10 roles de ERPNext, §11 reglas de captura). Aquí está el **cómo**: tareas, archivos, pruebas y qué significa "terminado" en cada fase.*

---

## 0. Reglas para todas las fases

1. **Nadie pierde acceso en ningún deploy.** Hasta la fase 9, todos los usuarios tienen el perfil transitorio "Acceso completo Yelke". Cada fase se puede subir sola.
2. **Una sola fuente de verdad.** Vistas, roles, pasos, listas y permisos de ERPNext salen del catálogo de `costeo_yelke/roles.py`. Ningún nombre de rol se escribe a mano en la pantalla ni en otro módulo.
3. **Todo lo que configura va en patch** idempotente (corre dos veces sin cambiar nada) y entra con el `migrate`. Nada a mano en producción.
4. **Commit solo de mis rutas** (hay otra sesión en el repo). Un commit por fase, con su prueba.
5. **Trampas conocidas que hay que respetar:**
   - **Role Profile:** reemplaza los roles del usuario en cada guardado. Los roles se dan en el perfil y luego se re-guarda cada usuario.
   - **Caché:** `frappe.get_roles` lee de Redis. Hay que limpiar la caché después de asignar.
   - **DocPerm:** con un solo Custom DocPerm, Frappe ignora los estándar. Se usa `frappe.permissions.add_permission`, que copia los estándar primero.
   - **hooks.py:** el bloque de mayúsculas *reemplaza* el diccionario de eventos de varios doctypes. Todo lo nuevo se agrega después y como lista.
   - **Tras tocar hooks.py:** `bench clear-cache`.

### Antes de empezar
- [ ] Commit de lo pendiente desde `ed6341a` (bandejas, facturas, IVA, reporte…) en commits propios, para que este trabajo arranque limpio.
- [ ] Respaldo de la base de yelke.localhost (sitio de pruebas).
- [ ] Usuarios de prueba en yelke.localhost, uno por perfil, sin System Manager: `compras@`, `almacen@`, `ventas@`, `finanzas@`, `direccion@`, `lectura@` (`.test`, contraseña en `e2e/usuarios.json`, no en el chat).

---

## Fase 1 · Reglas de captura (independiente de todo lo demás)

**Objetivo:** que clientes, proveedores, direcciones, contactos, cuentas y folios queden escritos de una sola forma, se capturen en la app o en el Escritorio.

### 1.1 Módulo nuevo `costeo_yelke/overrides/captura.py`
Funciones puras, probables sin base de datos:

| Función | Hace | Error si |
|---|---|---|
| `texto(v)` | quita espacios al inicio y al final, junta dobles, MAYÚSCULAS con acentos y Ñ | — |
| `estado_mx(v)` | devuelve una de las 32 entidades oficiales; resuelve alias (QRO, QUERETARO, EDO DE MEXICO, EDOMEX, MEXICO→ESTADO DE MÉXICO, CDMX, DF, D.F., CIUDAD DE MEXICO, NL, BCS, SLP, …) sin importar acentos ni puntos | no es una entidad: "MOROLEON no es un estado. Elige uno de la lista." |
| `cp_mx(v)` | solo dígitos | no son 5 dígitos |
| `telefono_mx(v)` | quita +52, 52 y 1 iniciales, espacios, guiones y paréntesis → `442 467 8939` | no quedan 10 dígitos. Si trae "ext", la extensión se conserva: `442 467 8939 ext 12` |
| `correo(v)` | minúsculas, sin espacios | formato inválido |
| `rfc(v)` | MAYÚSCULAS, sin espacios ni guiones | no cumple el patrón de persona moral (12), física (13) o genérico (XAXX010101000 / XEXX010101000) |
| `clabe(v)` | solo dígitos | no son 18 o falla el dígito verificador (algoritmo de Banxico) |
| `tarjeta(v)` | solo dígitos | no son 16 (15 para AmEx) |

Las 32 entidades van con sus nombres oficiales en mayúsculas y con acento (AGUASCALIENTES … ZACATECAS, más CIUDAD DE MÉXICO y ESTADO DE MÉXICO), en `ESTADOS_MX` dentro del mismo módulo.

**Extranjeros:** si `country` no es Mexico, no se aplican estado, CP, teléfono a 10 dígitos ni RFC mexicano. Solo se normalizan texto y correo.

### 1.2 Hooks (en `hooks.py`, después del bloque de mayúsculas, como listas)

| Doctype | Evento | Reglas |
|---|---|---|
| Customer / Supplier | before_validate | `texto` en razón social y `nombre_comercial` (agregar a `UPPER_FIELDS`); `rfc` en tax_id |
| Customer / Supplier | validate | RFC duplicado en el mismo doctype → error con el nombre del otro registro (excepto genéricos). Va junto a `validar_rfc` (doble captura) |
| Address | before_validate | `texto` (ya existe vía UPPER_FIELDS) + `estado_mx`, `cp_mx`, `telefono_mx` (phone, fax), `correo`; country = Mexico si viene vacío |
| Address | validate | al menos una liga (Customer, Supplier o Company) |
| Contact | before_validate | `texto` (ya existe) + `correo` en email_id y en la tabla `email_ids`; `telefono_mx` en phone, mobile_no y la tabla `phone_nos` |
| Contact | validate | al menos una liga a Customer o Supplier (los contactos de usuario o del sistema, como "MAILER DAEMON", no se tocan: se excluyen los ligados solo a User o sin compañía) |
| Bank Account | validate | `clabe`, `tarjeta`, junto a la doble captura que ya existe |
| Supplier (cuenta en campos `cb_*`) | validate | `clabe` en `cb_clabe`, `tarjeta` en `cb_tarjeta` |
| Sales Order | before_validate | `po_no` → `texto` |
| Purchase Invoice | before_validate | `bill_no` → `texto` |
| Item | before_validate | `description` sin espacios al inicio y al final |

### 1.3 Estado como lista en el Escritorio
- Property Setter: `Address.state` → `fieldtype Select`, `options` = las 32 entidades. Va en un patch y se exporta a la app (fixture de property setter o patch, igual que otros).
- **Va después del patch de normalización (1.5)**; si no, las direcciones viejas con valores fuera de la lista no se podrían volver a guardar.
- Formularios del SPA con campo estado, que cambian a `<select>` con `ESTADOS_MX` (servidos por un endpoint `catalogo_estados()`):
  - `components/DireccionClienteModal.vue` (estado y CP con `inputmode="numeric" maxlength=5`).
  - Buscar el resto con `grep -rn "state" frontend/src`: alta de cliente y de proveedor en ProductoNuevo, CotizacionDetail, SalesOrderDetail y PurchaseOrderDetail si capturan dirección.

### 1.4 Mensajes
Todos en español y sobre el dato, con el valor recibido: *"El teléfono «44 21 3» debe tener 10 dígitos (ej. 442 467 8939)."*

### 1.5 Patch `v0_2_69.normalizar_maestros` (datos existentes)
- Recorre Customer, Supplier, Address, Contact (con sus tablas), Bank Account, Sales Order (po_no) y Purchase Invoice (bill_no), y aplica las funciones con **`db_set` sin disparar validaciones**.
- **No rompe nada:** lo que no se puede corregir solo (estado que es ciudad, CP de 4 dígitos, teléfono de 8, RFC duplicado, contacto sin liga) **no se toca** y se anota en una lista.
- La lista se guarda como un Comment en un registro "Revisión de datos maestros" o como archivo CSV en File (decidir en la fase) y se avisa al Supervisor.
- **Idempotente:** la segunda corrida no cambia nada.
- **Dato real de hoy:** en yelke.localhost hay 15 formas de estado. Se espera resolver todas menos "MOROLEON" (y "MEXICO", que es ambiguo; se asume ESTADO DE MÉXICO y se reporta).

### 1.6 Pruebas
- [ ] Prueba unitaria de cada función: casos válidos, alias, errores y extranjeros (`scratchpad/test_captura.py`, sin base).
- [ ] Con rollback: crear o editar cliente, proveedor, dirección, contacto y cuenta bancaria con datos sucios y comprobar que quedan limpios. Lo inválido rebota con el mensaje esperado.
- [ ] Patch en seco con rollback: cuántos registros cambia y cuántos reporta. Después corrida real y segunda corrida (0 cambios).
- [ ] SPA: alta de dirección desde Entrega (modal), alta de cliente y de proveedor; el desplegable de estado funciona.
- [ ] Escritorio: crear una dirección con estado "qro" → se guarda "QUERÉTARO"; un CP de 4 dígitos → error.
- [ ] Facturas, remisiones, cotizaciones y OV existentes se siguen abriendo e imprimiendo, con la dirección impresa bien.

**Terminado cuando:** todo lo anterior pasa y la lista de pendientes manuales está revisada con el usuario.

---

## Fase 2 · Catálogo de vistas y roles (servidor, sin cambio visible)

### 2.1 `roles.py` → catálogo `VISTAS`
Una entrada por vista (~22, ver §3.2 del diseño):

```python
"materia": {"etiqueta": "Materia prima", "grupo": "Producción",
            "rol_editar": "Producción Materia Prima Yelke",          # existente
            "rol_ver": "Ver Producción Materia Prima Yelke",          # nuevo
            "paso": "producir", "sub": ["materia"],                  # dónde vive
            "listas": ["PurchaseOrderList", "PurchaseReceiptList"],
            "doctypes": {"Purchase Order": "editar", "Supplier Quotation": "editar", ...}}
```

- **Nombres de los roles nuevos:** `"<Grupo> <Vista> Yelke"` y `"Ver <Grupo> <Vista> Yelke"`, por ejemplo "Comercial Costear Yelke" y "Ver Comercial Costear Yelke". Así se ordenan juntos en ERPNext.
- **Las 9 de Producción conservan su clave y su rol de editar** (los usan 42 candados y los perfiles de producción); solo se agrega su rol de ver.
- `VISTAS_PRODUCCION`, `ROLES_VISTA_PRODUCCION` y `ETIQUETAS_VISTA` pasan a **derivarse** del catálogo (mismos nombres exportados, para no romper importaciones).
- Roles de proceso viejos (`ROLES_PROCESO`: Costeador, Cotizador…): ninguna lógica los usa. **No se borran** en esta fase y se documenta que quedan en desuso.

### 2.2 Funciones
- `accesos(user=None) -> {clave: "editar" | "ver"}`. Si el usuario tiene editar y ver, gana editar. Pase libre (Director, Supervisor, System Manager) = todo en editar. Los préstamos de permisos ya agregan roles, así que entran solos.
- `puede(clave, nivel="ver")` y `requiere_vista(*claves, nivel="editar")`. Compatibilidad: sin `nivel` = editar, como hoy.
- `vistas_produccion()` = claves de producción con al menos ver (mismo uso de hoy).
- Caché por usuario en `frappe.cache` (clave `accesos::<user>`), que se limpia en `User.on_update`, `Role Profile.on_update` y al otorgar o vencer un préstamo.

### 2.3 Endpoint
- `get_permisos_validacion_yelke()` agrega `accesos` (el dict). Se mantiene `vistas` para compatibilidad.
- `roles.mis_accesos()` (whitelist) por si otra página lo necesita sin el resto.

### 2.4 Patch `v0_2_70.roles_por_vista`
- Crea los roles que falten (desk_access = 1).
- Crea el Role Profile "Acceso completo Yelke" con **todos los roles de editar**.
- A cada usuario activo de tipo System User que no tenga ninguna vista:
  - con Role Profile: agrega los roles de editar **a su perfil** y re-guarda a los usuarios de ese perfil;
  - sin perfil: le agrega los roles directo.
- `bench clear-cache` al final (`frappe.clear_cache()`).

### 2.5 Pruebas
- [ ] Unitarias de `accesos()`: solo ver; ver + editar; pase libre; préstamo vigente y vencido.
- [ ] Patch en seco: lista de usuarios y perfiles que tocaría. Después corrida real; todos siguen viendo todo en la app.

---

## Fase 3 · Pantalla: menú, stepper, rutas y solo lectura

### 3.1 Composable `frontend/src/composables/useAccesos.js`
- Carga una vez `accesos` (de `get_permisos_validacion_yelke`) y expone `puede(clave)`, `puedeEditar(clave)`, `pasosPermitidos`, `listasPermitidas` y `cargado`.
- Necesita del servidor solo la tabla vista → paso / sub / listas: el endpoint devuelve también ese mapa, para no duplicar el catálogo en JS.

### 3.2 Menú (`components/AppSidebar.vue`)
- Cada `NavItem` declara su vista o lista; solo se pinta si `puede(...)`. Un grupo sin ítems no muestra su título.
- **Lista → vista dueña:**
  - Cotizaciones → cotizar.
  - Órdenes de venta → vender.
  - Solicitudes de material → preparación.
  - Órdenes de compra → materia, talleres.
  - Recibos de compra → envíos, materia.
  - Remisiones → entrega, envíos.
  - Facturas de venta → facturar.
  - Facturas de compra → facturas.
  - Productos → alta; Plantillas → plantillas; Recordatorios de precio → precios; Dirección → direccion.
  - Proyectos: siempre, para todos (decisión 2).
- **Enlaces externos al Escritorio** (Plan de producción, Órdenes de trabajo, Subcontratación, Escritorio ERPNext): solo con la vista que corresponde; "Escritorio ERPNext" para todos (decisión 6).

### 3.3 Rutas (`router/index.js`)
- `meta.vista` (o lista de vistas) en cada ruta. Una guardia global: si no `puede`, manda a `/inicio` con el aviso "No tienes acceso a …".
- Las rutas `/…/nueva` piden **editar**.

### 3.4 Stepper (`components/CosteoStepper.vue` + `CosteoDetailPage.vue`)
- Prop nueva `permitidos: string[]` (claves de paso); los demás no se pintan (igual que `oculto`). **Los índices no cambian** (`?step=`, `STEP_ORDER_IDX`).
- Etiqueta de estado del proyecto visible siempre ("En producción", "Entregado"…), para que quien no ve los pasos sepa en qué va.
- `CosteoDetailPage`:
  - Al abrir, si `statusToStep()` o `?step=` cae en un paso no permitido → el más cercano permitido.
  - Si no tiene ninguno → "No tienes etapas asignadas en este proyecto".
  - `goStep()` rechaza pasos no permitidos.
  - Botón principal de la barra (Pasar a cotización, Generar OV, Alta de productos, Ir a facturar…): solo si tiene **editar del paso al que lleva**.

### 3.5 Solo lectura por paso
- Pasos de formulario (Costear, Cotizar, Vender, Alta de productos, Flujo, Facturar): el contenido del paso va dentro de `<fieldset :disabled="soloLecturaPaso">`. El navegador deshabilita todos los inputs y botones de adentro sin tocar cada uno.
  - Lo que debe seguir activo con solo ver (Vista previa, Descargar PDF, abrir documento, cambiar de OV activa, actividad) se saca del fieldset o se marca para quedar fuera.
  - Una franja arriba del paso: "Solo lectura · lo captura <vista>".
- Producción: hoy `puedeVer(clave)` significa "puede abrir **y** capturar". Se separa:
  - `puedeVer` = abrir (ver o editar);
  - `puedeEditar` = acciones.
  - Revisar cada uso (≈ 20) — líneas de referencia: 1810, 2178, 2367, 3337, 3866, 5021–5028, 5540 y las acciones de las barras.
  - Los paneles laterales usan su prop `solo-lectura` cuando no hay editar.
- Páginas sueltas de documento (CotizacionDetail, SalesOrderDetail, PurchaseOrderDetail, SalesInvoiceDetail) y ProductoDetail: el mismo `fieldset` con la vista dueña.
- Listas: el botón "Nuevo …" solo con editar.

### 3.6 Inicio y Dirección
- `/direccion` pide la vista "direccion" (hoy: rol de aprobación o Director). Las aprobaciones siguen visibles para quien tiene Revisor o Aprobador aunque no tenga la vista (la bandeja de aprobación es independiente).
- Inicio: el tablero financiero con "indicadores"; el operativo, para todos.

### 3.7 Pruebas
- [ ] Playwright con los usuarios de prueba: para cada perfil, menú esperado, pasos del stepper esperados, una ruta prohibida que redirige y un paso en "ver" sin botones ni campos activos.
- [ ] El administrador sigue viendo y haciendo todo (regresión del flujo completo con el ejemplo de camisola).

---

## Fase 4 · Candados mínimos en el servidor (decisión: sin auditoría de lecturas)

Solo escrituras de las etapas que hoy no tienen candado:

| Vista | Endpoints (en `api/costeo_api.py` salvo indicación) |
|---|---|
| Costear | guardado del Costeo (hook `Costeo.validate`: si cambian campos de costeo y el usuario no tiene editar de "costear"); `crear_revision_costeo`, `reabrir_costeo` |
| Cotizar | `crear_cotizacion`, envío y rechazo de cotización, guardado de cotización |
| Vender | `crear_orden_venta`, guardado de OV, `generar_replica_ov`, cancelar OV, OC del cliente |
| Alta de productos | `materializar_articulo` y altas de producto |
| Flujo | confirmar y revertir flujo (`revertir_flujo_produccion`, `confirmar…`) |
| Facturar | `crear_factura_venta`, `actualizar_factura_venta`, validar factura de venta |
| Precios | fijar precio acordado y tabla por volumen |

- Los 42 candados de Producción pasan a `nivel="editar"` (es lo mismo de hoy; se revisa que ninguno sea de lectura).
- **Hacer primero un inventario rápido** con `grep -n "@frappe.whitelist" -A3`, solo de las escrituras de esas vistas, y anotarlo en este documento antes de tocar código.
- Pruebas: con un usuario "ver" de cada vista, llamar a un endpoint de escritura → `PermissionError` con mensaje en español.

---

## Fase 5 · Permisos de ERPNext por vista (Escritorio y API estándar)

### 5.1 Tabla de permisos en el catálogo
Cada vista declara `doctypes: {doctype: nivel}` (ver §10 del diseño). Además:
- **Lectura base para todos los roles de vista:** Company, Warehouse, Currency, UOM, Item Group, Customer Group, Supplier Group, Territory, Country, Payment Terms Template, Terms and Conditions, plantillas de impuestos, Mode of Payment, Price List, Talla, Print Format, Letter Head. Sin esto, los formularios no cargan los desplegables.
- **Niveles a permisos:**
  - ver → read, print, email, report, export;
  - editar → además write, create;
  - submit solo en doctypes con candado de aprobación o donde la etapa valida directo (recibos, remisiones, movimientos);
  - cancel, delete y amend → solo Supervisor y Director.
- **Costeo** (doctype propio): read para todas las vistas; write para costear, alta, flujo, OM y preparación (todos guardan partes del Costeo); submit, cancel y amend → costear (sujeto a aprobación).
- **File** (adjuntos): hereda del documento; revisar que subir PDF y XML en facturas funcione con editar.

### 5.2 Patch `v0_2_71.permisos_por_vista`
- Para cada (doctype, rol, nivel): `add_permission(doctype, rol, 0)` y `update_permission_property(...)` por cada ptype.
- Idempotente.
- No toca los permisos de System Manager ni de los roles estándar de ERPNext que ya existan (Accounts User, Stock User…), para no romper el Escritorio de quien ya los use.

### 5.3 Pruebas
- [ ] Con cada usuario de prueba sin System Manager:
  - la app carga sus vistas y sus listas sin errores 403;
  - en el Escritorio puede crear lo de su vista (un proveedor con "materia") y no lo de otra (un cliente con "materia" → sin permiso).
- [ ] Imprimir y descargar PDF con "ver".
- [ ] Subir adjuntos con "editar".
- [ ] Validar un documento con aprobación con "editar" sin rol de aprobador → lo manda a aprobar, no lo valida.

---

## Fase 6 · Mi panel (Inicio por usuario)

### 6.1 Servidor `costeo_yelke/api/mi_panel.py` → `get_mi_panel()`
Una sección por vista con editar del usuario. Cada renglón trae `{titulo, detalle, costeo, ruta}`, donde `ruta` es la URL exacta (paso, `vista`, `lote`, `paso`, `parada` de `useProduccionRuta`). Consultas **entre proyectos** (hoy los pendientes se calculan dentro de cada costeo):

| Vista | Pendiente | Fuente |
|---|---|---|
| Costear | costeos en borrador (propios primero) | Costeo docstatus 0 |
| Cotizar | costeos validados sin cotización; cotizaciones en borrador o sin enviar | Quotation |
| Vender | cotizaciones aceptadas sin OV; OV en borrador o sin enviar | Quotation, Sales Order |
| Alta / Flujo | OV validadas con artículos por dar de alta o flujo sin confirmar | Costeo status + pendientes |
| Preparación | OV en producción sin solicitud o sin lote | Production Plan, Material Request |
| Materia | solicitudes sin OC; OC sin enviar; OC sin recibir | MR, PO |
| Talleres | órdenes a taller sin validar; encargos sin envío; en taller sin recibir | PO subcontratada, SCO, SE |
| Envíos | lo mismo que la bandeja de envíos, entre proyectos | PR, SE, SCR, DN |
| Facturas | maquila recibida sin facturar; facturas en borrador (incluidas las de flete) | `get_facturas_compra` por costeo activo |
| Entrega | lotes con prendas producidas sin remisionar | SCR del taller final contra DN por `lote_ref` |
| Facturar | remisiones validadas sin factura de venta | DN, SI |

- Se limita a proyectos **activos** (no Completado ni Cancelado) para que sea rápido.
- Medir el tiempo de respuesta con el volumen de producción.

### 6.2 Pantalla `pages/DashboardPage.vue` (Inicio)
- Arriba: **Por aprobar** y **Me regresaron** (componentes de Dirección que ya existen).
- **Mis pendientes** agrupados por vista, con contador; cada renglón abre la ruta exacta.
- **Proyectos recientes** en los que participó (por Version o owner).
- Debajo, el tablero que ya existe (financiero u operativo según "indicadores").
- `/direccion` se queda como el panel completo de la empresa para quien tiene esa vista.

### 6.3 Pruebas
- [ ] Con datos de sandbox o del ejemplo: cada perfil ve solo sus secciones y cada enlace abre el lugar correcto (lote, taller y panel).
- [ ] Desempeño: menos de 1.5 s con todos los proyectos activos.

---

## Fase 7 · Listas de documentos

- **Enlaces viejos:** corregir el `step: "6"` de remisiones y los `step: "5"` genéricos para que lleguen al lote, la parada y el panel exactos, con las rutas de Producción. Hace falta que cada lista traiga `lote_ref` y, para OC, la parada (agregar al `get_list` de cada página).
- **Abrir un documento con proyecto:**
  - si tiene la vista del paso → al proyecto en su lugar exacto con el panel abierto;
  - si no, panel lateral de solo lectura en la misma lista.
- **Abrir un documento sin proyecto:**
  - Cotización, OV, OC y Factura de venta → su página de detalle (ya existe, ahora con solo lectura por vista);
  - Solicitud, Recibo, Remisión y Factura de compra → panel lateral de solo lectura con `direccion.get_resumen_documento` (ya existe, lo usa Dirección) y botones Vista previa, Descargar y ERPNext ↗.
- **Crear desde la lista** (decisión 3): solo con editar de la vista dueña. Revisar que "Nueva OC" y "Nueva OV" sueltas sigan funcionando.
- **Pruebas:** por cada lista, abrir un documento con y sin proyecto, con editar y con ver.

---

## Fase 8 · Pantalla de Accesos y "Ver como…"

### 8.1 Servidor `costeo_yelke/api/accesos.py` (solo Supervisor y Director)
- `get_matriz()`:
  - perfiles (Role Profile) con su nivel por vista;
  - usuarios con su perfil y sus roles sueltos de vista;
  - préstamos vigentes.
- `guardar_perfil(perfil, niveles)` (escritura delicada):
  1. reescribe los roles de vista del perfil;
  2. re-guarda cada usuario del perfil;
  3. limpia la caché;
  4. deja un Comment con quién cambió qué.
- `crear_perfil(nombre)`, `asignar_perfil(usuario, perfil)`.

### 8.2 Pantalla `pages/AccesosPage.vue` (ruta `/accesos`, vista "accesos")
- Matriz perfiles × vistas agrupadas (Comercial, Ingeniería, Producción, Finanzas, Dirección); cada celda es un selector — / Ver / Editar.
- Lista de usuarios con su perfil (selector) y sus préstamos.
- Aviso antes de guardar: "Esto cambia lo que ven N usuarios".

### 8.3 "Ver como…"
- Selector de usuario o perfil en la barra superior (solo Supervisor y Director). Reemplaza en la pantalla el resultado de `accesos` por el del elegido: menú, stepper y solo lectura.
- **Límite claro:** el servidor sigue tratando al administrador como administrador. Es una vista previa de lo que verá la persona, no una sesión con su usuario.

### 8.4 Pruebas
- [ ] Cambiar un perfil en la matriz → su usuario de prueba ve el cambio al recargar.
- [ ] La trampa del Role Profile está cubierta: los roles persisten después de guardar al usuario.

---

## Fase 9 · Pruebas finales, manual y salida

- **Playwright `e2e/accesos/`:** un guion por perfil (menú, stepper, solo lectura, rutas prohibidas, listas, Mi panel, Escritorio), que corre en yelke.localhost.
- **Regresión completa del flujo** con el administrador (ejemplo de camisola: costeo → factura → reporte).
- **Manual:** sección nueva "Accesos y perfiles" (qué es cada vista, ver contra editar, cómo asignar, "Ver como"); sección "Reglas de captura" (cómo se escriben estado, teléfono, RFC…). Ver la memoria del manual para editar el HTML grande sin romperlo.
- **Quitar el perfil transitorio:** solo cuando el usuario haya asignado perfiles reales. Es un paso manual desde la pantalla de Accesos, no un patch.
- **Deploy:** se suma al checklist de producción de contabilidad (`checklist-deploy-contabilidad`):
  - confirmar en el Patch Log v0_2_69, v0_2_70 y v0_2_71;
  - revisar la lista de datos a corregir a mano;
  - confirmar que los 8 usuarios de producción conservan acceso.

---

## Riesgos y cómo se cubren

| Riesgo | Cobertura |
|---|---|
| Alguien se queda sin acceso al subir | perfil transitorio "Acceso completo" (fase 2) y nada se quita hasta la fase 9 |
| Direcciones viejas que ya no se pueden guardar por el estado en lista | normalización (1.5) **antes** del Select (1.3); lo no corregible queda reportado |
| Custom DocPerm que borra los permisos estándar | `add_permission` copia los estándar; prueba con el Escritorio en 5.3 |
| Roles que no persisten por el Role Profile | todo se asigna vía perfil y se re-guarda al usuario (2.4, 8.1) |
| Caché que muestra accesos viejos | limpieza en los hooks de User, Role Profile y préstamo (2.2) |
| Lectura directa por API de etapas que no ve | **riesgo aceptado** (decisión del 2026-10-28) |
| Mi panel lento con muchos proyectos | solo proyectos activos; medir en 6.3 |
| Botones que deberían seguir activos en solo lectura (PDF, vista previa) | lista explícita en 3.5 y prueba por paso |
| Contactos del sistema (correo entrante) sin liga | excluidos de la regla de liga (1.2) |
| Clientes extranjeros | reglas mexicanas solo con country = Mexico (1.1) |

## Orden recomendado y tamaño

| # | Fase | Tamaño | Depende de |
|---|---|---|---|
| 1 | Reglas de captura | media | — |
| 2 | Catálogo y roles | chica | — |
| 3 | Pantalla (menú, stepper, rutas, solo lectura) | media-grande | 2 |
| 4 | Candados mínimos del servidor | chica | 2 |
| 5 | Permisos de ERPNext | media | 2 |
| 6 | Mi panel | media | 2 |
| 7 | Listas | media | 3 |
| 8 | Accesos y "Ver como" | media | 2, 3 |
| 9 | Pruebas, manual y salida | media | todas |

Al cerrar cada fase: prueba de la fase, commit propio y aviso con lo hecho y lo pendiente.
