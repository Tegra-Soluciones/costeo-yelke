# 00 · Contexto general

Lectura obligatoria al inicio de **cada** sesión del refactor. Supone que no recuerdas nada
de sesiones anteriores: todo lo que necesitas saber del sistema, del entorno y de las reglas
está aquí o en los documentos que se enlazan.

---

## 1. Qué es el sistema

**Costeo Yelke** es una app de Frappe (`costeo_yelke`) instalada sobre ERPNext para Yelke, un
fabricante de uniformes que **maquila** (subcontrata) casi toda su producción con talleres
externos. La app cubre el ciclo completo de un pedido:

```
Costear → Cotizar → Vender (OV) → Alta de productos → Flujo de producción →
Producir [Plan · Materia prima · Orden de manufactura · Talleres · Lotes · Envíos · Facturas] →
Enviar (remisión) → Facturar → Reporte final (estimado vs. real)
```

- El **Costeo** (doctype propio) es el documento central: productos, materiales, etapas
  (operaciones/servicios de taller), tallas, variantes de talla, overhead y margen.
- Todo lo demás son **documentos nativos de ERPNext** que la app crea y orquesta:
  Quotation, Sales Order, Production Plan, Material Request, Purchase Order (materia prima y
  de subcontratación), Subcontracting Order (= "encargo a taller"), Stock Entry
  "Send to Subcontractor" (= "envío"), Subcontracting Receipt (= "recibo de taller"),
  Purchase Receipt, Purchase Invoice, Delivery Note (= "remisión"), Sales Invoice,
  Journal Entry (pólizas de flete y de overhead).
- La pantalla es una **SPA en Vue 3** (`frontend/`) servida en `/costeo-app`, que llama a los
  métodos `@frappe.whitelist()` del servidor por `/api/method/costeo_yelke.api.<modulo>.<función>`.

Dos compañías en producción: **YELKE TEXTILES** (YT) y **SUS INDUSTRIAL**. En el sandbox la
compañía de pruebas es **YELKE PRUEBAS** (YP).

## 2. Versiones y entornos

| Entorno | Dónde | Notas |
|---|---|---|
| Código | `/Users/trabajo/Trabajo/frappe-bench-v15/apps/costeo_yelke` | rama `main`, remoto `upstream` = `Tegra-Soluciones/costeo-yelke` |
| Bench | `/Users/trabajo/Trabajo/frappe-bench-v15` | Frappe **15.120** / ERPNext **15.104**; Python `env/bin/python`; comando `bench` global |
| Sandbox | sitio `sandbox.local`, `http://127.0.0.1:8001` (cabecera `Host: sandbox.local`) | datos de prueba que **el usuario también usa** a mano |
| Sitio del refactor | sitio `refactor.local` (lo crea la sesión U0) | copia congelada ("foto") del sandbox; aquí corren TODAS las pruebas |
| Producción | QNAP, Docker, sitio `erp.yelke.com.mx` | Frappe **15.87** / ERPNext **15.85**. **Solo el usuario despliega.** |

- **Producción tiene versiones más viejas que el bench local.** El refactor no debe introducir
  ninguna API de Frappe/ERPNext que no exista en 15.87/15.85. Regla práctica: no se agregan
  llamadas nuevas al framework; se mueve el código que ya existe.
- El sandbox y `refactor.local` **comparten el mismo código** (misma carpeta de app). Un cambio
  en el código afecta a los dos.
- Los scripts de Python que hacen `frappe.init(...)` deben correrse **desde la carpeta
  `sites/`** (los logs usan rutas relativas; desde otra carpeta truena con
  `FileNotFoundError: .../logs/database.log`).

## 3. Estructura actual del código (al 15-oct-2026, commit `519ce25` + cambios de seguridad)

| Archivo | Líneas | Qué tiene |
|---|---|---|
| `costeo_yelke/api/costeo_api.py` | 11,187 | **El monolito**: 247 funciones (115 expuestas), 9 constantes. Ventas, producción, compras, talleres, facturas, reportes, impresión. |
| `costeo_yelke/costeo_yelke/doctype/costeo/costeo.py` | 1,963 | Controlador del Costeo: cálculos, estados de pieza (`_resolve_piece_states`, `_ops_prenda_armada`), métodos `pp_*` |
| `costeo_yelke/api/item_api.py` | 1,109 | Artículos, UDM, precios, precio acordado |
| `costeo_yelke/api/{quotation,sales_order,sales_invoice,purchase_order}_api.py` | 330–450 c/u | Backend de las **pantallas independientes** (duplican lo que hace el costeo) |
| `costeo_yelke/api/{contabilidad,fletes,tallas_ov,tallas_lote,om_general,impresion,documentos_api,costeo_template_api,bank_account_api}.py` | 30–480 c/u | Hooks contables, fletes, tallas, OM general, impresión |
| `costeo_yelke/hooks.py` | 362 | `doc_events`, `before_request` (candado de uso interno), override de `make_purchase_order`, scheduler |
| `costeo_yelke/security.py` | 82 | Candado: solo usuarios internos (System User) llaman `costeo_yelke.*` |
| `costeo_yelke/roles.py` | 166 | Roles Yelke, vistas de Producción, `requiere_vista`, `puede_aprobar_documentos` |
| `costeo_yelke/patches/` | 3,020 | 84 parches. **Algunos importan funciones de `costeo_api` — nunca se editan parches viejos.** |
| `frontend/src/pages/CosteoDetailPage.vue` | 9,116 | **El componente gigante**: los 8 pasos del costeo. Template 1–3264, script 3266–9064. |
| `frontend/src/composables/useProduccion.js` | 2,125 | Lógica de Producción (ya extraída; se inyecta con `provide("produccion")`) |
| `frontend/src/pages/*DetailPage.vue` | 700–1,450 c/u | Pantallas independientes de Cotización, OV, Factura, OC, Producto |
| `costeo_yelke/costeo_yelke/doctype/costeo/costeo.js` + `modules/*.js` | ~8,300 | Formulario del Costeo en el escritorio de ERPNext (anterior a la SPA) |
| `costeo_yelke/public/js/purchase_order_manufacturing_order.js` | 829 | OM en el formulario de la OC del escritorio |
| `costeo_yelke/public/costeo-app/` | — | **Build compilado de la SPA, versionado en git** (no se compila en producción) |

Pruebas automatizadas versionadas: **ninguna** (solo `test_costeo.py` vacío). CI: **no hay**.

## 4. Cómo se conecta todo

- **Pantalla → servidor:** `call("costeo_yelke.api.costeo_api.validar_documento", {...})`
  (helper en `frontend/src/utils/frappe.js`). La pantalla llama ~100 métodos distintos de
  `costeo_api` y otros ~80 de los demás módulos. **Estas rutas son contrato: no pueden cambiar.**
- **Eventos de documento:** `hooks.py → doc_events` apunta a rutas con punto, p. ej.
  `costeo_yelke.api.costeo_api.validar_oc_cliente_adjunta` (before_submit de Sales Order).
- **Candado de uso interno:** `security.guard_internal` (before_request) rechaza a quien no sea
  System User en `/api/method/`, `/api/v1/method/`, `/api/v2/method/` y
  `/api/v2/method/<Doctype>/<método>`.
- **Permisos:** casi todos los métodos usan `ignore_permissions=True` **a propósito**: los roles
  de Yelke (vistas de Producción) no tienen permisos de doctype. Los candados reales son
  `roles.requiere_vista(...)`, `puede_aprobar_documentos()`, `puede_revisar_documentos()` y los
  `doc_events`. No se agregan `frappe.has_permission` hasta la Fase 5 (requiere la matriz de
  permisos del usuario).

## 5. Comandos que vas a usar

```bash
# Python del bench (correr scripts SIEMPRE desde sites/)
cd /Users/trabajo/Trabajo/frappe-bench-v15/sites && ../env/bin/python <script.py>

# Pruebas (las crea la Fase 1)
bench --site refactor.local run-tests --app costeo_yelke --module <modulo.de.prueba>

# Restaurar la foto congelada antes de una corrida (lo crea R2)
tools/refactor/restaurar_foto.sh

# Compilar la SPA (escribe en costeo_yelke/public/costeo-app/)
cd frontend && npm run build

# Estilo
ruff check <rutas>          # configuración en pyproject.toml (line-length 110)
```

- **RTK**: hay un hook que reescribe algunos comandos de shell para ahorrar salida (p. ej.
  `grep` → `rtk grep`). Si un comando con banderas poco comunes falla raro (como `grep -h`),
  usa `rtk proxy <comando>` o `command grep`.
- **zsh**: en un `for f in "d Lote 2"` el argumento llega como UNA sola palabra. Pasa los
  argumentos por separado.

## 6. Reglas de trabajo (no negociables)

1. **Nunca `git add -A` ni `git add .`.** Puede haber otra sesión de Claude trabajando en la
   misma carpeta. Haz `git status` al empezar y al terminar; agrega **solo tus rutas**;
   revisa `git show --stat HEAD` después del commit.
2. **Commits locales; `push` solo si el plan o el usuario lo indican.** Antes de un push:
   `git pull --rebase upstream main`. Mensajes en español, prefijo `refactor:` / `test:` /
   `chore:`, y la línea de coautoría que indique el sistema.
3. **Nada en producción.** No despliegues ni escribas en el QNAP. Si el plan marca un
   despliegue, prepara el comando exacto y entrégaselo al usuario.
4. **Nunca contraseñas en el chat ni en archivos del repo.** Si algo requiere la contraseña de
   root de MariaDB o de un usuario, el usuario corre ese comando.
5. **No se cambia comportamiento en una sesión de refactor.** Si encuentras un bug, anótalo en
   `PROGRESO.md` (sección "Hallazgos") y sigue; se corrige en una sesión aparte con permiso del
   usuario. Excepción: un bug que impide que pasen las pruebas de la línea base → detente y
   pregunta.
6. **No toques:** `costeo_yelke/www/manual-costeo.html` (manual, 4.8 MB), `docs/entrega/`,
   parches existentes en `costeo_yelke/patches/`, ni los datos del sandbox salvo que la sesión
   lo diga.
7. **Si el plan no cuadra con el código** (una función que no existe, un archivo que cambió),
   **detente y pregunta.** No improvises un plan nuevo.
8. **Una sesión = un ID del plan.** No adelantes trabajo de la siguiente sesión.

## 7. Reglas de negocio que el refactor NO puede romper

Las pruebas de la Fase 1 cubren la mayoría; aun así, si una sesión toca código cercano a estas
reglas, léelas antes.

1. **Prendas vs. piezas.** Con el modelo por pieza, una prenda = N piezas (camisola: 7
   unidades = 6 piezas + puños ×2). **Todo lo que va a la pantalla se expresa en PRENDAS**; la
   conversión sale de `fg_item_qty / prendas` de la propia OC (`_piezas_por_prenda_de_po`).
   El error recurrente histórico es sumar piezas como si fueran prendas (×7).
2. **UDM de compra vs. de inventario.** `Material Request Item.qty` está en UDM de **compra**
   (1 Mazo = 1,728 piezas); `stock_qty` en UDM de inventario. Nunca se mezclan.
3. **Residuo decimal en BOM de piezas.** BOM a 9 decimales y holguras de 3 decimales en
   transferencia y recibo (`_ajustar_a_existencia`, `_necesidad_exacta_sco`). No se "limpia"
   redondeando.
4. **Precio en pieza portadora.** El precio del servicio va completo en una pieza y las demás en
   $0. A Yelke le importa el monto exacto al taller y la valuación de materia prima/mermas, no
   la valuación por pieza.
5. **Sobrantes en el taller.** La transferencia redondea hacia arriba; el sobrante se descuenta
   solo en la siguiente (`_descontar_lo_que_ya_tiene_el_taller`) y al final se devuelve
   (`sub_devolver_material`). Solo se toca el saldo **libre** (`_comprometido_en_talleres`).
6. **Lote = un encargo por proveedor con cantidad por producto** (`lote_abrir`). Un producto sin
   saldo pendiente se omite en silencio.
7. **La OC de subcontratación cubre todos los lotes**; el encargo a taller (SCO) es por lote.
   Las tallas del lote viven en el SCO (`tallas_lote.py`). Regla: suma por talla == OV exacto;
   total del producto ±5% contra el plan (`_QTY_TOLERANCIA_PCT`).
8. **Paradas, ramas y punto de ensamble** (`_lote_paradas`, `_ramas_por_pieza`,
   `costeo.py::_ops_prenda_armada`). `parada_id` es un hash de las piezas. La búsqueda de OC por
   `fg_item` **se acota a las OC del costeo** (dos costeos con el mismo producto comparten
   `fg_item`). `_lote_paradas` **no se modifica sin instrucción explícita del usuario**: en el
   refactor solo se mueve tal cual (y en la Fase 4 se reestructura con pruebas de foto).
9. **Entregas múltiples por parada** (`parada_registrar_entrega`): la parada terminal tiene
   tope; las intermedias no.
10. **Validación simple y doble.** Costeo: rol Aprobador. Orden de compra: Revisor
    (`marcar_revisado_documento`) y luego Aprobador. `validar_documento` y
    `cancelar_documento` solo aceptan `DOCTYPES_FLUJO_COSTEO` y exigen la vista de Producción
    que corresponda.
11. **OC del cliente obligatoria** para validar la OV (`validar_oc_cliente_adjunta`,
    before_submit). Todo degrada si la columna no existe (`frappe.db.has_column`).
12. **PDF obligatorio** en toda factura de compra y de venta (`factura_pdf`; XML opcional).
13. **Factura de maquila: una por OC de subcontratación**, y solo con la OC 100% recibida
    (bandeja de Facturas).
14. **Fletes:** captura obligatoria en recibos (`validar_envio_capturado_recibo`), folio CFDI
    obligatorio en la factura del flete, póliza de flete en la remisión, retención de IVA en
    paqueterías.
15. **Overhead:** póliza al validar la factura de venta (`_contabilizar_overhead_factura`), una
    sola vez; al cancelar la factura se cancela la póliza.
16. **Documentos cancelados no se borran** (`contabilidad.bloquear_borrado_cancelado`; la llave
    es `frappe.flags.permitir_borrar_cancelados`).
17. **Producto repetido en la OV:** `_sales_order_item` solo amarra si hay exactamente una línea.
18. **Variante de talla = otro Costeo Producto** (`variante_talla_de` es solo informativo).
19. **Valuación de inventario: Costo Promedio Móvil.** Maestros en MAYÚSCULAS
    (`uppercase_master`).
20. **`mr_dividir_en_lotes` hace `frappe.db.commit()` explícito.** En general: antes de
    probar una función que escribe, busca `frappe.db.commit()` en toda su ruta. Un rollback
    después de un commit **no deshace nada**.
21. **Enviar por correo/WhatsApp solo documentos validados** (`exigir_documento_enviable`).

## 8. Trampas técnicas conocidas

- **Custom DocPerm:** si un doctype tiene al menos una Custom DocPerm, Frappe ignora las
  DocPerm estándar.
- **Role Profile:** al guardar un usuario con perfil, sus roles se reemplazan por los del perfil.
  `frappe.get_roles()` lee de Redis: verifica contra la tabla `Has Role`.
- **Borrar un Custom Field no tira la columna:** `has_column` sigue dando True.
- **Amend:** `no_copy` se ignora al corregir (amend) y `_validate_links` corre antes de
  `before_insert`.
- **Orden de cancelación** de un flujo completo: factura de compra → recibo de taller → envío →
  encargo → recibo de compra → OC → solicitud → plan → OV → cotización.
- **Fotos de lectura:** algunos resultados traen listas cuyo orden cambia entre procesos
  (vienen de `set`). Comparar primero exacto; si solo difiere el orden, investigar antes de
  aceptar.

## 9. Glosario

| Término | Significado |
|---|---|
| OV | Orden de Venta (Sales Order) |
| OC | Orden de Compra (Purchase Order). "OC de maquila" = `is_subcontracted=1` |
| SCO / encargo | Subcontracting Order: lo que se le encarga a un taller en un lote |
| SCR / recibo de taller | Subcontracting Receipt |
| Envío / transferencia | Stock Entry "Send to Subcontractor" |
| MR / solicitud | Material Request |
| Plan | Production Plan ligado a una OV |
| OM | Orden de Manufactura: ficha de confección que se imprime para el taller |
| Lote (`lote_ref`) | Tanda de producción ("Lote 1", "Lote 2") |
| Parada | Paso de un taller dentro de un lote (`parada_id` = hash) |
| Rama | Recorrido de UNA pieza por los talleres |
| Pieza / prenda | Pieza = parte cortada (frente, manga…); prenda = producto terminado |
| `fg_item` | Artículo que produce un renglón de OC de maquila (pieza o prenda) |
| Remisión | Delivery Note |
| Vista | Rol de Producción que habilita una sección (`roles.VISTAS_PRODUCCION`) |
| Foto | Respaldo congelado del sandbox restaurado en `refactor.local` |
| Foto de lectura | Respuesta guardada de un método de lectura para compararla después |
