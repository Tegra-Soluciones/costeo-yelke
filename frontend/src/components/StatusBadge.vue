<template>
  <span
    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide"
    :style="style"
  >
    <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: cfg.dot }"></span>
    {{ modelValue }}
  </span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "Borrador" },
});

const map = {
  "Borrador":       { bg: "#f4f4f5", text: "#52525b", dot: "#a1a1aa" },
  "Cotizado":       { bg: "#eff6ff", text: "#1d4ed8", dot: "#3b82f6" },
  "Orden de Venta": { bg: "#faf5ff", text: "#6d28d9", dot: "#8b5cf6" },
  "En Producción":  { bg: "#fff4ef", text: "#c53a06", dot: "#ff6b15" },
  "Completado":     { bg: "#f0fdf4", text: "#15803d", dot: "#22c55e" },
  "Cancelado":      { bg: "#fef2f2", text: "#b91c1c", dot: "#ef4444" },
};

const cfg = computed(() => map[props.modelValue] || map["Borrador"]);
const style = computed(() => ({
  background: cfg.value.bg,
  color: cfg.value.text,
}));
</script>
