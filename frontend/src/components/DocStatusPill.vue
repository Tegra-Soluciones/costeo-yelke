<template>
  <span
    class="text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap inline-flex items-center gap-1"
    :class="cls"
  >
    <svg v-if="state === 'validado'" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from "vue";

// Pill de estado de un documento individual (Costeo/OC/SCO/Recibo/...), a partir de
// su docstatus nativo de Frappe (0 borrador, 1 validado, 2 cancelado). `label` permite
// sobreescribir el texto (ej. "Recibido" en vez de "Validado").
const props = defineProps({
  docstatus: { type: [Number, String], default: 0 },
  label: { type: String, default: "" },
});

const state = computed(() => {
  const ds = Number(props.docstatus);
  if (ds === 1) return "validado";
  if (ds === 2) return "cancelado";
  return "borrador";
});
const label = computed(() => props.label || { validado: "Validado", cancelado: "Cancelado", borrador: "Borrador" }[state.value]);
const cls = computed(() => ({
  validado: "bg-green-50 text-green-700",
  cancelado: "bg-red-50 text-red-700",
  borrador: "bg-amber-50 text-amber-700",
}[state.value]));
</script>
