/**
 * Estado de navegación de Producción, guardado en los query params de la URL
 * (docs/plan-ui-produccion.md §4.5). No toca el router: solo lee y escribe
 * `route.query` con `router.replace`, igual que ya hacía `?step=` y `?lote=`.
 *
 *   ?step=5&vista=tablero|preparacion|ordenes|envios|facturas|lote
 *      &prep=1|2|3        (1 Plan · 2 Materia prima · 3 Orden de manufactura)
 *      &lote=Lote%202&paso=materia|flujo|talleres|entrega
 *      &parada=<parada_id>&pieza=<pieza>&tpaso=encargo|envio|recibo|factura
 *      &panel=<tipo>:<nombre>                           (panel lateral abierto)
 *      &filtro_lote=Lote%201&seg=salidas                (bandejas)
 *      &producto=<item_code>                            (filtro de producto)
 *
 * Así cualquier pantalla de Producción es un enlace que se puede compartir y
 * sobrevive a un refresh.
 */
import { computed } from "vue";

// "om" (orden de manufactura) dejó de ser una vista propia: ahora es el PASO 3 de
// Preparación. La vista que ocupa su lugar en el menú es "ordenes" (las órdenes a
// talleres), que antes era ese paso 3 -- se capturó la ficha y después se mandan las
// órdenes, para que cada taller la reciba ya heredada.
// "om" se acepta solo por compatibilidad con enlaces guardados: la página lo
// traduce al paso 3 de Preparación.
export const VISTAS = ["tablero", "preparacion", "ordenes", "lote", "envios", "facturas", "om"];
// "flujo" dejó de ser un paso propio: la matriz pieza x etapa ES el índice de
// talleres (sus columnas son exactamente las paradas), así que vive dentro de
// "talleres". Se acepta como alias para que los enlaces guardados sigan sirviendo.
export const PASOS_LOTE = ["materia", "talleres", "entrega"];
export const PASO_LOTE_ALIAS = { flujo: "talleres" };
// La factura NO es un paso del taller: es UNA por orden de compra de
// subcontratación y se captura en la bandeja de Facturas (ver PASOS_TALLER_UI).
// Un enlace viejo con ?tpaso=factura cae al paso que toque.
export const PASOS_TALLER = ["encargo", "envio", "recibo"];

// Qué vista (rol) manda en cada paso del lote -- ver roles.VISTAS_PRODUCCION.
// "talleres" acepta los dos roles: la matriz es de Flujo (ahí se encargan las
// piezas) y el detalle de cada taller es de Talleres.
export const VISTA_DE_PASO_LOTE = {
  materia: "materia", talleres: ["flujo", "talleres"], entrega: "entrega",
};

export function useProduccionRuta(route, router, { costeo, sales_order } = {}) {
  /** Escribe varias claves de golpe; `null`/`""` borra la clave. */
  function set(cambios) {
    const query = { ...route.query };
    for (const [k, v] of Object.entries(cambios)) {
      if (v === null || v === undefined || v === "") delete query[k];
      else query[k] = String(v);
    }
    // `router.replace` no apila historial: moverse entre vistas de Producción no
    // debe llenar el botón "atrás" del navegador de pasos intermedios.
    router.replace({ query });
  }

  const leer = (k, por_defecto = "") => (route.query[k] !== undefined ? String(route.query[k]) : por_defecto);

  const vista = computed(() => {
    const v = leer("vista");
    return VISTAS.includes(v) ? v : "";
  });
  const loteRef = computed(() => leer("lote"));
  const pasoLote = computed(() => {
    const p = PASO_LOTE_ALIAS[leer("paso")] || leer("paso");
    return PASOS_LOTE.includes(p) ? p : "";
  });
  const paradaId = computed(() => leer("parada"));
  const pieza = computed(() => leer("pieza"));
  const pasoTaller = computed(() => {
    const p = leer("tpaso");
    return PASOS_TALLER.includes(p) ? p : "";
  });
  const prepPaso = computed(() => Number(leer("prep", "0")) || 0);
  const filtroLote = computed(() => leer("filtro_lote"));
  const seg = computed(() => leer("seg"));
  const producto = computed(() => leer("producto"));
  /** `panel` llega como "<tipo>:<nombre>"; el nombre puede traer ":" (no se parte de más). */
  const panel = computed(() => {
    const raw = leer("panel");
    if (!raw) return null;
    const i = raw.indexOf(":");
    return i < 0 ? { tipo: raw, nombre: "" } : { tipo: raw.slice(0, i), nombre: raw.slice(i + 1) };
  });

  // ── Navegación ──────────────────────────────────────────────────────────────
  function irVista(v, extra = {}) {
    set({
      vista: v, prep: null, lote: null, paso: null, parada: null, pieza: null,
      tpaso: null, panel: null, ...extra,
    });
  }
  function irPreparacion(paso = 1) { set({ vista: "preparacion", prep: paso, lote: null, paso: null, parada: null, tpaso: null, panel: null }); }
  function irLote(lote_ref, paso = "", extra = {}) {
    set({ vista: "lote", lote: lote_ref, paso: paso || null, parada: null, pieza: null, tpaso: null, panel: null, prep: null, ...extra });
  }
  function irPasoLote(paso) { set({ paso, parada: null, pieza: null, tpaso: null, panel: null }); }
  function irTaller(parada_id, tpaso = "", pieza_ref = "") {
    set({ vista: "lote", paso: "talleres", parada: parada_id, tpaso: tpaso || null, pieza: pieza_ref || null, panel: null });
  }
  function irPasoTaller(tpaso) { set({ tpaso }); }
  function salirTaller() { set({ parada: null, pieza: null, tpaso: null }); }
  function abrirPanel(tipo, nombre = "") { set({ panel: nombre ? `${tipo}:${nombre}` : tipo }); }
  function cerrarPanel() { set({ panel: null }); }

  // ── Memoria por costeo + OV ────────────────────────────────────────────────
  // Reemplaza a `costeo_ultimo_lote_<costeo>`: ahora se recuerda la VISTA completa,
  // y por OV, porque cada OV tiene sus propios lotes (ver Fase 0).
  const claveMemoria = () => `costeo_ultima_vista_${costeo?.value || costeo || ""}_${sales_order?.value || sales_order || ""}`;

  function recordar() {
    try {
      const { vista: v, prep, lote, paso, parada, pieza: pz, tpaso, seg: sg, filtro_lote, producto: pr } = route.query;
      localStorage.setItem(claveMemoria(), JSON.stringify({ vista: v, prep, lote, paso, parada, pieza: pz, tpaso, seg: sg, filtro_lote, producto: pr }));
    } catch { /* localStorage puede fallar (modo privado) -- se ignora */ }
  }
  function recordado() {
    try { return JSON.parse(localStorage.getItem(claveMemoria()) || "null"); }
    catch { return null; }
  }
  /** Al cambiar de OV: Tablero limpio (los lotes de la OV anterior ya no existen aquí). */
  function reiniciar() { irVista("tablero"); }

  return {
    vista, loteRef, pasoLote, paradaId, pieza, pasoTaller, prepPaso, filtroLote, seg, producto, panel,
    set, irVista, irPreparacion, irLote, irPasoLote, irTaller, irPasoTaller, salirTaller,
    abrirPanel, cerrarPanel, recordar, recordado, reiniciar,
  };
}
