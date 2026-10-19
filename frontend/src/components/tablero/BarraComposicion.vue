<!--
  Parte del todo como barra 100 % apilada (la guía: nada de dona). Segmentos con
  2 px de separación del color de la superficie, el porcentaje dentro SOLO si cabe
  (si no, lo carga la leyenda), leyenda siempre visible con monto y porcentaje, y
  tooltip por segmento. Paleta validada: #2a78d6 #eb6834 #1baf7a #eda100 #6250d6
  (CVD ΔE ≥ 9.1); los dos claros quedan bajo 3:1, por eso la leyenda con valores.
-->
<template>
  <div>
    <div class="flex h-9 gap-[2px] rounded-lg overflow-hidden" role="img" :aria-label="titulo">
      <div
        v-for="(p, i) in visibles" :key="p.clave" class="relative h-full flex items-center justify-center text-[11.5px] font-semibold transition-opacity"
        :style="{ width: `${p.pct}%`, background: COLORES[i % COLORES.length], color: claro(i) ? '#111' : '#fff', opacity: activo >= 0 && activo !== i ? 0.45 : 1 }"
        :title="`${p.etiqueta}: ${formato(p.monto)} (${p.pct.toFixed(1)} %)`" tabindex="0"
        @pointerenter="activo = i" @pointerleave="activo = -1" @focus="activo = i" @blur="activo = -1"
      >
        <span v-if="p.pct >= 9">{{ Math.round(p.pct) }} %</span>
      </div>
    </div>
    <div class="grid sm:grid-cols-2 gap-x-6 gap-y-2 mt-4">
      <div
        v-for="(p, i) in visibles" :key="`l-${p.clave}`" class="flex items-center gap-2 text-[12.5px] rounded-md -mx-1 px-1"
        :class="activo === i ? 'bg-surface-raised' : ''" @pointerenter="activo = i" @pointerleave="activo = -1"
      >
        <span class="w-2.5 h-2.5 rounded-[3px] flex-shrink-0" :style="{ background: COLORES[i % COLORES.length] }"></span>
        <span class="flex-1 truncate">{{ p.etiqueta }}</span>
        <span class="tabular-nums text-ink-muted whitespace-nowrap">{{ formato(p.monto) }}</span>
        <b class="tabular-nums font-semibold w-14 text-right whitespace-nowrap">{{ p.pct.toFixed(1) }} %</b>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  partes: { type: Array, default: () => [] }, // [{ clave, etiqueta, monto }]
  formato: { type: Function, default: (v) => String(v) },
  titulo: { type: String, default: "" },
});
const COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"];
const CLAROS = new Set(["#1baf7a", "#eda100"]);
const activo = ref(-1);
const total = computed(() => props.partes.reduce((s, p) => s + Math.max(0, p.monto || 0), 0));
const visibles = computed(() => props.partes
  .map((p) => ({ ...p, pct: total.value ? (Math.max(0, p.monto || 0) / total.value) * 100 : 0 }))
  .filter((p) => p.pct > 0));
const claro = (i) => CLAROS.has(COLORES[i % COLORES.length]);
</script>
