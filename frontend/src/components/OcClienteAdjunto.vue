<!--
  La orden de compra del CLIENTE, como archivo adjunto en vez de un número escrito a
  mano. Es el respaldo del pedido: sin ella no se valida la orden de venta (el candado
  real vive en el servidor, en validar_documento).

  El archivo se sube con `uploadFile` y queda adjunto al documento que se le indique:
  a la Orden de Venta cuando ya existe, o al Costeo mientras todavía no -- un archivo
  solo se puede colgar de un documento que ya está guardado.
-->
<template>
  <div>
    <div v-if="modelValue" class="flex items-center gap-2 rounded-lg border border-surface-border bg-white px-3 py-2">
      <svg class="w-4 h-4 text-ink-light flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
      <a :href="modelValue" target="_blank" class="text-[12.5px] text-brand-600 hover:underline truncate flex-1" :title="nombre">{{ nombre }}</a>
      <button v-if="!soloLectura" type="button" class="text-[11.5px] text-ink-muted hover:text-red-600 flex-shrink-0" @click="emit('quitar')">Quitar</button>
    </div>

    <label
      v-else-if="!soloLectura"
      class="flex items-center justify-center gap-2 h-[38px] rounded-lg border border-dashed border-surface-border bg-white text-[12.5px] text-ink-muted hover:border-brand-300 hover:text-brand-600 cursor-pointer"
      :class="{ 'opacity-60 pointer-events-none': subiendo }"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v12m0-12l-4 4m4-4l4 4M4 20h16"/>
      </svg>
      {{ subiendo ? "Subiendo…" : "Adjuntar la OC del cliente (PDF o imagen)" }}
      <input type="file" accept=".pdf,image/*" class="hidden" :disabled="subiendo" @change="emit('archivo', $event)" />
    </label>

    <p v-else class="text-[12px] text-ink-light">Sin archivo adjunto.</p>
  </div>
</template>

<script setup>
import { computed } from "vue";
const props = defineProps({
  modelValue: { type: String, default: "" },
  soloLectura: { type: Boolean, default: false },
  subiendo: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "archivo", "quitar"]);
// El valor es la RUTA del archivo; para mostrarlo basta el último tramo.
const nombre = computed(() => decodeURIComponent((props.modelValue || "").split("/").pop() || ""));
</script>
