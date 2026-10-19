<!--
  Indicador (contrato del stat tile de la guía): etiqueta · valor · cambio contra el
  periodo anterior (flecha + texto; verde/rojo según si subir es bueno, gris si no se
  juzga) · minigráfica de tendencia o medidor · nota. `grande` = el número principal.
-->
<template>
  <div class="bg-white p-4 flex flex-col min-w-0" :class="grande ? 'lg:p-5' : ''">
    <div class="flex items-center gap-2">
      <span v-if="icono" class="w-6 h-6 rounded-md flex items-center justify-center" :class="tonoIcono"><Icono :nombre="icono" class="w-3.5 h-3.5" :grosor="2" /></span>
      <p class="p-meta truncate">{{ etiqueta }}</p>
    </div>
    <p class="font-semibold tracking-tight leading-none mt-1.5" :class="grande ? 'text-[44px] lg:text-[52px]' : 'text-[26px]'">{{ valor }}</p>
    <p v-if="delta !== undefined" class="text-[11.5px] mt-1.5">
      <template v-if="delta == null"><span class="text-ink-light">{{ periodo ? "sin datos del periodo anterior" : "" }}</span></template>
      <template v-else>
        <span class="font-semibold inline-flex items-center gap-0.5" :class="tono"><Icono :nombre="delta >= 0 ? 'sube' : 'baja'" class="w-3 h-3" :grosor="2.5" />{{ Math.abs(delta).toFixed(puntos ? 1 : 0) }}{{ puntos ? " pts" : " %" }}</span>
        <span class="text-ink-light"> {{ periodo }}</span>
      </template>
    </p>
    <Sparkline v-if="tendencia && tendencia.some((x) => x)" class="mt-2" :valores="tendencia" :color="color" />
    <div v-if="barra != null" class="h-1.5 rounded-full mt-2.5" :style="{ background: riel }">
      <div class="h-1.5 rounded-full" :style="{ width: `${Math.min(100, Math.max(0, barra))}%`, background: color }"></div>
    </div>
    <p v-if="nota" class="text-[11.5px] text-ink-muted mt-auto pt-2 leading-snug">{{ nota }}</p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Sparkline from "@/components/tablero/Sparkline.vue";
import Icono from "@/components/Icono.vue";

const props = defineProps({
  etiqueta: String,
  valor: String,
  delta: { type: Number, default: undefined },
  periodo: String,
  puntos: Boolean,
  neutro: Boolean,
  // Para indicadores donde subir es malo (p. ej. entregas vencidas).
  invertido: Boolean,
  nota: String,
  barra: { type: Number, default: null },
  tendencia: { type: Array, default: null },
  grande: Boolean,
  icono: String,
  alerta: Boolean,
  color: { type: String, default: "#f05208" },
  riel: { type: String, default: "#fff4ef" },
});
const tono = computed(() => {
  if (props.neutro || Math.abs(props.delta || 0) < 0.05) return "text-ink-muted";
  const bueno = props.invertido ? props.delta < 0 : props.delta >= 0;
  return bueno ? "text-emerald-700" : "text-red-700";
});
const tonoIcono = computed(() => (props.alerta ? "bg-red-50 text-red-700" : "bg-brand-50 text-brand-700"));
</script>
