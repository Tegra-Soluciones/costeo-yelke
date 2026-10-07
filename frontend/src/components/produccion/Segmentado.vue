<!--
  Control segmentado: filtro de producto del lote, "Viendo" de un taller, y las
  secciones de las bandejas (docs/plan-ui-produccion.md §4.3).

  `opciones`: [{ valor, texto, conteo, caliente }]
     conteo: número a la derecha del texto
     caliente: lo pinta en naranja (pendientes), si no, gris
-->
<template>
  <div class="p-seg">
    <button
      v-for="o in opciones" :key="o.valor" type="button"
      :class="{ on: o.valor === modelValue }"
      @click="emit('update:modelValue', o.valor)"
    >
      {{ o.texto }}
      <span v-if="o.conteo != null && o.conteo !== 0" :class="o.caliente ? 'p-count-hot' : 'p-count'">{{ o.conteo }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  opciones: { type: Array, default: () => [] },
  modelValue: { type: [String, Number], default: "" },
});
const emit = defineEmits(["update:modelValue"]);
</script>
