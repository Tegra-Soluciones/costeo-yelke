<template>
  <!-- "Para": a qué talleres va este proceso / observación / tabla / archivo de la
       OM general. Ninguno marcado = todos los talleres. -->
  <div class="flex flex-wrap items-center gap-1">
    <span class="text-[10.5px] text-ink-light mr-0.5">Para:</span>
    <button
      type="button" :disabled="disabled"
      class="text-[10.5px] px-1.5 py-px rounded-full ring-1 transition-colors"
      :class="!modelValue.length ? 'ring-brand-300 bg-brand-50 text-brand-700' : 'ring-surface-border text-ink-light hover:text-ink'"
      @click="$emit('update:modelValue', [])"
    >Todos</button>
    <button
      v-for="t in talleres" :key="t" type="button" :disabled="disabled"
      class="text-[10.5px] px-1.5 py-px rounded-full ring-1 transition-colors"
      :class="modelValue.includes(t) ? 'ring-brand-400 bg-brand-500 text-white' : 'ring-surface-border text-ink-muted hover:text-ink'"
      @click="toggle(t)"
    >{{ t }}</button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  talleres: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
function toggle(t) {
  const v = [...props.modelValue];
  const i = v.indexOf(t);
  if (i >= 0) v.splice(i, 1); else v.push(t);
  emit("update:modelValue", v);
}
</script>
