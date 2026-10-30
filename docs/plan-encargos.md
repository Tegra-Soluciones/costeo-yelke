# Asignaciones de trabajo por paso del proyecto ("encargos" en el código)

Juan (o cualquiera con la vista) le encarga a una persona un paso de un proyecto, con
mensaje y fecha límite opcional. A esa persona le llega el aviso, lo ve en su Inicio y
en el proyecto, y el encargo **se marca solo** cuando el paso se atiende. Quien
encargó recibe el aviso de "terminado" y puede encargar el siguiente paso.

## Modelo

Un encargo es un **ToDo** de Frappe (también sale en el Escritorio, "Asignado a")
ligado al Costeo (`reference_type = Costeo`) con campos propios (patch v0_2_72):

| Campo | Para qué |
|---|---|
| `encargo_yelke` | marca los ToDo que son encargos de la app |
| `vista_yelke` | clave de `roles.VISTAS` (paso); vacío = encargo general del proyecto |
| `lote_yelke` | lote, en los pasos que van por lote |
| `mensaje_yelke` | la instrucción tal cual se escribió |
| `visto_yelke` | el paso tuvo algo pendiente después de encargarse (ver "Se marca solo") |
| `cierre_yelke` | Automático · Manual · Regresado · Quitado |
| `cerrado_en_yelke`, `nota_cierre_yelke` | cuándo y con qué nota se cerró |
| `avisos_yelke` | 1 = ya se avisó "vence hoy", 2 = ya se avisó "venció" |

`date` (fecha límite), `allocated_to`, `assigned_by` y `status` son los del ToDo.

## Quién puede

- **Encargar un paso**: quien tiene ese paso en Editar, o Dirección/pase libre.
- **A quién**: solo a quien tiene ese paso en Editar (no se encarga a quien no puede hacerlo).
  Encargo general: a cualquiera con al menos un paso.
- **Marcar listo / regresar**: la persona encargada (o pase libre).
- **Quitar, reasignar, recordar**: quien encargó (o pase libre).

## Se marca solo

Cada paso tiene una señal de "hay algo pendiente". El encargo se cierra solo cuando
ese paso **tuvo algo pendiente después de encargarse y ya no lo tiene**. Así un
encargo de un paso que todavía no arranca (cotizar con el costeo en borrador) no se
cierra antes de tiempo, y uno de un paso ya hecho se queda para cerrar a mano.

| Paso | Pendiente mientras… |
|---|---|
| Costear | el costeo no esté validado ni enviado a aprobación |
| Cotizar | no haya cotización validada o enviada a aprobación después de asignarse |
| Vender | no haya orden de venta validada o enviada a aprobación después de asignarse |
| Alta de productos | haya OV y queden artículos por dar de alta |
| Flujo de producción | el flujo no esté confirmado |
| Preparación | falte la solicitud de material o las órdenes a talleres validadas |
| Materia prima | haya material sin pedir o sin recibir (del lote, si tiene) |
| Talleres | falte el encargo de algún taller (del lote) o algo por enviar o recibir |
| Envíos | haya material por recibir, el lote no tenga encargos a taller, falte enviarles material o recibir su trabajo |
| Facturas de compra | alguna orden de compra del proyecto (material o maquila) no esté facturada completa |
| Entrega | con lote: falte la remisión validada del lote; sin lote: la OV no esté entregada |
| Facturar | la orden de venta no esté facturada completa |
| Tablero, OM, Flujo del lote, Reporte, General | a mano ("Listo") |

Se revisa: al guardar/validar/cancelar cualquier documento del proyecto (doc_events),
al abrir el proyecto o el Inicio, y cada hora (por si algo cambió por otra vía).
Proyecto cancelado → sus encargos abiertos se quitan solos (completado no: ahí sigue facturar, cobrar y el reporte).

## Momentos

1. **Proyecto nuevo**: desde Proyectos, "Encargar proyecto": título, cliente, persona,
   mensaje y fecha. Crea el costeo en borrador y el encargo de Costear.
2. **Cualquier paso**: botón "Encargos" en el proyecto → lista del proyecto + formulario
   (paso, lote si aplica, persona, mensaje, fecha). Por omisión, el paso que estás viendo.
3. **Al terminar**: a quien encargó le llega "Sandra terminó Costear" con el enlace al
   proyecto que abre el formulario con el **siguiente paso** ya elegido.
4. **No me toca / no puedo**: la persona lo regresa con motivo; a quien encargó le llega
   el aviso para reasignarlo.
5. **Reasignar / quitar / recordar** desde el proyecto, el Inicio o Dirección.
6. **Fecha límite**: aviso el día que vence y al vencer (a ambos); se pinta en rojo.
7. **Comentarios**: un comentario en el proyecto le avisa a la contraparte de sus encargos
   abiertos (encargado ↔ quien encargó).
8. **Escritorio**: el ToDo se ve en "Asignado a"; cerrarlo ahí cuenta como "Listo".

## Dónde se ve

- **Campana + correo**: cada aviso abre el proyecto en el paso exacto (no el Escritorio).
- **Inicio**: "Te encargaron" (abiertos, vencidos primero) y "Encargaste" (abiertos y
  terminados en los últimos 7 días).
- **Proyecto**: franja "Te encargaron esto" bajo el stepper y el panel "Encargos".
- **Panel de Dirección**: pestaña "Encargos" con los de todo el equipo, por persona.
- **Actividad del proyecto**: encargado, terminado, regresado, quitado.
