<!--
  Columnas agrupadas por mes (Vendido / Facturado). Especificación de la guía de
  visualización: columnas ≤ 24 px con punta redondeada de 4 px (cuadradas en la
  base), 2 px de separación entre las del mismo mes, cuadrícula de línea fina, un
  solo eje, leyenda siempre visible (2 series), tooltip por mes y vista de tabla.
  Paleta validada (#f05208 / #2a78d6 sobre blanco: CVD ΔE 26.5, contraste ≥ 3:1).
-->
<template>
  <div>
    <div class="flex items-center gap-4 flex-wrap mb-3">
      <template v-if="leyenda">
      <span v-for="s in series" :key="s.clave" class="flex items-center gap-1.5 text-[12px] text-ink-muted">
        <span class="w-2.5 h-2.5 rounded-[3px]" :style="{ background: s.color }"></span>{{ s.etiqueta }}
        <!-- El valor del último mes va aquí y no sobre la columna: ahí las dos etiquetas se enciman -->
        <b v-if="ultimo >= 0" class="font-semibold text-ink tabular-nums">{{ compacto(datos[ultimo][s.clave]) }}</b>
      </span>
      <span v-if="ultimo >= 0" class="text-[11.5px] text-ink-light">en {{ datos[ultimo].etiqueta }}</span>
      </template>
      <button type="button" class="ml-auto text-[12px] text-ink-muted hover:text-ink font-medium" @click="tabla = !tabla">
        {{ tabla ? "Ver gráfica" : "Ver tabla" }}
      </button>
    </div>

    <table v-if="tabla" class="p-tbl">
      <thead><tr><th>Mes</th><th v-for="s in series" :key="s.clave" class="text-right">{{ s.etiqueta }}</th></tr></thead>
      <tbody>
        <tr v-for="m in datos" :key="m.mes">
          <td>{{ m.etiqueta }}</td>
          <td v-for="s in series" :key="s.clave" class="text-right tabular-nums">{{ fmt(m[s.clave]) }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else ref="caja" class="relative" @pointerleave="activo = -1">
      <svg :viewBox="`0 0 ${ancho} ${ALTO}`" class="w-full block" :style="{ height: `${ALTO}px` }" role="img" :aria-label="titulo">
        <!-- Cuadrícula y eje: línea fina, recesiva -->
        <g v-for="t in ticks" :key="t">
          <line :x1="MARGEN_IZQ" :x2="ancho" :y1="y(t)" :y2="y(t)" stroke="#ececec" stroke-width="1" />
          <text :x="MARGEN_IZQ - 8" :y="y(t) + 4" text-anchor="end" class="fill-ink-light" style="font-size: 10.5px">{{ compacto(t) }}</text>
        </g>
        <g v-for="(m, i) in datos" :key="m.mes">
          <!-- Área de interacción: toda la banda del mes, más grande que las columnas -->
          <rect
            :x="xBanda(i)" :y="0" :width="banda" :height="ALTO - MARGEN_ABAJO" fill="transparent"
            tabindex="0" @pointerenter="activo = i" @focus="activo = i" @blur="activo = -1"
          />
          <rect v-if="activo === i" :x="xBanda(i)" :y="0" :width="banda" :height="ALTO - MARGEN_ABAJO" fill="#f4f4f5" rx="6" pointer-events="none" />
          <path
            v-for="(s, j) in series" :key="s.clave" :d="columna(i, j, m[s.clave])" :fill="m._color || s.color"
            pointer-events="none"
          />
          <text :x="xBanda(i) + banda / 2" :y="ALTO - 8" text-anchor="middle" class="fill-ink-muted" style="font-size: 11px">{{ m.etiqueta }}</text>
        </g>
      </svg>

      <div
        v-if="activo >= 0" class="absolute z-10 pointer-events-none bg-white border border-surface-border rounded-lg shadow-lg px-3 py-2 min-w-[150px]"
        :style="tooltipPos"
      >
        <p class="text-[11px] text-ink-muted mb-1">{{ datos[activo].etiqueta }}</p>
        <div v-for="s in series" :key="s.clave" class="flex items-center gap-2 text-[12px]">
          <span class="w-3 h-0.5 rounded" :style="{ background: s.color }"></span>
          <span class="font-semibold tabular-nums">{{ fmt(datos[activo][s.clave]) }}</span>
          <span class="text-ink-muted">{{ s.etiqueta }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { dinero, dineroCorto } from "@/utils/formato.js";

const props = defineProps({
  datos: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{ clave, etiqueta, color }]
  moneda: { type: String, default: "MXN" },
  titulo: { type: String, default: "" },
  // Una sola serie (p. ej. prendas por semana): sin leyenda, la nombra el título.
  leyenda: { type: Boolean, default: true },
  // Otra unidad que no sea dinero (prendas, órdenes...).
  formato: { type: Function, default: null },
  formatoCorto: { type: Function, default: null },
});
const fmt = (v) => (props.formato ? props.formato(v) : dinero(v, props.moneda));

const ALTO = 220;
const MARGEN_IZQ = 48;
const MARGEN_ABAJO = 26;
const MAX_COL = 24;
const SEP = 2;

const caja = ref(null);
const ancho = ref(640);
const activo = ref(-1);
const tabla = ref(false);
let observador;

onMounted(() => {
  observador = new ResizeObserver(([e]) => { ancho.value = Math.max(280, Math.round(e.contentRect.width)); });
  if (caja.value) observador.observe(caja.value);
});
onBeforeUnmount(() => observador?.disconnect());

const maximo = computed(() => Math.max(1, ...props.datos.flatMap((m) => props.series.map((s) => m[s.clave] || 0))));
const ticks = computed(() => {
  // Marcas en números redondos (1, 2, 2.5 o 5 × 10^n); el eje termina en la primera
  // que cubre el máximo, para no desperdiciar altura.
  const crudo = maximo.value / 4;
  const p = 10 ** Math.floor(Math.log10(crudo));
  const paso = [1, 2, 2.5, 5, 10].map((f) => f * p).find((v) => v >= crudo) || crudo;
  const n = Math.max(2, Math.ceil(maximo.value / paso));
  return Array.from({ length: n + 1 }, (_, k) => k * paso);
});
const tope = computed(() => ticks.value[ticks.value.length - 1] || 1);
const banda = computed(() => (ancho.value - MARGEN_IZQ) / Math.max(1, props.datos.length));
const anchoCol = computed(() => Math.min(MAX_COL, (banda.value * 0.62 - SEP * (props.series.length - 1)) / Math.max(1, props.series.length)));
const ultimo = computed(() => {
  for (let i = props.datos.length - 1; i >= 0; i--) if (props.series.some((s) => props.datos[i][s.clave])) return i;
  return -1;
});

const y = (v) => (ALTO - MARGEN_ABAJO) - (v / tope.value) * (ALTO - MARGEN_ABAJO - 14);
const xBanda = (i) => MARGEN_IZQ + i * banda.value;
const xCol = (i, j) => {
  const grupo = anchoCol.value * props.series.length + SEP * (props.series.length - 1);
  return xBanda(i) + (banda.value - grupo) / 2 + j * (anchoCol.value + SEP);
};
/** Columna con la punta redondeada (4 px) y la base cuadrada, sobre el eje. */
function columna(i, j, v) {
  if (!v) return "";
  const x = xCol(i, j), w = anchoCol.value, base = ALTO - MARGEN_ABAJO, top = y(v);
  const r = Math.min(4, w / 2, (base - top) / 2);
  return `M${x},${base} V${top + r} Q${x},${top} ${x + r},${top} H${x + w - r} Q${x + w},${top} ${x + w},${top + r} V${base} Z`;
}
const compacto = (v) => (props.formatoCorto ? props.formatoCorto(v) : dineroCorto(v, props.moneda).replace(".00", ""));
const tooltipPos = computed(() => {
  const x = xBanda(activo.value) + banda.value / 2;
  const izquierda = x > ancho.value - 170 ? x - 170 : x + 12;
  return { left: `${(izquierda / ancho.value) * 100}%`, top: "8px" };
});
</script>
