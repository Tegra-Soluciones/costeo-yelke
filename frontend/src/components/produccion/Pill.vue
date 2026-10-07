<!--
  Pastilla de estado. Mismo vocabulario de color que EstadoPunto
  (docs/plan-ui-produccion.md §4.1.6).

  `ancho` fija un ancho para que una columna de pills en una lista quede alineada
  (así se ven en el mockup: `w-28 justify-center`).
-->
<template>
  <span class="p-pill" :class="[`p-pill-${estado}`, ancho]"><slot>{{ texto }}</slot></span>
</template>

<script setup>
defineProps({
  estado: { type: String, default: "off", validator: (v) => ["ok", "fac", "wait", "now", "bad", "off"].includes(v) },
  texto: { type: String, default: "" },
  ancho: { type: String, default: "" },
});
</script>
