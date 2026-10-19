<!--
  Lista de barras horizontales de UNA serie (magnitud): nombre, monto en la punta,
  barra ≤ 8 px en el color de la serie sobre un riel del mismo tono, muy claro.
  Una sola serie: sin leyenda (el título de la tarjeta la nombra). Tooltip nativo
  y la cifra siempre visible, así que nada depende del color.
-->
<template>
  <div>
    <p v-if="!filas.length" class="p-meta py-4">{{ vacio }}</p>
    <div v-else class="space-y-3">
      <div v-for="f in filas" :key="f.nombre" :title="`${f.nombre}: ${formato(f.valor)}${f.nota ? ' · ' + f.nota : ''}`">
        <div class="flex items-baseline justify-between gap-3 mb-1">
          <span class="text-[12.5px] text-ink truncate" :class="f.otros ? 'text-ink-muted' : 'font-medium'">{{ f.nombre }}</span>
          <span class="text-[12.5px] tabular-nums whitespace-nowrap"><b class="font-semibold">{{ formato(f.valor) }}</b><span v-if="f.nota" class="text-ink-light"> · {{ f.nota }}</span></span>
        </div>
        <div class="h-2 rounded-full" :style="{ background: riel }">
          <div class="h-2 rounded-full" :style="{ width: `${ancho(f.valor)}%`, background: f.otros ? '#a1a1aa' : color }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  filas: { type: Array, default: () => [] }, // [{ nombre, valor, nota?, otros? }]
  formato: { type: Function, default: (v) => String(v) },
  color: { type: String, default: "#f05208" },
  riel: { type: String, default: "#fff4ef" },
  vacio: { type: String, default: "Sin datos en el periodo." },
});
const max = computed(() => Math.max(1, ...props.filas.map((f) => f.valor || 0)));
const ancho = (v) => Math.max(v > 0 ? 1.5 : 0, ((v || 0) / max.value) * 100);
</script>
