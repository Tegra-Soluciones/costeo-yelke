<template>
  <div class="flex h-screen overflow-hidden bg-surface">
    <!-- Las pantallas pensadas para celular (meta.movil, p. ej. Dirección) se pintan
         sin el menú ni la barra en pantallas chicas: traen su propio encabezado. -->
    <div :class="sinMarcoMovil ? 'hidden lg:flex' : 'flex'"><AppSidebar /></div>

    <!-- Content area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <div :class="sinMarcoMovil ? 'hidden lg:block' : ''"><AppNavbar /></div>
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
import { useRoute } from "vue-router";
import AppSidebar from "@/components/AppSidebar.vue";
import AppNavbar  from "@/components/AppNavbar.vue";

const route = useRoute();
const sinMarcoMovil = computed(() => !!route.meta.movil);
</script>
