<!--
  "Te regresaron para corregir": lo que Dirección o el revisor le devolvieron al
  usuario y todavía no reenvía, y las órdenes de venta que Dirección canceló y le toca
  rehacer (api/aprobaciones.get_mis_devueltos). Va en Inicio; no se pinta si no hay nada.
-->
<template>
  <div v-if="items.length" class="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3">
    <p class="text-[13px] font-semibold text-amber-950">
      Te {{ items.length === 1 ? "regresaron 1 documento" : `regresaron ${items.length} documentos` }} para corregir
    </p>
    <div class="mt-2 divide-y divide-amber-200">
      <RouterLink
        v-for="d in items" :key="`${d.doctype}/${d.name}`" :to="ruta(d)"
        class="flex items-start gap-3 py-2 hover:bg-amber-100/50 -mx-2 px-2 rounded-lg"
        @click="asegurarCompania(d.compania)"
      >
        <Icono nombre="regresar" class="w-4 h-4 text-amber-800 mt-0.5 flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <p class="text-[13px] font-medium text-amber-950">{{ d.etiqueta }} · <span class="font-mono">{{ d.name }}</span></p>
          <p v-if="d.motivo" class="text-[12.5px] text-amber-900 truncate">“{{ d.motivo }}”</p>
        </div>
        <span class="text-amber-800 text-[12px] font-medium whitespace-nowrap">{{ d.accion || "Corregir" }} ›</span>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import Icono from "@/components/Icono.vue";
import { asegurarCompania } from "@/composables/useCompany.js";
import { call } from "@/utils/frappe.js";

const items = ref([]);
const ruta = (d) => (d.ruta || "/").replace(/^\/costeo-yelke/, "") || "/";

onMounted(async () => {
  try { items.value = (await call("costeo_yelke.api.aprobaciones.get_mis_devueltos")).items || []; } catch { /* opcional */ }
});
</script>
