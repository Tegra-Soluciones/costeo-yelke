<template>
  <div class="bg-white rounded-xl border border-surface-border px-4 py-3 flex items-center gap-5 flex-wrap">
    <div v-for="s in segments" :key="s.key" class="flex items-center gap-2.5 min-w-[150px] flex-1">
      <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" :class="s.pct === null ? 'bg-surface-raised text-ink-light' : s.pct >= 100 ? 'bg-green-100 text-green-600' : 'bg-brand-50 text-brand-600'">
        <svg v-if="s.pct >= 100" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
        <component v-else :is="s.icon" class="w-4 h-4" />
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[11.5px] font-medium text-ink-muted truncate">{{ s.label }}</span>
          <span class="text-[11.5px] font-semibold text-ink flex-shrink-0">{{ s.pct === null ? '—' : s.pct + '%' }}</span>
        </div>
        <div class="h-1.5 rounded-full bg-surface-raised mt-1 overflow-hidden">
          <div class="h-full rounded-full transition-all" :class="s.pct >= 100 ? 'bg-green-500' : 'bg-brand-500'" :style="{ width: (s.pct || 0) + '%' }"></div>
        </div>
        <p v-if="s.detail" class="text-[10.5px] text-ink-light mt-0.5">{{ s.detail }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h } from "vue";

// Barra de progreso persistente del pedido, visible tanto en "Producir" como en
// "Enviar" -- la producción y el envío ahora se entrelazan (se puede enviar un lote
// mientras otro sigue en planta), así que conviene ver las tres etapas siempre juntas.
const props = defineProps({
  materiaPrimaPct: { type: [Number, null], default: null },
  subPct: { type: [Number, null], default: null },
  subDetail: { type: String, default: "" },
  envioPct: { type: [Number, null], default: null },
});

const IconBox = () => h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8" }, [
  h("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" }),
]);
const IconFactory = () => h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8" }, [
  h("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" }),
]);
const IconTruck = () => h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8" }, [
  h("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 5H6l-2-5m16 0H4m5 5v.01M15 18v.01" }),
]);

const segments = computed(() => [
  { key: "mp", label: "Materia prima", pct: props.materiaPrimaPct, icon: IconBox },
  { key: "sub", label: "Producción", pct: props.subPct, detail: props.subDetail, icon: IconFactory },
  { key: "envio", label: "Entregado", pct: props.envioPct, icon: IconTruck },
]);
</script>
