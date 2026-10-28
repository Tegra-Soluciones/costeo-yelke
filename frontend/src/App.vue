<template>
  <div class="flex h-screen overflow-hidden bg-surface">
    <!-- Las pantallas pensadas para celular (meta.movil, p. ej. Dirección) se pintan
         sin el menú ni la barra en pantallas chicas: traen su propio encabezado. -->
    <div :class="sinMarcoMovil ? 'hidden lg:flex' : 'flex'"><AppSidebar /></div>

    <!-- Content area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <div :class="sinMarcoMovil ? 'hidden lg:block' : ''"><AppNavbar /></div>
      <!-- "Ver como…" (pantalla de Accesos): la app pintada con los accesos de otro
           puesto o usuario. Solo la pantalla; el servidor sigue tratándote como tú. -->
      <div v-if="accesos.simulado" class="flex items-center justify-between gap-3 px-5 py-2 bg-brand-50 border-b border-brand-200 text-[12.5px] text-brand-800">
        <span>Viendo la app como <b>{{ accesos.simulado.etiqueta }}</b> · vista previa, los datos y acciones siguen siendo los tuyos</span>
        <button type="button" class="font-semibold hover:underline" @click="salirSimulacion">Salir</button>
      </div>
      <RouterView v-slot="{ Component }">
        <!-- Sin <Transition>: el modo out-in dejaba el contenido pegado en
             opacity:0 (fade-enter-from) cuando el componente entrante renderizaba
             pesado o el saliente no terminaba de irse. La navegación instantánea
             es preferible a ese glitch. -->
        <component :is="Component" class="flex-1 overflow-y-auto" />
      </RouterView>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { simular, useAccesos } from "@/composables/useAccesos.js";
import AppSidebar from "@/components/AppSidebar.vue";
import AppNavbar  from "@/components/AppNavbar.vue";

const route = useRoute();
const router = useRouter();
const sinMarcoMovil = computed(() => !!route.meta.movil);
const { estado: accesos } = useAccesos();
function salirSimulacion() { simular(null, null); router.push("/accesos"); }
</script>
