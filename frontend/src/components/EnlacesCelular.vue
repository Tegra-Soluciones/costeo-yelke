<!--
  Salida entre las pantallas de celular (Dirección, Levantamiento, Asignaciones): en el
  celular no hay menú de la app, así que cada una enlaza a las otras que el usuario tiene.
  `actual`: la ruta en la que se está (no se repite).
-->
<template>
  <nav class="flex items-center gap-1 flex-wrap">
    <RouterLink
      v-for="e in enlaces" :key="e.to" :to="e.to"
      :class="e.naranja ? 'h-8 px-3 rounded-full bg-brand-500 text-white text-[12px] font-semibold flex items-center active:bg-brand-600' : 'h-8 px-2 flex items-center text-[12px] text-ink-light font-medium'"
    >{{ e.texto }}</RouterLink>
  </nav>
</template>

<script setup>
import { computed } from "vue";
import { usePermisosAprobacion } from "@/composables/useAprobacion.js";
import { useAccesos } from "@/composables/useAccesos.js";

const props = defineProps({ actual: { type: String, default: "" } });
const permisos = usePermisosAprobacion();
const { puede } = useAccesos();

const enlaces = computed(() => [
  { to: "/prospecto-comercial", texto: "+ Prospecto", naranja: true, ve: puede("levantamiento", "editar") },
  { to: "/direccion", texto: "Dirección ›", ve: permisos.ve_panel || permisos.puede_aprobar || permisos.puede_revisar || permisos.puede_aprobar_precios },
  { to: "/asignaciones", texto: "Asignaciones ›", ve: true },
].filter((e) => e.ve && e.to !== props.actual));
</script>
