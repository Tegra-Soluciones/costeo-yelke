<!--
  Acumulado en el tiempo de dos series con la misma unidad (Vendido y Facturado):
  líneas de 2 px, la primera con un lavado de su color al 10 %, un solo eje, línea
  guía vertical que sigue al puntero y se pega al mes más cercano, un tooltip con
  las dos series, leyenda siempre visible y la etiqueta al final de cada línea.
-->
<template>
  <div ref="caja" class="relative select-none" @pointermove="mover" @pointerleave="activo = -1">
    <svg :viewBox="`0 0 ${ancho} ${ALTO}`" class="w-full block" :style="{ height: `${ALTO}px` }" role="img" :aria-label="titulo">
      <g v-for="t in ticks" :key="t">
        <line :x1="IZQ" :x2="ancho - DER" :y1="y(t)" :y2="y(t)" stroke="#ececec" stroke-width="1" />
        <text :x="IZQ - 8" :y="y(t) + 4" text-anchor="end" class="fill-ink-light" style="font-size: 10.5px">{{ compacto(t) }}</text>
      </g>
      <path v-if="acum.length" :d="areaDe(series[0].clave)" :fill="series[0].color" opacity="0.1" />
      <path v-for="s in series" :key="s.clave" :d="lineaDe(s.clave)" fill="none" :stroke="s.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
      <text v-for="(m, i) in acum" v-show="mostrarEtiqueta(i)" :key="m.mes" :x="x(i)" :y="ALTO - 8" text-anchor="middle" class="fill-ink-muted" style="font-size: 11px">{{ m.etiqueta }}</text>
      <!-- Final de cada línea: punto con anillo del color de la superficie + valor -->
      <g v-for="s in series" :key="`f-${s.clave}`">
        <circle :cx="x(acum.length - 1)" :cy="y(final(s.clave))" r="4.5" :fill="s.color" stroke="#fff" stroke-width="2" />
      </g>
      <g v-if="activo >= 0">
        <line :x1="x(activo)" :x2="x(activo)" :y1="10" :y2="ALTO - ABAJO" stroke="#d4d4d8" stroke-width="1" />
        <circle v-for="s in series" :key="`a-${s.clave}`" :cx="x(activo)" :cy="y(acum[activo][s.clave])" r="4.5" :fill="s.color" stroke="#fff" stroke-width="2" />
      </g>
    </svg>
    <div class="absolute right-0 top-0 text-right space-y-0.5 pointer-events-none">
      <p v-for="s in series" :key="`v-${s.clave}`" class="text-[12px] flex items-center justify-end gap-1.5">
        <span class="w-3 h-0.5 rounded" :style="{ background: s.color }"></span>
        <span class="text-ink-muted">{{ s.etiqueta }}</span><b class="font-semibold tabular-nums">{{ compacto(final(s.clave)) }}</b>
      </p>
    </div>
    <div v-if="activo >= 0" class="absolute z-10 pointer-events-none bg-white border border-surface-border rounded-lg shadow-lg px-3 py-2 min-w-[170px]" :style="posTooltip">
      <p class="text-[11px] text-ink-muted mb-1">Acumulado a {{ acum[activo].etiqueta }}</p>
      <div v-for="s in series" :key="`t-${s.clave}`" class="flex items-center gap-2 text-[12px]">
        <span class="w-3 h-0.5 rounded" :style="{ background: s.color }"></span>
        <span class="font-semibold tabular-nums">{{ formato(acum[activo][s.clave]) }}</span><span class="text-ink-muted">{{ s.etiqueta }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  datos: { type: Array, default: () => [] },     // [{ mes, etiqueta, <clave>: valor del mes }]
  series: { type: Array, default: () => [] },    // [{ clave, etiqueta, color }]
  formato: { type: Function, default: (v) => String(v) },
  compacto: { type: Function, default: (v) => String(v) },
  titulo: { type: String, default: "" },
});
const ALTO = 230, IZQ = 50, DER = 14, ABAJO = 26;
const caja = ref(null);
const ancho = ref(640);
const activo = ref(-1);
let obs;
onMounted(() => { obs = new ResizeObserver(([e]) => { ancho.value = Math.max(280, Math.round(e.contentRect.width)); }); caja.value && obs.observe(caja.value); });
onBeforeUnmount(() => obs?.disconnect());

const acum = computed(() => {
  const suma = Object.fromEntries(props.series.map((s) => [s.clave, 0]));
  return props.datos.map((m) => {
    const fila = { mes: m.mes, etiqueta: m.etiqueta };
    for (const s of props.series) { suma[s.clave] += Number(m[s.clave]) || 0; fila[s.clave] = suma[s.clave]; }
    return fila;
  });
});
const maximo = computed(() => Math.max(1, ...acum.value.flatMap((m) => props.series.map((s) => m[s.clave]))));
const ticks = computed(() => {
  const crudo = maximo.value / 4, p = 10 ** Math.floor(Math.log10(crudo));
  const paso = [1, 2, 2.5, 5, 10].map((f) => f * p).find((v) => v >= crudo) || crudo;
  const n = Math.max(2, Math.ceil(maximo.value / paso));
  return Array.from({ length: n + 1 }, (_, k) => k * paso);
});
const tope = computed(() => ticks.value[ticks.value.length - 1] || 1);
const x = (i) => IZQ + (i / Math.max(1, acum.value.length - 1)) * (ancho.value - IZQ - DER - 110);
const y = (v) => (ALTO - ABAJO) - (v / tope.value) * (ALTO - ABAJO - 14);
const final = (k) => acum.value[acum.value.length - 1]?.[k] || 0;
const lineaDe = (k) => acum.value.map((m, i) => `${i ? "L" : "M"}${x(i)},${y(m[k])}`).join(" ");
const areaDe = (k) => `${lineaDe(k)} L${x(acum.value.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
const mostrarEtiqueta = (i) => acum.value.length <= 7 || i % 2 === (acum.value.length - 1) % 2;
function mover(ev) {
  const r = caja.value.getBoundingClientRect();
  const px = ((ev.clientX - r.left) / r.width) * ancho.value;
  let mejor = 0;
  acum.value.forEach((_, i) => { if (Math.abs(x(i) - px) < Math.abs(x(mejor) - px)) mejor = i; });
  activo.value = acum.value.length ? mejor : -1;
}
const posTooltip = computed(() => {
  const px = x(activo.value);
  const izq = px > ancho.value - 200 ? px - 190 : px + 12;
  return { left: `${(izq / ancho.value) * 100}%`, top: "44px" };
});
</script>
