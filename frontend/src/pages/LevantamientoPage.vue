<!--
  Levantamiento (vista «levantamiento», roles.VISTAS): pantalla propia para quien toma
  los datos de un pedido nuevo -- Dirección y quien tenga la vista. Pensada para el
  celular: ahí se pinta sin el menú de la app (meta.movil) y trae su propio encabezado.
-->
<template>
  <div class="bg-surface min-h-full px-0 lg:px-8">
    <div class="max-w-[760px] mx-auto">
      <div class="px-4 lg:px-0 pb-1 lg:pt-5 flex items-end justify-between gap-3" style="padding-top: max(12px, env(safe-area-inset-top))">
        <div>
          <p class="p-eyebrow">Pedido nuevo</p>
          <h1 class="text-[22px] lg:text-[24px] font-semibold tracking-tight leading-tight mt-0.5">Levantamiento</h1>
          <p class="p-lede mt-0.5">Datos del cliente, el pedido y sus fotos; se lo asignas a quien lo va a costear.</p>
        </div>
        <!-- En el celular no hay menú: la salida a lo demás que tenga. -->
        <div class="lg:hidden flex items-center -mr-2 flex-shrink-0 self-start">
          <RouterLink v-if="puede('direccion')" to="/direccion" class="h-10 px-2 flex items-center text-[12px] text-ink-light font-medium">Dirección ›</RouterLink>
          <RouterLink v-else-if="otrasVistas" to="/inicio" class="h-10 px-2 flex items-center text-[12px] text-ink-light font-medium">App ›</RouterLink>
        </div>
      </div>
      <div style="padding-bottom: max(24px, env(safe-area-inset-bottom))">
        <LevantamientoProyecto />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import LevantamientoProyecto from "@/components/direccion/LevantamientoProyecto.vue";
import { useAccesos } from "@/composables/useAccesos.js";

const { estado, puede } = useAccesos();
const otrasVistas = computed(() => Object.keys(estado.accesos || {}).some((k) => k !== "levantamiento"));
</script>
