<!--
  Los recibos de UNA orden de compra o de UN encargo a taller, cuando el proveedor
  entrega por partes. Cada pastilla es un recibo (validado o en borrador) y se puede
  abrir; al final, si ya se recibió todo o cuánto falta.

  El estado lo calcula el backend (estado_recibos_oc / estado_recibos_sco): aquí
  solo se pinta. Crear otro recibo NO vive aquí, sino en la barra de acciones del
  paso, igual que el resto de los botones que avanzan el flujo.
-->
<template>
  <div class="flex items-center gap-1.5 flex-wrap mb-3">
    <span class="text-[11.5px] text-ink-muted mr-0.5">{{ recibos.length > 1 ? `${recibos.length} recibos:` : "Recibo:" }}</span>
    <button
      v-for="(r, i) in recibos" :key="r.name" type="button"
      class="inline-flex items-center gap-1 h-6 px-2 rounded-full text-[11.5px] border transition-colors"
      :class="[
        r.name === activo ? 'border-ink text-ink bg-surface-raised' : 'border-surface-border text-ink-muted hover:text-ink hover:border-ink-light',
      ]"
      :title="`${r.name}${r.posting_date ? ' · ' + r.posting_date : ''}`"
      @click="emit('abrir', r.name)"
    >
      <span class="w-1.5 h-1.5 rounded-full" :class="r.docstatus === 1 ? 'bg-green-500' : 'bg-amber-400'"></span>
      <span>Entrega {{ i + 1 }}</span>
      <span class="text-ink-light">· {{ r.docstatus === 1 ? cantidad(r.qty) : "borrador" }}</span>
    </button>
    <span class="flex-1"></span>
    <span v-if="completo" class="text-[11.5px] text-green-700 font-medium">Recibido completo</span>
    <span v-else-if="pendiente > 0" class="text-[11.5px] text-amber-700 font-medium">Faltan {{ cantidad(pendiente) }} por recibir</span>
  </div>
</template>

<script setup>
defineProps({
  recibos: { type: Array, default: () => [] },
  activo: { type: String, default: "" },
  completo: { type: Boolean, default: false },
  pendiente: { type: Number, default: 0 },
});
const emit = defineEmits(["abrir"]);
const cantidad = (n) => Number(n || 0).toLocaleString("es-MX", { maximumFractionDigits: 3 });
</script>
