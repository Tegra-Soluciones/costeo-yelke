<!--
  Estado vacío: ícono gris + título + una línea (docs/plan-ui-produccion.md §4.3).
  La acción NO va aquí: vive en la barra de acciones de abajo, como todas.
-->
<template>
  <div class="p-panel p-12 text-center">
    <div class="w-10 h-10 rounded-full bg-surface-raised mx-auto flex items-center justify-center text-ink-light text-lg">
      <slot name="icono">{{ icono }}</slot>
    </div>
    <p class="text-[14px] font-semibold mt-3">{{ titulo }}</p>
    <p v-if="detalle || $slots.detalle" class="p-meta mt-1"><slot name="detalle">{{ detalle }}</slot></p>
  </div>
</template>

<script setup>
defineProps({
  titulo: { type: String, required: true },
  detalle: { type: String, default: "" },
  icono: { type: String, default: "⏳︎" },
});
</script>
