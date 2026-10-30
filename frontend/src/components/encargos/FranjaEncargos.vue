<!--
  En el proyecto: lo que esta persona tiene asignado aquí (abierto). "Abrir" lleva al
  paso de la asignación sin salir del proyecto.
-->
<template>
  <div v-if="mios.length" class="p-panel border-brand-200 overflow-hidden">
    <div class="px-4 pt-3 pb-1 flex items-center gap-2">
      <span class="p-dot p-dot-now"></span>
      <p class="text-[13px] font-semibold text-ink">{{ mios.length === 1 ? "Te asignaron esto" : `Te asignaron ${mios.length} cosas aquí` }}</p>
    </div>
    <FilaEncargo v-for="f in mios" :key="f.name" :f="f" vista="para_mi" :mostrar-proyecto="false" con-regla en-proyecto
                 @abrir="emit('ir', f)" @cambio="emit('cambio')" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import FilaEncargo from "@/components/encargos/FilaEncargo.vue";

const props = defineProps({ encargos: { type: Array, default: () => [] } });
const emit = defineEmits(["ir", "cambio"]);
const mios = computed(() => props.encargos.filter((f) => f.es_mio && f.estado === "abierto"));
</script>
