<template>
  <div class="flex h-screen overflow-hidden bg-surface">
    <AppSidebar />

    <!-- Content area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppNavbar />
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" class="flex-1 overflow-y-auto" />
        </Transition>
      </RouterView>
    </div>
  </div>
</template>

<script setup>
import AppSidebar from "@/components/AppSidebar.vue";
import AppNavbar  from "@/components/AppNavbar.vue";
</script>
