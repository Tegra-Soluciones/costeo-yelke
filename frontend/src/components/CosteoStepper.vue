<template>
  <div class="bg-white border-b border-surface-border px-6 py-3.5 flex-shrink-0">
    <div class="flex items-start max-w-3xl mx-auto">
      <template v-for="(step, idx) in steps" :key="step.key">

        <!-- Step -->
        <button
          class="flex flex-col items-center gap-1.5 w-[74px] flex-shrink-0 group"
          :class="reachable(idx) ? 'cursor-pointer' : 'cursor-default'"
          :disabled="!reachable(idx)"
          @click="reachable(idx) && $emit('select', idx)"
        >
          <span
            class="w-8 h-8 rounded-full flex items-center justify-center transition-all"
            :class="circleClass(idx)"
          >
            <svg v-if="stateOf(idx) === 'done'" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.9">
              <path stroke-linecap="round" stroke-linejoin="round" :d="step.icon" />
            </svg>
          </span>
          <span class="text-[11.5px] whitespace-nowrap" :class="labelClass(idx)">{{ step.label }}</span>
        </button>

        <!-- Connector -->
        <div
          v-if="idx < steps.length - 1"
          class="flex-1 h-0.5 mt-4 transition-colors"
          :class="idx < statusIdx ? 'bg-brand-300' : 'bg-surface-border'"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  // costeo_status: Borrador | Cotizado | Orden de Venta | En Producción | Completado
  modelValue: { type: String, default: "Borrador" },
  activeStep: { type: Number, default: 0 },
});
defineEmits(["select"]);

const steps = [
  { key: "costear",  label: "Costear",  icon: "M9 7h6M9 11h6M9 15h4M6 3h12a1 1 0 011 1v16a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z" },
  { key: "cotizar",  label: "Cotizar",  icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
  { key: "vender",   label: "Vender",   icon: "M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" },
  { key: "producir", label: "Producir", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z" },
  { key: "facturar", label: "Facturar", icon: "M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" },
];

const ORDER = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Completado"];
const statusIdx = computed(() => Math.max(ORDER.indexOf(props.modelValue), 0));

function stateOf(idx) {
  if (idx < statusIdx.value) return "done";
  if (idx === statusIdx.value) return "current";
  return "pending";
}
function reachable(idx) { return idx <= statusIdx.value; }

function circleClass(idx) {
  const s = stateOf(idx);
  const viewing = idx === props.activeStep ? " ring-2 ring-brand-200 ring-offset-1" : "";
  if (s === "done") return "bg-brand-500 text-white" + viewing;
  if (s === "current") return "bg-brand-50 text-brand-600 border-2 border-brand-500" + viewing;
  return "bg-surface-raised text-ink-light" + viewing;
}
function labelClass(idx) {
  const viewed = idx === props.activeStep ? " underline underline-offset-4 decoration-brand-300" : "";
  const s = stateOf(idx);
  if (s === "done") return "text-brand-600 font-medium" + viewed;
  if (s === "current") return "text-brand-700 font-semibold" + viewed;
  return "text-ink-light" + viewed;
}
</script>
