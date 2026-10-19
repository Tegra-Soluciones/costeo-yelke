<!--
  Botón "Actividad · n" para el encabezado de cualquier documento. Abre la línea
  de tiempo y los comentarios en el panel lateral de Producción.
-->
<template>
  <button
    type="button" :disabled="!name"
    class="px-3 py-1.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 flex items-center gap-1.5 disabled:opacity-40"
    title="Actividad y comentarios" @click="abierto = true"
  >
    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h8M8 14h5M21 12a9 9 0 01-13.5 7.8L3 21l1.2-4.5A9 9 0 1121 12z"/></svg>
    Actividad
    <span v-if="cuenta" class="min-w-[18px] h-[18px] px-1 rounded-full bg-sky-100 text-sky-700 text-[10.5px] font-bold flex items-center justify-center">{{ cuenta }}</span>
  </button>

  <PanelLateral :abierto="abierto" eyebrow="Actividad" :titulo="name" :meta="etiqueta" @cerrar="abierto = false">
    <ActividadDocumento ref="lista" :doctype="doctype" :name="name" @cuenta="(n) => (cuenta = n)" />
  </PanelLateral>
</template>

<script setup>
import { ref, watch } from "vue";
import PanelLateral from "@/components/produccion/PanelLateral.vue";
import ActividadDocumento from "@/components/aprobacion/ActividadDocumento.vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, default: "" },
  etiqueta: { type: String, default: "Línea de tiempo y comentarios" },
});

const abierto = ref(false);
const cuenta = ref(0);
const lista = ref(null);

async function contar() {
  if (!props.name) return;
  try {
    const r = await call("costeo_yelke.api.actividad.get_cuenta_comentarios", { doctype: props.doctype, name: props.name });
    cuenta.value = r.comentarios || 0;
  } catch { /* el botón funciona igual sin el contador */ }
}

watch(() => [props.doctype, props.name], contar, { immediate: true });
defineExpose({ recargar: () => { contar(); lista.value?.recargar(); } });
</script>
