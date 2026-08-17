<template>
  <button
    type="button"
    class="w-full text-left rounded-xl border p-3 transition-colors"
    :class="active ? 'border-brand-300 bg-brand-50/40 ring-1 ring-brand-200' : 'border-surface-border bg-white hover:border-brand-200 hover:bg-surface-raised/60'"
    @click="emit('select')"
  >
    <div class="flex items-center justify-between gap-2 mb-2.5">
      <div class="min-w-0">
        <p class="text-[13px] font-semibold text-ink truncate">{{ title }}</p>
        <p v-if="subtitle" class="text-[11.5px] text-ink-muted truncate">{{ subtitle }}</p>
      </div>
      <span v-if="badge" class="text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0" :class="badgeClass || 'bg-surface-raised text-ink-muted'">{{ badge }}</span>
    </div>

    <!-- Mini-pipeline: pasos conectados por una línea, cada uno con su estado -->
    <div class="flex items-center">
      <template v-for="(s, i) in steps" :key="s.key">
        <div class="flex items-center gap-1.5 min-w-0" :class="i > 0 ? 'flex-1' : ''">
          <div v-if="i > 0" class="h-px flex-1 min-w-[8px]" :class="s.status === 'pending' ? 'bg-surface-border' : 'bg-brand-300'"></div>
          <div
            class="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-semibold"
            :class="{
              'bg-green-500 text-white': s.status === 'done',
              'bg-brand-500 text-white': s.status === 'active',
              'bg-surface-raised text-ink-light border border-surface-border': s.status === 'pending',
            }"
            :title="s.label"
          >
            <svg v-if="s.status === 'done'" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
            <span v-else>{{ i + 1 }}</span>
          </div>
        </div>
      </template>
    </div>
    <p class="text-[10.5px] text-ink-light mt-1.5">
      <span v-for="(s, i) in steps" :key="'l' + s.key" :class="s.status === 'pending' ? '' : 'text-ink-muted font-medium'">{{ s.label }}<span v-if="i < steps.length - 1"> · </span></span>
    </p>
  </button>
</template>

<script setup>
// Tarjeta genérica de "lote": un mini-pipeline de pasos (ej. OC -> Recibo, o
// SCO -> Transferencia -> Recibo) con su estado. La misma tarjeta sirve para
// materia prima y subcontratación, solo cambia qué `steps` se le pasan.
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  badge: { type: String, default: "" },
  badgeClass: { type: String, default: "" },
  active: { type: Boolean, default: false },
  // steps: [{ key, label, status: 'done' | 'active' | 'pending' }]
  steps: { type: Array, required: true },
});
const emit = defineEmits(["select"]);
</script>
