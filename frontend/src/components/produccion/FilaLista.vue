<!--
  Una fila de lista: punto de estado · título + meta · slot derecho (pasos
  compactos o pills) · chevron. El clic abre (docs/plan-ui-produccion.md §4.3).

  Las listas de Producción SOLO muestran el estado; el detalle se abre en un panel
  lateral o en una sub-pantalla, nunca dentro de la fila.

  `estatica` = fila que no se abre (p. ej. la cadena final en espera, o un renglón
  que solo lleva una acción suelta como "Registrar devolución").
-->
<template>
  <component
    :is="estatica ? 'div' : 'button'"
    class="p-row"
    :class="{ static: estatica }"
    :type="estatica ? undefined : 'button'"
    @click="!estatica && emit('abrir')"
  >
    <span v-if="orden !== null && orden !== undefined" class="text-[11px] font-mono text-ink-light w-4 flex-shrink-0">{{ orden }}</span>
    <EstadoPunto v-else-if="estado" :estado="estado" />

    <div class="flex-1 min-w-0">
      <p class="text-[13.5px] font-medium truncate">
        <slot name="titulo">{{ titulo }}</slot>
      </p>
      <p v-if="meta || $slots.meta" class="p-meta truncate"><slot name="meta">{{ meta }}</slot></p>
    </div>

    <slot name="derecha" />
    <span v-if="!estatica" class="text-ink-light flex-shrink-0">›</span>
  </component>
</template>

<script setup>
import EstadoPunto from "@/components/produccion/EstadoPunto.vue";

defineProps({
  titulo: { type: String, default: "" },
  meta: { type: String, default: "" },
  estado: { type: String, default: "" },
  // Número de orden a la izquierda (talleres, cadena final). Sustituye al punto.
  orden: { type: [Number, String], default: null },
  estatica: { type: Boolean, default: false },
});
const emit = defineEmits(["abrir"]);
</script>
