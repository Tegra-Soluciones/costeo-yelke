<!--
  Lo que se capturó en la orden de compra del taller (Preparación · Órdenes a
  talleres), a la vista dentro de su encargo: a dónde entrega cada pieza al
  terminar (api/entregas_taller.py). Su orden de manufactura no va aquí: ya está en
  el botón «Orden de manufactura» del encabezado del taller. Solo lectura.
-->
<template>
  <div class="space-y-3">
    <details class="p-panel group">
      <summary class="px-4 py-3 cursor-pointer list-none flex items-center justify-between gap-2">
        <span class="text-[13px] font-medium text-ink">Al terminar, entregar a</span>
        <span class="flex items-center gap-2"><span class="p-meta">{{ resumenEntregas }}</span><svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></span>
      </summary>
      <div class="px-4 pb-4">
        <p v-if="!entregas" class="p-meta">Cargando…</p>
        <p v-else-if="!entregas.indicar" class="p-meta">La orden de este taller no indica a dónde entregar.</p>
        <p v-else-if="!entregas.filas.length" class="p-meta">No se pudo deducir del flujo y no se capturó en la orden.</p>
        <ul v-else class="divide-y divide-surface-border rounded-lg border border-surface-border">
          <li v-for="(f, i) in entregas.filas" :key="i" class="px-3 py-2">
            <p class="text-[12.5px] text-ink"><span class="font-medium">{{ f.piezas || "—" }}</span>
              <span v-if="varios && f.producto" class="text-ink-light"> · {{ entregas.nombres[f.producto] || f.producto }}</span></p>
            <p class="text-[12.5px] text-brand-700 font-medium mt-0.5">→ {{ f.destino || "—" }}</p>
            <p v-if="f.entregar_a && f.entregar_a === entregas.supplier" class="text-[11.5px] text-ink-muted">Se queda en este taller para el siguiente paso</p>
            <p v-else-if="f.direccion" class="text-[11.5px] text-ink-muted whitespace-pre-line">{{ f.direccion }}</p>
          </li>
        </ul>
      </div>
    </details>

  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({ po: { type: String, required: true } });
const entregas = ref(null);

const varios = computed(() => new Set((entregas.value?.filas || []).map((f) => f.producto).filter(Boolean)).size > 1);
const resumenEntregas = computed(() => {
  const e = entregas.value;
  if (!e) return "";
  if (!e.indicar || !e.filas.length) return "sin indicar";
  return `${e.filas.length} destino${e.filas.length === 1 ? "" : "s"}${e.editadas ? " · editado a mano" : ""}`;
});

watch(() => props.po, async (po) => {
  entregas.value = null;
  if (!po) return;
  try { entregas.value = await call("costeo_yelke.api.entregas_taller.get_entregas", { po }); }
  catch { entregas.value = { indicar: false, filas: [], nombres: {} }; }
}, { immediate: true });
</script>
