# 05 · Verificación, inicio, cierre y despliegue

El refactor no cambia comportamiento. Se demuestra con **niveles de verificación** que cada
sesión ejecuta según lo que tocó. Las herramientas las construye la Fase 1; antes de que existan
(sesiones R1–R6) cada sesión verifica lo que el plan le indique.

---

## 1. Niveles de verificación

| Nivel | Qué demuestra | Cómo | Tiempo aprox. | Disponible desde |
|---|---|---|---|---|
| **V1 · Estático** | compila, estilo, capas y contratos intactos | `python -m py_compile` de lo tocado · `ruff check` de lo tocado · `tools/refactor/verificar_capas.py` · `tools/refactor/contratos.py --verificar` | 1 min | R1 |
| **V2 · Lectura** | todas las lecturas devuelven exactamente lo mismo | `tools/refactor/restaurar_foto.sh` → `tools/refactor/fotos.py comparar` | 5–10 min | R3 |
| **V3 · Integral** | el flujo completo escribe igual: 20 verificaciones contables, candados y cancelaciones | `tools/refactor/restaurar_foto.sh` → `bench --site refactor.local run-tests --app costeo_yelke --module costeo_yelke.tests.integracion.test_flujo_completo` | 15–25 min | R4 |
| **V4 · Pantalla** | la SPA compila y se ve igual | `cd frontend && npm run build && npx vitest run && npx eslint src` + recorrido con el navegador contra `tests/linea_base/pantalla/` | 15 min | R6 |
| **V5 · Rendimiento** | no empeoró (o mejoró lo esperado) | `tools/refactor/rendimiento.py comparar` | 3 min | R5 |

**Qué nivel exige cada tipo de sesión** (cada sesión del plan lo repite):

| Tipo de sesión | Niveles |
|---|---|
| Herramientas y pruebas (Fase 1) | los que la sesión construye, más V1 |
| Mover código del servidor (Fase 2) | V1 + V2 + V3 |
| Limpieza por área (Fase 3) | V1 + V2 + V3 |
| Funciones críticas y rendimiento (Fase 4) | V1 + V2 + V3 + V5 |
| Permisos (Fase 5) | V1 + V3 + pruebas por rol |
| Pantalla (Fase 6) | V1 (si tocó Python) + V4; V2 si tocó el servidor |

### Reglas de las fotos de lectura (V2)

- Una diferencia **detiene la sesión.** No se "actualiza la foto" para que pase.
- Única excepción: valores que dependen de la fecha u hora de la corrida, o listas que
  provienen de un `set` (su orden cambia entre procesos). Se agregan a la lista de
  normalización de `fotos.py` **con una línea de justificación** y se anotan en `PROGRESO.md`.
  Si no estás seguro de que sea eso, pregunta al usuario.
- Las fotos se regeneran **solo** cuando el plan lo dice (p. ej. después de una sesión de
  corrección de bug autorizada por el usuario) y en un commit aparte que diga por qué.

### La foto congelada

- `refactor.local` se restaura desde un respaldo del sandbox tomado una sola vez (sesión U0) y
  guardado **fuera del repo** en `~/refactor-yelke/foto.sql.gz`.
- Antes de cada V2/V3 se restaura: así todas las corridas parten exactamente de los mismos datos,
  aunque el código haga `commit()` a mitad de proceso.
- Nunca se corren pruebas contra `sandbox.local` (el usuario lo usa a mano).

## 2. Protocolo de INICIO de sesión

1. Lee `README.md`, `00-CONTEXTO.md`, `01-ARQUITECTURA-DESTINO.md`, este archivo,
   `PROGRESO.md` y **tu sección** en `02-PLAN-SESIONES.md`. Si tu sesión lo indica, lee también
   `03-MAPA-SERVIDOR.md` o `04-MAPA-PANTALLA.md`.
2. En `PROGRESO.md` confirma que todas las sesiones de las que depende la tuya están
   **Terminadas** y que no hay una sesión **En curso**. Si la anterior quedó a medias, detente
   y avisa al usuario.
3. `git status` y `git log --oneline -5`. Confirma que el commit de la sesión anterior está en
   `HEAD`. Si hay archivos modificados que no son tuyos, **no los toques ni los incluyas**;
   si están en archivos que tu sesión necesita editar, detente y pregunta.
4. Corre la verificación **antes de cambiar nada** (los mismos niveles que exige tu sesión). Si
   la línea base ya falla, no es tu culpa pero tampoco puedes seguir: anótalo y pregunta.
5. Marca tu sesión como **En curso** en `PROGRESO.md` (fecha y hora).

## 3. Protocolo de CIERRE de sesión

1. Corre todos los niveles que exige tu sesión. Todo en verde.
2. Actualiza `PROGRESO.md`:
   - estado **Terminada**, fecha, hash del commit;
   - qué se hizo en 3 a 6 líneas;
   - **hallazgos** (bugs vistos y no corregidos, rarezas, decisiones tomadas);
   - métricas si aplica (líneas de `costeo_api.py`, consultas, tiempos);
   - si queda un **despliegue pendiente**, dilo.
3. Commit solo de tus rutas (ver reglas de git en `00-CONTEXTO.md`). Un commit por sesión es lo
   ideal; si la sesión tiene pasos separables (p. ej. "solo formato"), varios commits claros.
4. Responde al usuario con: qué se hizo, qué se verificó (con cifras), hallazgos, y **el ID de la
   siguiente sesión**, o el despliegue o decisión que haga falta antes.

## 4. Protocolo de FALLA

- Si una verificación falla y la causa no es evidente en dos intentos razonables:
  1. Deja el código como estaba antes de tu sesión (`git restore` de tus archivos o
     `git revert` de tu commit). **Nunca** `git reset --hard` ni `git checkout .`: borrarían el
     trabajo de otra sesión.
  2. Anota en `PROGRESO.md` qué falló, la salida relevante y qué intentaste.
  3. Marca la sesión como **Bloqueada** y pregunta al usuario.
- Prohibido "arreglar" una diferencia cambiando la prueba o la foto (salvo la excepción de la
  sección 1).
- Si encuentras un bug real del sistema: no lo corrijas dentro del refactor. Anótalo en
  Hallazgos; el usuario decide si se abre una sesión de corrección.

## 5. Despliegues (puntos de control)

El plan marca puntos **D1…D7**. En cada uno, la sesión que lo alcanza prepara y entrega al
usuario lo siguiente. **El usuario ejecuta todo.**

1. `git pull --rebase upstream main && git push upstream main` (en la Mac).
2. En el QNAP (`ssh erpnext-yelke`), respaldo previo:
   `docker exec cimix-yelke-backend-1 bench --site erp.yelke.com.mx backup --with-files`
3. `cd /share/ZFS18_DATA/Container/container-station-data/application/cimix-yelke && ./update_costeo.sh --site erp.yelke.com.mx --branch main --commit <sha>`
   (si el script se detiene en `bench migrate` por la incompatibilidad conocida de `crm`,
   aplicar el ajuste documentado y terminar a mano; ver la memoria del proyecto
   "Deploy a producción (QNAP)").
4. **Prueba de humo en producción (solo lectura):**
   - abrir la lista de costeos y 3 costeos en distintos pasos;
   - recorrer los 8 pasos de un costeo en producción (que carguen sin error);
   - Producir: Tablero, un lote abierto, bandeja de Envíos, bandeja de Facturas;
   - imprimir una OC de maquila y una cotización (vista previa);
   - abrir el reporte final de un costeo terminado;
   - revisar el **Error Log** de ERPNext: sin errores nuevos de `costeo_yelke`.
5. Si algo falla en producción: volver al commit anterior con el mismo script
   (`--commit <sha anterior>`). Como la Fase 2 no cambia datos ni agrega parches, revertir el
   código es suficiente.

En la Fase 2 no hay migraciones ni parches nuevos. Si una sesión necesita uno, es una señal de
que se está cambiando comportamiento: detente.
