<!--
  Proyectos (solo Director): cada costeo vivo con su etapa en el ciclo, lo
  entregado, los encargos a taller recibidos y sus alertas (api/direccion.get_proyectos).
-->
<template>
  <div>
    <div class="px-4 lg:px-0 pt-3">
      <div class="p-seg w-full lg:w-auto grid grid-cols-3 lg:inline-grid">
        <button
          v-for="[k, l] in GRUPOS" :key="k" type="button"
          class="justify-center" :class="grupo === k ? 'on' : ''" @click="grupo = k"
        >{{ l }} · {{ cuenta(k) }}</button>
      </div>
    </div>

    <div v-if="cargando && !proyectos.length" class="p-8 text-center p-meta">Cargando proyectos…</div>
    <p v-else-if="error" class="p-6 text-[13px] text-red-700">{{ error }}</p>
    <div v-else class="px-4 lg:px-0 py-3 grid gap-2.5 lg:grid-cols-2">
      <RouterLink
        v-for="p in visibles" :key="p.name" :to="`/costeo/${encodeURIComponent(p.name)}`"
        class="p-panel px-4 py-3.5 block hover:bg-zinc-50 active:bg-zinc-50"
        @click="asegurarCompania(p.compania)"
      >
        <p v-if="p.compania" class="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-ink-light truncate mb-0.5">{{ p.compania }}</p>
        <div class="flex items-start gap-3">
          <div class="flex-1 min-w-0">
            <p class="text-[14.5px] font-semibold leading-tight truncate">{{ p.titulo }}</p>
            <p class="p-meta truncate">{{ p.cliente }}<template v-if="p.documento"> · {{ p.documento }}</template></p>
          </div>
          <div class="text-right flex-shrink-0">
            <p v-if="p.monto != null" class="text-[14px] font-semibold tabular-nums">{{ dineroCorto(p.monto, p.moneda) }}</p>
            <p class="text-[11px] text-ink-light">entrega {{ p.entrega ? fecha(p.entrega) : "—" }}</p>
          </div>
        </div>
        <div class="flex items-center gap-1 mt-3">
          <span v-for="(e, i) in ETAPAS" :key="e" class="h-1.5 flex-1 rounded-full" :class="colorEtapa(p, i + 1)"></span>
        </div>
        <p class="text-[11.5px] text-ink-muted mt-1.5">
          <template v-if="p.etapa >= 6">Completado · entregado y facturado</template>
          <template v-else>Va en <b class="text-ink font-medium">{{ ETAPAS[p.etapa - 1] }}</b> · paso {{ p.etapa }} de 6</template>
        </p>
        <div class="flex items-center gap-2 mt-2.5">
          <div class="flex-1 h-1 bg-zinc-100 rounded"><div class="h-1 rounded" :class="p.entregado_pct >= 100 ? 'bg-emerald-500' : 'bg-sky-500'" :style="`width:${Math.min(100, p.entregado_pct)}%`"></div></div>
          <span class="text-[11.5px] text-ink-muted tabular-nums whitespace-nowrap">{{ p.entregado_pct }} % entregado</span>
        </div>
        <p v-if="p.encargos[1]" class="text-[11.5px] text-ink-light mt-1">{{ p.encargos[0] }} de {{ p.encargos[1] }} órdenes a taller recibidas</p>
        <div v-for="(a, i) in p.alertas" :key="i" class="mt-2.5 rounded-xl border px-3.5 py-2 text-[12.5px] leading-snug flex gap-2"
             :class="a.tono === 'bad' ? 'bg-red-50 border-red-200 text-red-800' : 'bg-amber-50 border-amber-200 text-amber-900'">
          <span>{{ a.tono === "bad" ? "⛔" : "⚠️" }}</span><span>{{ a.texto }}</span>
        </div>
      </RouterLink>
      <p v-if="!visibles.length" class="p-meta text-center py-10 lg:col-span-2">Nada aquí.</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { asegurarCompania } from "@/composables/useCompany.js";
import { call } from "@/utils/frappe.js";
import { dineroCorto, fecha } from "@/utils/formato.js";

const props = defineProps({ grupoInicial: { type: String, default: "activos" } });
const emit = defineEmits(["cuenta"]);

const ETAPAS = ["Costeo", "Cotización", "OV", "Producción", "Entrega", "Factura"];
const GRUPOS = [["activos", "Activos"], ["atrasados", "Atrasados"], ["completados", "Completados"]];

const proyectos = ref([]);
const cargando = ref(false);
const error = ref("");
const grupo = ref(props.grupoInicial);

const visibles = computed(() => proyectos.value.filter((p) => p.grupo === grupo.value));
const cuenta = (g) => proyectos.value.filter((p) => p.grupo === g).length;

function colorEtapa(p, n) {
  if (n < p.etapa || p.etapa >= 6) return "bg-emerald-500";
  if (n === p.etapa) return p.grupo === "atrasados" ? "bg-red-500" : "bg-brand-500";
  return "bg-zinc-200";
}

async function cargar() {
  cargando.value = true;
  error.value = "";
  try {
    proyectos.value = (await call("costeo_yelke.api.direccion.get_proyectos")).proyectos || [];
    emit("cuenta", cuenta("atrasados"));
  } catch (e) {
    error.value = e.message || "No se pudieron cargar los proyectos.";
  } finally {
    cargando.value = false;
  }
}

onMounted(cargar);
defineExpose({ recargar: cargar, verGrupo: (g) => (grupo.value = g) });
</script>
