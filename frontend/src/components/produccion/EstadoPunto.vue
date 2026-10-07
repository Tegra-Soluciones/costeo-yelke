<!--
  Punto de estado de 8 px. Es el vocabulario de color de toda Producción
  (docs/plan-ui-produccion.md §4.1.6), en un solo lugar para que no se invente
  en cada pantalla:

    ok   verde    hecho
    fac  índigo   facturado
    wait ámbar    pendiente o borrador
    now  naranja  lo que sigue (con halo)
    bad  rojo     bloqueado o falta
    off  gris     en espera
-->
<template>
  <span class="p-dot" :class="`p-dot-${estado}`" :title="titulo || undefined"></span>
</template>

<script setup>
defineProps({
  estado: { type: String, default: "off", validator: (v) => ["ok", "fac", "wait", "now", "bad", "off"].includes(v) },
  titulo: { type: String, default: "" },
});
</script>
