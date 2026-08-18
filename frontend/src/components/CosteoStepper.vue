<template>
  <div class="bg-white border-b border-surface-border px-6 py-3.5 flex-shrink-0">
    <div class="overflow-x-auto">
      <div class="flex items-start w-max mx-auto">
        <template v-for="(step, idx) in STEPS" :key="step.key">
          <button
            class="flex flex-col items-center gap-1.5 w-[74px] flex-shrink-0 group"
            :class="stepReachable(idx) ? 'cursor-pointer' : 'cursor-default'"
            :disabled="!stepReachable(idx)"
            @click="stepReachable(idx) && $emit('select', idx)"
          >
            <span class="w-8 h-8 rounded-full flex items-center justify-center transition-all" :class="stepCircleClass(idx)">
              <svg v-if="stepState(idx) === 'done'" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.9">
                <path stroke-linecap="round" stroke-linejoin="round" :d="step.icon" />
              </svg>
            </span>
            <span class="text-[11.5px] whitespace-nowrap" :class="stepLabelClass(idx)">{{ step.label }}</span>
          </button>
          <div
            v-if="idx < STEPS.length - 1"
            class="flex-1 min-w-[16px] h-0.5 mt-4 transition-colors"
            :class="stepState(idx) === 'done' ? 'bg-brand-300' : 'bg-surface-border'"
          />
        </template>
      </div>
    </div>

    <!-- Lotes de producción: en su propio renglón (no alargan la barra principal),
         alineados bajo "Producir" -- cada uno es un sub-paso de ese mismo paso. -->
    <div v-if="lotes.length || producirReachable" class="overflow-x-auto mt-2">
      <div class="flex items-center gap-1.5 w-max" :style="{ marginLeft: producirOffsetPx }">
        <div class="w-4 h-4 border-l-2 border-b-2 border-surface-border rounded-bl-md flex-shrink-0 -mt-2"></div>
        <button
          v-for="lote in lotes" :key="lote.lote_ref"
          class="flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full border transition-colors flex-shrink-0"
          :class="loteCircleClass(lote)"
          @click="$emit('select-lote', lote.lote_ref)"
        >
          <span class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0" :class="loteDotClass(lote)">
            <svg v-if="lote.done" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="4"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
          </span>
          <span class="text-[11px] font-medium whitespace-nowrap">{{ lote.label }}</span>
        </button>
        <button
          v-if="producirReachable"
          class="w-6 h-6 rounded-full border border-dashed border-brand-300 text-brand-500 hover:bg-brand-50 flex items-center justify-center flex-shrink-0"
          title="Nuevo lote"
          @click="$emit('create-lote')"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  // costeo_status: Borrador | Cotizado | Orden de Venta | En Producción | Entregado | Completado
  modelValue: { type: String, default: "Borrador" },
  activeStep: { type: Number, default: 0 },
  // Lotes de producción ya creados (de la OV activa), en orden. [{ lote_ref, label, done }]
  lotes: { type: Array, default: () => [] },
  // lote_ref del lote que se está viendo ahora mismo (si activeStep está en esa vista).
  activeLoteRef: { type: String, default: "" },
});
defineEmits(["select", "select-lote", "create-lote"]);

const STEPS = [
  { key: "costear",  label: "Costear",  icon: "M9 7h6M9 11h6M9 15h4M6 3h12a1 1 0 011 1v16a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z" },
  { key: "cotizar",  label: "Cotizar",  icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
  { key: "vender",   label: "Vender",   icon: "M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" },
  { key: "preparar_manufactura", label: "Alta de Productos", icon: "M9 3v2m6-2v2M5 8h14M6 5h12a1 1 0 011 1v13a1 1 0 01-1 1H6a1 1 0 01-1-1V6a1 1 0 011-1zm3 7l2 2 4-4" },
  { key: "producir", label: "Producir", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z" },
  { key: "enviar",   label: "Enviar",   icon: "M12 19l9 2-9-18-9 18 9-2zm0 0v-8" },
  { key: "facturar", label: "Facturar", icon: "M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" },
  { key: "reportar", label: "Reportar", icon: "M9 19V6a1 1 0 011-1h1a1 1 0 011 1v13m-3 0h3m-3 0H6a1 1 0 01-1-1v-7a1 1 0 011-1h1a1 1 0 011 1v8m3 0h3v-16a1 1 0 011-1h1a1 1 0 011 1v16m-3 0h3" },
];
const ORDER = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado"];
const statusIdx = computed(() => Math.max(ORDER.indexOf(props.modelValue), 0));
// Índice de STEPS -> índice comparable en ORDER. null = paso sin costeo_status propio
// (es una vista/sub-etapa dentro de un estatus más amplio, no un estatus en sí).
const STEP_ORDER_IDX = [0, 1, 2, null, 3, null, 4, null];
// "Manufactura" vive dentro del estatus "Orden de Venta" (no dispara su propio
// costeo_status -- el Costeo sigue siendo "Orden de Venta" mientras se materializan
// artículos y se asignan etapas; solo al preparar producción de verdad pasa a "En
// Producción"). "Reportar" tampoco es un estatus real -- se marca "done" cuando el
// proceso ya cerró (Completado) y mientras tanto se ve como los demás pasos
// alcanzables: gris con borde, sin marcar como "actual" salvo que se esté viendo.
const PREP_MFG_IDX = 3;
const PRODUCIR_IDX = 4;
const ENVIAR_IDX = 5;
const REPORT_IDX = 7;

function stepState(idx) {
  if (idx === REPORT_IDX) {
    if (props.activeStep === REPORT_IDX) return "current";
    return statusIdx.value >= 5 ? "done" : "pending";
  }
  if (idx === PREP_MFG_IDX) {
    if (props.activeStep === idx) return "current";
    return statusIdx.value >= 3 ? "done" : "pending";
  }
  if (idx === ENVIAR_IDX) {
    if (props.activeStep === idx) return "current";
    return statusIdx.value >= 4 ? "done" : "pending";
  }
  if (idx === PRODUCIR_IDX) {
    // "Current" mientras se está en Producir o en cualquiera de sus lotes -- las
    // subetapas de lote son parte visual de este mismo paso.
    if (props.activeStep === idx) return "current";
    return statusIdx.value >= 3 ? "done" : "pending";
  }
  const orderIdx = STEP_ORDER_IDX[idx];
  if (orderIdx < statusIdx.value) return "done";
  if (orderIdx === statusIdx.value) return "current";
  return "pending";
}
// "Enviar"/"Reportar" no deben esperar a que TODA la producción esté recibida --
// las remisiones parciales se pueden ir creando lote por lote. "Manufactura" es
// alcanzable en cuanto existe la Orden de Venta.
function stepReachable(idx) {
  if (idx === PREP_MFG_IDX) return statusIdx.value >= 2;
  if (idx === ENVIAR_IDX || idx === REPORT_IDX) return statusIdx.value >= 3;
  const orderIdx = STEP_ORDER_IDX[idx];
  return orderIdx != null ? orderIdx <= statusIdx.value : false;
}
const producirReachable = computed(() => statusIdx.value >= 3);

function stepCircleClass(idx) {
  const viewing = idx === props.activeStep && !props.activeLoteRef ? " ring-2 ring-brand-200 ring-offset-1" : "";
  const s = stepState(idx);
  if (s === "done") return "bg-brand-500 text-white" + viewing;
  if (s === "current") return "bg-brand-50 text-brand-600 border-2 border-brand-500" + viewing;
  if (stepReachable(idx)) return "bg-surface-raised text-ink-light border border-brand-200" + viewing;
  return "bg-surface-raised text-ink-light" + viewing;
}
function stepLabelClass(idx) {
  const viewed = idx === props.activeStep && !props.activeLoteRef ? " underline underline-offset-4 decoration-brand-300" : "";
  const s = stepState(idx);
  if (s === "done") return "text-brand-600 font-medium" + viewed;
  if (s === "current") return "text-brand-700 font-semibold" + viewed;
  return "text-ink-light" + viewed;
}

// Alinea el renglón de lotes debajo del círculo de "Producir" -- cada círculo mide
// 74px (w-[74px]) y hay uno de conector entre cada par, así que el offset es
// "índice de Producir" círculos completos.
const producirOffsetPx = computed(() => `${PRODUCIR_IDX * 74}px`);

function loteCircleClass(lote) {
  const active = props.activeLoteRef === lote.lote_ref;
  if (active) return "border-brand-500 bg-brand-50 text-brand-700";
  if (lote.done) return "border-brand-200 bg-white text-brand-600";
  return "border-surface-border bg-white text-ink-muted hover:bg-surface-raised";
}
function loteDotClass(lote) {
  if (lote.done) return "bg-brand-500 text-white";
  if (props.activeLoteRef === lote.lote_ref) return "bg-brand-500 text-white";
  return "bg-surface-raised border border-surface-border";
}
</script>
