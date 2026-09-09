<template>
  <div class="flex h-screen overflow-hidden bg-surface">
    <AppSidebar />

    <!-- Content area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppNavbar />
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
import AppSidebar from "@/components/AppSidebar.vue";
import AppNavbar  from "@/components/AppNavbar.vue";
</script>
