<!--
  Mis pendientes (Inicio): lo que le toca a esta persona en TODOS los proyectos activos,
  una tarjeta por vista que tiene en "editar" (api/mi_panel.py). Cada renglón lleva al
  lugar exacto del proyecto: paso, vista de Producción y lote.
-->
<template>
  <section v-if="cargando || secciones.length">
    <div class="flex items-baseline justify-between mb-2">
      <p class="text-[14px] font-semibold text-ink">Mis pendientes</p>
      <p v-if="!cargando" class="p-meta">{{ total }} en {{ proyectos }} proyecto(s) activo(s)</p>
    </div>
    <div v-if="cargando && !secciones.length" class="p-panel p-6 text-center p-meta">Buscando lo que te toca…</div>
    <div class="grid lg:grid-cols-2 gap-3">
      <div v-for="sec in secciones" :key="sec.clave" class="p-panel">
        <div class="flex items-center justify-between px-4 pt-3 pb-2">
          <p class="p-eyebrow">{{ sec.etiqueta }}</p>
          <span class="p-count-hot !ml-0">{{ sec.total }}</span>
        </div>
        <FilaLista
          v-for="(f, i) in sec.filas.slice(0, abiertas[sec.clave] ? sec.filas.length : 4)" :key="i"
          estado="wait" :titulo="f.titulo" :meta="`${f.detalle} · ${f.proyecto}${f.cliente ? ' · ' + f.cliente : ''}`"
          @abrir="router.push(f.ruta)"
        />
        <button
          v-if="sec.filas.length > 4 && !abiertas[sec.clave]" type="button"
          class="w-full px-4 py-2 text-[12.5px] text-brand-600 hover:text-brand-700 text-left border-t border-surface-border"
          @click="abiertas[sec.clave] = true"
        >Ver {{ sec.filas.length - 4 }} más{{ sec.total > sec.filas.length ? ` (de ${sec.total})` : "" }}</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import FilaLista from "@/components/produccion/FilaLista.vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({ company: { type: String, default: "" }, recargar: { type: Number, default: 0 } });
const router = useRouter();
const secciones = ref([]);
const proyectos = ref(0);
const cargando = ref(false);
const abiertas = reactive({});
const total = computed(() => secciones.value.reduce((a, s) => a + s.total, 0));

async function cargar() {
  cargando.value = true;
  try {
    const r = await call("costeo_yelke.api.mi_panel.get_mi_panel", { company: props.company || undefined });
    secciones.value = r.secciones || [];
    proyectos.value = r.proyectos_activos || 0;
  } catch { secciones.value = []; }
  finally { cargando.value = false; }
}
watch(() => [props.company, props.recargar], cargar, { immediate: true });
</script>
