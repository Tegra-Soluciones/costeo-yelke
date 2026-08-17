<script setup>
// Selector persistente y visible de "OV activa" -- se repite igual en Producir, Enviar,
// Facturar y Reportar para que siempre sea obvio a qué Orden de Venta corresponde lo que
// se está viendo, y para poder cambiar de OV sin tener que volver al acordeón de Vender.
const props = defineProps({
  salesOrders: { type: Array, default: () => [] },
  activeName: { type: String, default: null },
});
const emit = defineEmits(["update:activeName"]);

function fmtC(v) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0);
}
</script>

<template>
  <div v-if="salesOrders.length" class="flex items-center gap-2 bg-brand-50/70 border border-brand-100 rounded-lg px-3 py-2">
    <svg class="w-4 h-4 text-brand-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
    <span class="text-[11.5px] font-semibold text-brand-700 flex-shrink-0">OV activa:</span>
    <select
      v-if="salesOrders.length > 1"
      class="text-[12.5px] font-medium text-ink bg-white border border-brand-200 rounded-md px-2 py-1 flex-1 min-w-0"
      :value="activeName"
      @change="emit('update:activeName', $event.target.value)"
    >
      <option v-for="so in salesOrders" :key="so.name" :value="so.name">
        {{ so.name }} — {{ so.docstatus === 1 ? "Validada" : "Borrador" }} — {{ fmtC(so.grand_total) }}
      </option>
    </select>
    <span v-else class="text-[12.5px] font-medium text-ink truncate">{{ salesOrders[0].name }}</span>
    <span
      v-if="salesOrders.length > 1"
      class="text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0"
      :class="salesOrders.length > 1 ? 'bg-brand-100 text-brand-700' : ''"
    >{{ salesOrders.length }} OV{{ salesOrders.length === 1 ? '' : 's' }}</span>
  </div>
</template>
