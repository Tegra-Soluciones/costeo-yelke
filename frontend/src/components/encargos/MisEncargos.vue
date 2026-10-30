<!--
  Inicio: "Te asignaron" (abiertas, vencidas primero) y "Asignaste" (abiertas y cerradas
  de los últimos días), en renglones compactos; el detalle abre en el panel lateral.
  No se pinta si no hay nada (api/encargos.get_mios).
-->
<template>
  <section v-if="paraMi.length || asigne.length" class="grid gap-3" :class="paraMi.length && asigne.length ? 'lg:grid-cols-2' : ''">
    <div v-for="b in bloques" :key="b.clave" class="p-panel self-start overflow-hidden">
      <div class="flex items-center justify-between px-4 pt-3 pb-2.5 border-b border-surface-border">
        <p class="text-[14px] font-semibold text-ink">{{ b.titulo }}</p>
        <span v-if="b.hot" class="p-count-hot !ml-0">{{ b.hot }}</span>
        <p v-else class="p-meta">{{ b.nota }}</p>
      </div>
      <FilaAsignacion v-for="f in b.filas.slice(0, LIMITE)" :key="f.name" :f="f" :quien="b.quien" @abrir="sel = f" />
      <RouterLink v-if="b.filas.length > LIMITE" to="/asignaciones" class="block px-4 py-2.5 text-[12.5px] text-brand-600 hover:text-brand-700">
        Ver las {{ b.filas.length }} ›
      </RouterLink>
    </div>
    <DetalleAsignacion :f="sel" @cerrar="sel = null" @cambio="cargar" />
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import DetalleAsignacion from "@/components/asignaciones/DetalleAsignacion.vue";
import FilaAsignacion from "@/components/asignaciones/FilaAsignacion.vue";
import { getMios, version } from "@/composables/useEncargos.js";

const props = defineProps({ company: { type: String, default: "" }, recargar: { type: Number, default: 0 } });
const LIMITE = 5;
const paraMi = ref([]);
const asigne = ref([]);
const sel = ref(null);

const bloques = computed(() => {
  const out = [];
  if (paraMi.value.length) out.push({ clave: "mi", titulo: "Te asignaron", filas: paraMi.value, quien: "de", hot: paraMi.value.length });
  if (asigne.value.length) {
    const abiertas = asigne.value.filter((f) => f.estado === "abierto").length;
    out.push({ clave: "yo", titulo: "Asignaste", filas: asigne.value, quien: "para",
      nota: `${abiertas} abierta(s) · ${asigne.value.length - abiertas} cerrada(s) esta semana` });
  }
  return out;
});

async function cargar() {
  try {
    const r = await getMios();  // de todas las compañías, como el contador del menú
    paraMi.value = (r.para_mi || []).filter((f) => f.estado === "abierto");
    asigne.value = r.encargue || [];
  } catch { /* Inicio funciona igual sin esto */ }
}
watch(() => [props.recargar, version.value], cargar, { immediate: true });
</script>
