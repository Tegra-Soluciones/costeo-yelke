<template>
  <Teleport to="body">
    <Transition name="overlay">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        @click.self="$emit('cancel')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" />

        <!-- Panel -->
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 flex flex-col gap-4">
          <!-- Icon -->
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
              :class="iconBg"
            >
              <svg v-if="variant === 'danger'" class="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
              <svg v-else class="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
            </div>
            <div>
              <h3 class="text-sm font-semibold text-gray-900">{{ title }}</h3>
              <p class="text-xs text-gray-500 mt-0.5">{{ message }}</p>
            </div>
          </div>

          <!-- Extra slot -->
          <slot />

          <!-- Buttons -->
          <div class="flex gap-2 justify-end pt-1">
            <button
              class="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              @click="$emit('cancel')"
            >
              {{ cancelLabel }}
            </button>
            <button
              :disabled="loading"
              class="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-60 flex items-center gap-2"
              :class="confirmCls"
              @click="$emit('confirm')"
            >
              <svg v-if="loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ loading ? 'Procesando…' : confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: Boolean,
  title:        { type: String, default: "¿Confirmar acción?" },
  message:      { type: String, default: "" },
  confirmLabel: { type: String, default: "Confirmar" },
  cancelLabel:  { type: String, default: "Cancelar" },
  variant:      { type: String, default: "danger" }, // 'danger' | 'warning'
  loading:      { type: Boolean, default: false },
});

defineEmits(["update:modelValue", "confirm", "cancel"]);

const iconBg     = computed(() => props.variant === "danger" ? "bg-red-100"  : "bg-amber-100");
const confirmCls = computed(() => props.variant === "danger" ? "bg-red-600 hover:bg-red-700" : "bg-amber-500 hover:bg-amber-600");
</script>

<style scoped>
.overlay-enter-active { transition: opacity 0.15s ease; }
.overlay-leave-active { transition: opacity 0.1s ease; }
.overlay-enter-from, .overlay-leave-to { opacity: 0; }
.overlay-enter-active .relative, .overlay-leave-active .relative { transition: transform 0.15s ease, opacity 0.15s ease; }
.overlay-enter-from .relative, .overlay-leave-to .relative { transform: scale(0.95); opacity: 0; }
</style>
