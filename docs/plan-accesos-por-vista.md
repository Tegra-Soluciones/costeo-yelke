# Plan: accesos por vista (cada etapa, su rol)

*2026-10-28 · solo diseño, sin código.*

## 1. Objetivo

Que cada persona trabaje con **su** vista de la app:

- cada pantalla y cada etapa es una pieza independiente con su propio rol;
- cada pieza se da en dos niveles: **ver** (solo lectura) o **editar**;
- el usuario solo ve las etapas que le tocan (las demás no aparecen);
- su panel le muestra lo que tiene pendiente y lo lleva directo al lugar exacto del proyecto;
- las listas de documentos respetan los mismos accesos y llevan al proyecto cuando corresponde.

Todavía no se sabe qué le toca a cada quien. Por eso el plan **separa todo** en piezas chicas y deja la asignación como una decisión aparte, fácil de cambiar después.

## 2. Lo que ya existe (y se reutiliza)

| Pieza | Estado | Dónde |
|---|---|---|
| 9 roles por vista de Producción (tablero, preparación, OM, materia, flujo, talleres, envíos, facturas, entrega) | hecho | `roles.py` · `VISTAS_PRODUCCION` |
| Candado del servidor `requiere_vista()` | en 42 de 239 endpoints, solo escritura | `roles.py`, `api/*.py` |
| Menú de Producción filtrado y "No tienes acceso a …" | hecho | `puedeVer()` en CosteoDetailPage |
| Paneles en solo lectura ("La captura la hace Facturas") | hecho, solo en Producción | `PanelLateral` · prop `solo-lectura` |
| Aprobaciones: Revisor, Aprobador, Director, delegación | hecho | `api/aprobaciones.py` |
| Préstamo de permisos por fechas | hecho | `api/permisos_temporales.py` |
| Role Profiles en producción (Yelke Supervisor, Yelke Secundario, CEO) | existen | ver memoria "El Perfil de Rol manda" |

**Lo que falta:**

- Costear, Cotizar, Vender, Alta de productos, Flujo, Facturar, Reportar, Inicio, catálogos y listas no tienen roles.
- Ninguna lectura está restringida.
- No hay nivel "ver" separado de "editar".
- Los roles nuevos no dan permiso sobre los documentos de ERPNext, así que hoy solo funciona quien tiene System Manager.

## 3. Modelo propuesto

### 3.1 Vistas: el catálogo único

Una sola tabla en `roles.py` (`VISTAS`) es la fuente de verdad. La usan el servidor, la pantalla, el menú, el stepper, las listas y la pantalla de asignación. Cada vista declara:

```
clave       "materia"
etiqueta    "Materia prima"
grupo       "Producción"
rol_editar  "Producción Materia Prima Yelke"     (el que ya existe)
rol_ver     "Ver Producción Materia Prima Yelke" (nuevo)
pasos       paso del costeo / sub-vista de Producción donde vive
doctypes    {"Purchase Order": "editar", "Purchase Receipt": "editar", "Supplier Quotation": "editar", ...}
listas      rutas de lista que habilita (/ordenes-compra, /recibos-compra)
```

**Editar incluye ver.** Las 9 claves de Producción y sus roles se conservan tal cual, porque ya están en 42 candados y en los perfiles de producción.

### 3.2 Catálogo propuesto (≈ 22 vistas)

| Grupo | Vista | Qué cubre |
|---|---|---|
| **Comercial** | Costear | paso 0: productos, materiales, etapas, márgenes |
| | Cotizar | paso 1: cotización, envío, rechazo |
| | Vender | paso 2: orden de venta, OC del cliente, cancelar OV |
| | Precios | precios acordados, tabla por volumen |
| **Ingeniería** | Alta de productos | paso 3 y catálogo de Productos |
| | Flujo de producción | paso 4: confirmar y revertir el flujo |
| | Plantillas | plantillas de costeo |
| **Producción** (ya existen) | Tablero · Preparación · Orden de manufactura · Materia prima · Flujo del lote · Talleres · Envíos · Facturas de compra · Entrega | paso 5 por dentro |
| **Finanzas** | Facturar | paso 7: factura de venta |
| | Reporte final | paso 8: rentabilidad y su PDF |
| | Indicadores financieros | Inicio con ventas, márgenes y utilidad |
| **Dirección** | Panel de Dirección | proyectos y resumen de toda la empresa |
| **Administración** | Accesos | asignar vistas a usuarios y perfiles (§6) |

Las aprobaciones **no cambian** y son otra dimensión. La vista dice *qué ves y capturas*; los roles de aprobación (Revisor, Aprobador, Director, Aprobador de precios) dicen *qué validas*. Un comprador con "Materia prima · editar" arma la OC y la manda a aprobar; validarla sigue siendo del Aprobador.

### 3.3 Dos niveles: ver y editar

| | Ver | Editar |
|---|---|---|
| La vista aparece en el menú y el stepper | sí | sí |
| Ve documentos, montos, PDF | sí | sí |
| Botones de crear, guardar, validar, enviar | ocultos | sí |
| Campos | solo lectura | editables |
| Paneles laterales | franja "Solo lectura" (mecanismo actual) | normal |
| Servidor | lecturas permitidas, escrituras bloqueadas | todo |

Son dos roles por vista y no un rol más una bandera, porque así lo maneja Frappe sin inventar nada. Funciona con Role Profiles, con el préstamo de permisos y con la delegación tal como ya están.

### 3.4 Perfiles por puesto

La asignación real se hace con **Role Profiles por puesto** ("Compras", "Almacén", "Ventas", "Finanzas", "Dirección"…), armados con vistas. A cada usuario se le asigna su perfil. Cambiar lo que ve todo un puesto se hace en un solo lugar.

Mientras se decide quién ve qué, todos se quedan con un perfil transitorio "Acceso completo Yelke" para que nadie se quede bloqueado el día del deploy.

## 4. Qué cambia en cada parte de la app

### 4.1 El costeo (stepper y pasos)
- **El stepper solo muestra los pasos permitidos.** Los demás desaparecen (no se ven bloqueados), pero el avance del proyecto se sigue viendo con una etiqueta de estado ("En producción").
- Si se abre un costeo en un paso no permitido (por un enlace o porque ahí se quedó), cae en el primer paso permitido.
- Con nivel **ver**, la barra de acciones de abajo se queda vacía y los campos van en solo lectura. Es el mismo patrón de Producción, llevado a todos los pasos.
- Dentro de Producción nada cambia: ya funciona así.

### 4.2 Proyectos (lista de costeos)
- Se ven los proyectos donde el usuario tiene al menos una vista activa.
- Cada renglón dice qué le toca ahí ("2 OC por recibir") y abre directo ese paso.
- *Decisión pendiente:* ¿un usuario de Almacén ve todos los proyectos o solo los que tienen algo para él?

### 4.3 Mi panel (Inicio + Dirección integrados)
"Inicio" se vuelve el panel personal de cada quien:

1. **Mis pendientes**: por cada vista con nivel editar, lo que está esperando. Ya existe casi todo en las bandejas y en el tablero:
   - Comprar: solicitudes sin OC, OC sin recibir.
   - Almacén: envíos pendientes y regresos.
   - Talleres: encargos por enviar o recibir.
   - Facturas: por capturar y en borrador.
   - Entrega: lotes terminados sin remisión.
   - Ventas: cotizaciones por enviar.
   - Costear: borradores propios.
2. **Por aprobar**, si tiene rol de aprobación (lo que ya hace la bandeja de Dirección).
3. **Me regresaron** (ya existe).
4. **Proyectos recientes** en los que participó.

Cada renglón lleva al lugar exacto: costeo, paso, lote, taller y panel abierto, usando las direcciones de `useProduccionRuta`, que ya lo permiten.

Quien tiene "Panel de Dirección" ve además el resumen de la empresa y todos los proyectos, como hoy en `/direccion`. Las cifras financieras siguen detrás de "Indicadores financieros".

### 4.4 Listas de documentos
Hoy son pantallas sueltas, unas abren una página propia y otras mandan a pasos viejos (el "paso 6" de remisiones ya no existe). Propuesta:

- **Cada lista pertenece a una vista.** OC → Materia prima / Talleres; Recibos → Envíos; Remisiones → Entrega; Facturas de compra → Facturas; Cotizaciones → Cotizar; OV → Vender; Facturas de venta → Facturar; Solicitudes de material → Preparación. Solo aparece en el menú si se tiene esa vista.
- **Al abrir un documento de un proyecto, lleva al proyecto en el lugar exacto** (por ejemplo, el lote y el taller de esa OC) con su panel abierto. Si en el proyecto no tiene esa vista pero sí la lista, se abre el documento en solo lectura en un panel lateral sobre la misma lista, sin salir de ella.
- **Documentos sin proyecto** (una OC o una OV hecha a mano): se abren en el panel lateral de la lista. Las 4 páginas de detalle que hay hoy (Cotización, OV, OC, Factura de venta) se pasan a ese panel para que todo funcione igual.
- **Crear desde la lista** ("Nueva OC") solo con nivel editar. *Decisión pendiente:* ¿se permite crear documentos fuera de un proyecto?
- Se corrigen los enlaces a pasos viejos (6, 5 genérico) para que usen la ruta de Producción.

### 4.5 Menú lateral
Se arma solo con el catálogo: muestra los grupos y las pantallas a las que el usuario tiene acceso. "Escritorio ERPNext" solo aparece para administración.

## 5. El servidor

> **Acotado por la decisión del 2026-10-28 (§9):** por ahora no se auditan los endpoints; solo candados de escritura en las etapas nuevas. Lo de abajo queda como referencia para cuando se quiera cerrar.

Ocultar pantallas no basta: el dato también se puede pedir directo al servidor.

1. **Inventario de endpoints.** Los 239 endpoints `@frappe.whitelist` se clasifican en una tabla (endpoint → vista → lee/escribe). Hoy solo 42 tienen candado, y solo para escritura.
2. **Candados:**
   - `requiere_vista(clave, nivel="editar")` en toda escritura.
   - Nuevo `requiere_vista(clave, nivel="ver")` en las lecturas con datos sensibles: costos, márgenes, precios, facturas, reporte final.
   - Los endpoints compartidos aceptan cualquiera de sus vistas.
3. **Permisos de los documentos de ERPNext (DocPerm).**
   - El catálogo declara qué doctypes lee o edita cada vista, y un patch genera los permisos de cada rol: ver → read/print; editar → read/write/create (y submit/cancel donde aplique, sin saltarse las aprobaciones).
   - Hace falta porque la app usa `frappe.client.get_list` y `get_value` en 25 lugares, y el escritorio y los PDF también los piden. Sin esto, un usuario sin System Manager no ve nada.
   - *Trampa conocida:* en cuanto un doctype tiene un permiso personalizado, Frappe ignora los de fábrica. El patch los copia primero, con `frappe.permissions.add_permission`, que lo hace solo.
4. **`ignore_permissions`.** Se usa en 144 lugares. Se revisan los que **leen** para que no entreguen datos de una vista que el usuario no tiene. Los que escriben quedan detrás de `requiere_vista`.
5. **Un endpoint `mis_accesos()`** devuelve `{clave: "ver" | "editar"}` del usuario actual (con préstamos y delegación incluidos). Es lo único que consulta la pantalla.

## 6. Asignar accesos sin pelearse con ERPNext

Pantalla **Accesos** (vista de Administración):

- Una matriz con **puestos (perfiles) en filas y vistas en columnas**. Cada celda es — / Ver / Editar.
- Al guardar, se escriben los roles del Role Profile y se re-guardan sus usuarios. Así se evita la trampa del perfil que reemplaza roles.
- Debajo, los usuarios con su perfil y los préstamos activos.
- **"Ver como…"**: elegir un usuario o perfil y abrir la app tal como la vería. Es indispensable para ir probando las asignaciones sin pedirle a cada persona que entre a revisar.

Todo eso se puede hacer en ERPNext (Role Profile, Role, User), pero son tres pantallas y nombres de rol largos. La matriz lo deja en un solo lugar.

## 7. Casos que hay que cuidar

- **Director y Supervisor:**
  - Hoy tienen pase libre en Producción.
  - Propuesta: Director ve todo, edita lo que se le asigne y aprueba. Supervisor queda como respaldo con todo en editar.
  - System Manager se queda solo para el desarrollador.
- **Montos sensibles:** ¿Almacén y Talleres deben ver precios y costos? Si no, hace falta una capacidad aparte, "Ver importes", que oculte montos en sus vistas. Es más trabajo y conviene decidirlo antes.
- **Notificaciones:** los avisos y recordatorios que hoy van por rol deben ir a quien tenga la vista con nivel editar.
- **Correo y WhatsApp:** enviar un documento cuenta como editar.
- **PDF:** imprimir cuenta como ver (permiso `print`).
- **Archivos adjuntos:** heredan el permiso del documento; revisar que sigan funcionando.
- **Préstamo de permisos y delegación:** ya trabajan con roles, así que con vistas siguen funcionando.
- **Caché:** los roles se leen de Redis; después de asignar hay que limpiar la caché del usuario (la pantalla de Accesos lo hace).

## 8. Fases (versión original — ver §12, ajustada)

| Fase | Contenido | Tamaño |
|---|---|---|
| 0 | Decidir el catálogo de vistas y las preguntas de §9; mockup de "Mi panel" y de la matriz de Accesos | chica |
| 1 | Catálogo en `roles.py`, roles "Ver …" y de las etapas nuevas, `mis_accesos()`, perfil transitorio "Acceso completo Yelke" (nadie pierde acceso) | chica |
| 2 | Pantalla: menú, stepper, guardia de rutas y modo solo lectura en todos los pasos | media |
| 3 | Servidor: inventario de los 239 endpoints, candados de ver/editar, revisión de `ignore_permissions` en lecturas | **grande** |
| 4 | DocPerm generados desde el catálogo (patch) y prueba con usuarios sin System Manager | media |
| 5 | Mi panel (pendientes por vista, aprobaciones, enlaces al lugar exacto) | media |
| 6 | Listas: dueño por vista, panel lateral, enlaces corregidos | media |
| 7 | Pantalla de Accesos + "Ver como…" | media |
| 8 | Pruebas por perfil (Playwright: cada perfil ve y puede exactamente lo suyo) y manual | media |

Cada fase se puede subir sola sin romper nada: hasta que se quite el perfil transitorio, todos siguen viendo todo.

## 9. Decisiones tomadas (2026-10-28)

| # | Pregunta | Decisión |
|---|---|---|
| 1 | Catálogo de vistas | Aprobado el enfoque (§3.2) |
| 2 | ¿Todos los proyectos o solo los suyos? | **Todos** los proyectos, cada quien con sus etapas |
| 3 | ¿Crear documentos fuera de un proyecto? | **Sí**, desde las listas, con nivel editar de su vista |
| 4 | ¿Quién ve dinero? | **Todos**, por ahora (puede cambiar; queda previsto en §7) |
| 5 | Director | **Ve y puede todo**; en la práctica aprueba y comenta |
| 6 | ¿Usan el Escritorio ERPNext? | **Sí**, para cargar proveedores, clientes, artículos, etc. → roles de ERPNext por puesto (§10) y reglas de captura (§11) |
| — | Servidor | **No auditar los 239 endpoints por ahora.** Lo que no se ve no se usa (usuarios no técnicos). Se conservan los candados de escritura que ya existen y se agregan solo en lo nuevo |

Con eso la **fase 3 se reduce** a: candados de escritura en los pasos que hoy no tienen ninguno
(Costear, Cotizar, Vender, Facturar) y nada en lecturas. El riesgo aceptado: alguien que sepa
llamar a la API directo podría leer datos de etapas que no ve.

## 10. Roles dentro de ERPNext (Escritorio)

Los mismos roles de vista dan permisos sobre los documentos de ERPNext. El patch los genera
desde el catálogo; aquí lo que cada vista puede hacer en el Escritorio:

| Doctype (Escritorio) | Ver | Crear / editar | Desde la vista |
|---|---|---|---|
| Cliente, su dirección y contacto | todas | **Vender**, **Cotizar** | Comercial |
| Proveedor, su dirección, contacto y cuenta bancaria | todas | **Materia prima**, **Talleres** | Producción |
| Transportista (proveedor de paquetería) | todas | **Envíos**, **Materia prima** | Producción |
| Artículo, grupo de artículo, UDM, BOM | todas | **Alta de productos** | Ingeniería |
| Lista de precios / precio de artículo | Comercial, Finanzas | **Precios** | Comercial |
| Cotización · Orden de venta | Comercial, Finanzas | **Cotizar** · **Vender** | Comercial |
| Solicitud de material · Plan de producción | Producción | **Preparación** | Producción |
| Orden de compra · Recibo de compra | Producción, Finanzas | **Materia prima** · **Envíos** | Producción |
| Orden / recibo de subcontratación · Movimiento de material | Producción | **Talleres** · **Envíos** | Producción |
| Remisión | Producción, Comercial | **Entrega** | Producción |
| Factura de compra | Producción, Finanzas | **Facturas de compra** | Producción |
| Factura de venta · Póliza · Pago | Finanzas | **Facturar** | Finanzas |
| Almacén, compañía, cuentas contables, plantillas de impuestos | Finanzas | **solo Supervisor / Director** | Administración |

- **Validar (submit) y cancelar** siguen detrás de las aprobaciones (candado único en `before_submit`): tener "editar" no basta para validar un documento con aprobación.
- **Borrar**: solo Supervisor y Director. Un documento cancelado no se borra (ya existe el candado de folios).
- **Director y Supervisor**: todo.
- **Ver todo el dinero**: todas las vistas con "ver" leen montos (decisión 4).

## 11. Reglas de captura (para que todo quede registrado igual)

Se aplican al guardar, **en la app y en el Escritorio por igual** (hooks del servidor, no de la
pantalla), sobre lo que ya hace `overrides/uppercase_master.py`. Se corrige solo lo que tiene una
sola forma correcta; si no se puede adivinar, se detiene con un mensaje claro en español.

**Para todo texto de nombre:** se quitan espacios al inicio y al final, se juntan los dobles
("JESUS " → "JESUS") y se pasa a MAYÚSCULAS conservando acentos y Ñ (el SAT los respeta).

| Documento | Campo | Regla | Hoy en tus datos |
|---|---|---|---|
| **Cliente / Proveedor** | Razón social, nombre comercial | MAYÚSCULAS + espacios | nombre comercial no se pasaba a mayúsculas |
| | RFC | MAYÚSCULAS, sin espacios ni guiones; formato válido (12 moral / 13 física, o genérico XAXX010101000 / XEXX010101000); doble captura (ya existe) | sin validar formato |
| | RFC duplicado | no se puede dar de alta otro cliente (o proveedor) con el mismo RFC, salvo los genéricos | — |
| **Dirección** | Título, calle, colonia, ciudad | MAYÚSCULAS + espacios | ya en mayúsculas |
| | Estado | **lista cerrada de las 32 entidades** (desplegable); se corrigen solas las formas conocidas: QRO / QUERETARO → QUERÉTARO, EDO DE MEXICO / MEXICO → ESTADO DE MÉXICO, CDMX / DF → CIUDAD DE MÉXICO… | 15 formas distintas, incluso "MOROLEON" (ciudad) |
| | Código postal | 5 dígitos (México) | — |
| | País | México por omisión | — |
| | Correo | minúsculas y formato válido | — |
| | Teléfono | 10 dígitos, sin +52, guardado como `442 467 8939` | con y sin espacios |
| | Liga | toda dirección ligada a un cliente, proveedor o la compañía | — |
| **Contacto** | Nombre, apellidos, puesto | MAYÚSCULAS + espacios | "JESUS " con espacio |
| | Correo(s) | minúsculas, formato válido | "Angeles.Mares@…" |
| | Teléfono(s) y celular | igual que en dirección | mezcla de formatos |
| | Liga | todo contacto ligado a un cliente o proveedor (no huérfanos) | — |
| **Cuenta bancaria** | CLABE | 18 dígitos + dígito verificador; doble captura (ya existe) | sin dígito verificador |
| | Tarjeta | 16 dígitos | — |
| **Artículo** | Código, nombre | ya en MAYÚSCULAS | ya existe |
| | Descripción | espacios al inicio y al final | — |
| **Orden de venta** | OC del cliente (`po_no`) | MAYÚSCULAS, sin espacios sobrantes | — |
| **Factura de compra** | Folio del proveedor (`bill_no`) | MAYÚSCULAS, sin espacios | — |
| **Almacén, grupos, marca, territorio** | Nombre | ya en MAYÚSCULAS | ya existe |

**Datos que ya existen:** un patch los normaliza una vez (estados, teléfonos, correos, espacios),
igual que se hizo con las mayúsculas. Lo que no se pueda corregir solo (un estado que es una
ciudad, un CP de 4 dígitos) sale en una lista para revisarlo a mano, sin bloquear nada.

## 12. Fases ajustadas

| Fase | Contenido | Tamaño |
|---|---|---|
| 1 | Catálogo de vistas, roles "Ver …" y de las etapas nuevas, `mis_accesos()`, perfil transitorio "Acceso completo Yelke" | chica |
| 2 | Pantalla: menú, stepper, guardia de rutas, modo solo lectura en todos los pasos | media |
| 3 | Candados de escritura solo en Costear, Cotizar, Vender y Facturar (sin auditoría de lecturas) | chica |
| 4 | Permisos de ERPNext por vista (§10), generados por patch; prueba con usuarios sin System Manager | media |
| 5 | Reglas de captura (§11) + patch que normaliza lo existente + lista de lo que no se pudo | media |
| 6 | Mi panel | media |
| 7 | Listas: dueño por vista, panel lateral, crear desde la lista, enlaces corregidos | media |
| 8 | Pantalla de Accesos + "Ver como…" | media |
| 9 | Pruebas por perfil y manual | media |

Las reglas de captura (fase 5) no dependen de las demás y se pueden hacer primero.
