<!--
  Actividad de un documento como sección plegable al final de un panel lateral
  (Producción): el panel ya ocupa el lado derecho, así que la línea de tiempo va
  dentro y no en un panel encima del otro.
-->
<template>
  <details class="mt-6 border-t border-surface-border pt-4 group" :open="abierta" @toggle="(e) => (abierta = e.target.open)">
    <summary class="list-none cursor-pointer flex items-center justify-between">
      <span class="p-eyebrow">Actividad<template v-if="cuenta"> · {{ cuenta }} comentario{{ cuenta === 1 ? "" : "s" }}</template></span>
      <span class="text-ink-light group-open:rotate-90 transition">›</span>
    </summary>
    <div v-if="abierta" class="mt-3">
      <ActividadDocumento :doctype="doctype" :name="name" :ultimos="5" @cuenta="(n) => (cuenta = n)" />
    </div>
  </details>
</template>

<script setup>
import { ref, watch } from "vue";
import ActividadDocumento from "@/components/aprobacion/ActividadDocumento.vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
});

const abierta = ref(false);
const cuenta = ref(0);

watch(() => [props.doctype, props.name], async () => {
  abierta.value = false;
  try {
    cuenta.value = (await call("costeo_yelke.api.actividad.get_cuenta_comentarios", { doctype: props.doctype, name: props.name })).comentarios || 0;
  } catch { cuenta.value = 0; }
}, { immediate: true });
</script>
