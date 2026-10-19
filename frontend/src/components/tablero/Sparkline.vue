<!--
  Minigráfica de tendencia para un indicador (contrato del stat tile de la guía):
  línea de 2 px en gris recesivo, el último punto en el color de acento.
-->
<template>
  <div ref="caja" class="w-full">
  <svg v-if="valores.length > 1" :viewBox="`0 0 ${W} ${H}`" class="block w-full" :style="{ height: `${H}px` }" aria-hidden="true">
    <path :d="area" fill="currentColor" class="text-zinc-200" opacity="0.35" />
    <polyline :points="puntos" fill="none" stroke="#a1a1aa" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
    <circle :cx="ultimo[0]" :cy="ultimo[1]" r="3.5" :fill="color" stroke="#fff" stroke-width="2" />
  </svg>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  valores: { type: Array, default: () => [] },
  color: { type: String, default: "#f05208" },
});
// Se dibuja con el ancho real del contenedor (si no, el SVG se escala por su alto y
// queda diminuto en una tarjeta ancha).
const H = 36;
const caja = ref(null);
const W = ref(160);
let obs;
onMounted(() => { obs = new ResizeObserver(([e]) => { W.value = Math.max(60, Math.round(e.contentRect.width)); }); caja.value && obs.observe(caja.value); });
onBeforeUnmount(() => obs?.disconnect());
const coords = computed(() => {
  const v = props.valores.map((x) => Number(x) || 0);
  const max = Math.max(...v, 0), min = Math.min(...v, 0);
  const rango = max - min || 1;
  return v.map((x, i) => [5 + (i / Math.max(1, v.length - 1)) * (W.value - 10), H - 5 - ((x - min) / rango) * (H - 10)]);
});
const puntos = computed(() => coords.value.map((c) => c.join(",")).join(" "));
const area = computed(() => {
  const c = coords.value;
  if (!c.length) return "";
  return `M${c[0][0]},${H} L${c.map((p) => p.join(",")).join(" L")} L${c[c.length - 1][0]},${H} Z`;
});
const ultimo = computed(() => coords.value[coords.value.length - 1] || [0, 0]);
</script>
