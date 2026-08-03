<template>
  <header class="bg-white border-b border-surface-border px-6 py-4 flex items-center justify-between flex-shrink-0">
    <div class="flex items-center gap-3 min-w-0">
      <!-- Back button -->
      <button
        v-if="back"
        class="p-1.5 rounded-md text-ink-light hover:text-ink hover:bg-surface-raised transition-colors flex-shrink-0"
        @click="handleBack"
        aria-label="Atrás"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>

      <div class="min-w-0">
        <h1 class="text-[15px] font-semibold text-ink leading-none truncate">{{ title }}</h1>
        <p v-if="subtitle" class="text-[12px] text-ink-muted mt-1 truncate">{{ subtitle }}</p>
      </div>
    </div>

    <!-- Actions slot -->
    <div class="flex items-center gap-2 flex-shrink-0 ml-4">
      <slot />
    </div>
  </header>
</template>

<script setup>
import { getCurrentInstance } from "vue";
import { useRouter } from "vue-router";
const router = useRouter();
defineProps({
  title:    { type: String, required: true },
  subtitle: { type: String, default: "" },
  back:     { type: Boolean, default: false },
});
const emit = defineEmits(["back"]);
function handleBack() {
  const hasListener = !!getCurrentInstance()?.vnode?.props?.["onBack"];
  if (hasListener) {
    emit("back");
  } else {
    router.back();
  }
}
</script>
