<!--
  Encabezado de cada paso del taller: qué documento es (Encargo / Envío de material /
  Recibo del taller), su folio y su estado. Los tres pasos muestran datos parecidos y
  sin esto no se distinguía en cuál documento se estaba.
-->
<template>
  <div class="flex items-center gap-2.5 flex-wrap mb-3">
    <span class="text-[15px] font-semibold text-ink">{{ titulo }}</span>
    <span v-if="codigo" class="text-[13px] font-mono text-ink-muted">{{ codigo }}</span>
    <span v-else class="text-[12.5px] text-ink-light">sin crear todavía</span>
    <DocStatusPill v-if="codigo" :docstatus="docstatus" :label="etiqueta" />
  </div>
</template>

<script setup>
import DocStatusPill from "@/components/DocStatusPill.vue";

defineProps({
  titulo: { type: String, required: true },
  codigo: { type: String, default: "" },
  docstatus: { type: [Number, String], default: 0 },
  etiqueta: { type: String, default: "" },
});
</script>
