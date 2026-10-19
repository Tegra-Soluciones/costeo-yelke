<!--
  Proyectos por etapa como recorrido: una estación por etapa del ciclo con su cuenta,
  sobre la línea del proceso. La estación con más proyectos lleva el acento (dónde se
  concentra el trabajo); las vacías quedan en gris. Rejilla de columnas iguales: cabe
  en cualquier ancho sin cortarse.
-->
<template>
  <div class="relative grid" :style="{ gridTemplateColumns: `repeat(${etapas.length}, minmax(0, 1fr))` }">
    <div class="absolute top-6 h-[2px] bg-brand-100" :style="{ left: `${50 / etapas.length}%`, right: `${50 / etapas.length}%` }"></div>
    <div v-for="e in etapas" :key="e.nombre" class="relative flex flex-col items-center text-center px-0.5">
      <div
        class="w-12 h-12 rounded-full flex items-center justify-center text-[17px] font-semibold ring-4 ring-white"
        :class="!e.valor ? 'bg-zinc-100 text-ink-light' : e.valor === max ? 'bg-brand-600 text-white' : 'bg-brand-50 text-brand-700'"
      >{{ e.valor }}</div>
      <p class="text-[11px] mt-1.5 leading-tight break-words" :class="e.valor ? 'text-ink font-medium' : 'text-ink-light'">{{ e.nombre }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ etapas: { type: Array, default: () => [] } }); // [{ nombre, valor }]
const max = computed(() => Math.max(1, ...props.etapas.map((e) => e.valor || 0)));
</script>
