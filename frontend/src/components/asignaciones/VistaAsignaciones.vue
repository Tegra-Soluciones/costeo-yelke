<!--
  Asignaciones (api/encargos.py, docs/plan-encargos.md) con el diseño de Producción:
  menú a la izquierda (persona o proyecto; o "Me asignaron" /
  "Asigné"), lista compacta a la derecha y el detalle en el panel lateral.

    modo "equipo"  todas las del equipo (Dirección / acceso total)
    modo "mias"    las que me asignaron y las que asigné
-->
<template>
  <div class="space-y-5">
    <div class="flex gap-5 items-start" :class="movil ? 'flex-col' : ''">
      <!-- Menú -->
      <select v-if="movil" v-model="grupo" class="p-field">
        <option v-for="g in grupos" :key="g.clave" :value="g.clave">{{ g.nombre }}{{ g.abiertas ? ` (${g.abiertas})` : "" }}</option>
      </select>
      <aside v-else class="w-[248px] flex-shrink-0 sticky top-0">
        <select v-if="modo === 'equipo'" v-model="agrupar" class="p-field h-8 text-[12.5px] mb-3">
          <option value="persona">Por persona</option>
          <option value="proyecto">Por proyecto</option>
        </select>
        <div class="space-y-0.5">
          <template v-for="(g, i) in grupos" :key="g.clave">
            <div v-if="i === 1 && modo === 'equipo'" class="p-rail-group !pt-3">{{ agrupar === "persona" ? "Personas" : "Proyectos" }}</div>
            <button type="button" class="p-rail-item" :class="{ on: grupo === g.clave }" :title="g.detalle || g.nombre" @click="grupo = g.clave">
              <span v-if="agrupar === 'persona' && g.persona" class="w-5 h-5 rounded-full flex items-center justify-center text-[9.5px] font-semibold flex-shrink-0" :class="colorAvatar(g.clave)">{{ iniciales(g.nombre) }}</span>
              <span v-else class="p-dot flex-shrink-0" :class="g.vencidas ? 'p-dot-bad' : g.abiertas ? 'p-dot-wait' : 'p-dot-off'"></span>
              <span class="truncate">{{ g.nombre }}</span>
              <span v-if="g.vencidas" class="p-count-hot !bg-red-500" :title="`${g.vencidas} vencida(s)`">{{ g.abiertas }}</span>
              <span v-else class="p-count">{{ g.abiertas || "" }}</span>
            </button>
          </template>
        </div>
      </aside>

      <!-- Lista -->
      <section class="flex-1 min-w-0 w-full p-panel overflow-hidden">
        <div class="px-4 pt-4 pb-3 flex items-start justify-between gap-3 flex-wrap border-b border-surface-border">
          <div class="min-w-0">
            <p class="text-[15px] font-semibold text-ink truncate">{{ actual?.nombre }}</p>
            <p v-if="actual?.detalle" class="p-meta truncate">{{ actual.detalle }}</p>
          </div>
          <div class="flex items-center gap-2">
            <RouterLink v-if="actual?.ruta" :to="actual.ruta" class="p-btn-ghost h-7 px-2 text-[12.5px]">Abrir proyecto ›</RouterLink>
            <select v-model="filtro" class="p-field h-8 w-auto text-[12.5px]">
              <option v-for="[k, l] in FILTROS" :key="k" :value="k">{{ l }} ({{ cuenta(k) }})</option>
            </select>
            <button type="button" class="p-btn-ghost h-7 px-2" :disabled="cargando" title="Actualizar" @click="cargar">
              <Icono nombre="actualizar" class="w-4 h-4" :class="cargando ? 'animate-spin' : ''" />
            </button>
          </div>
        </div>
        <p v-if="error" class="px-4 py-3 text-[12.5px] text-red-700">{{ error }}</p>
        <div v-if="cargando && !filas.length" class="p-10 text-center p-meta">Cargando asignaciones…</div>
        <div v-else-if="!lista.length" class="py-6">
          <VacioEstado
            :icono="filtro === 'cerradas' ? 'reloj' : 'check-circulo'"
            :titulo="{ abiertas: 'Nada abierto', vencidas: 'Nada vencido', cerradas: 'Nada cerrado en los últimos 7 días' }[filtro]"
            detalle="Para asignar un paso, abre el proyecto y usa el botón «Asignar»."
          />
        </div>
        <template v-else>
          <FilaAsignacion
            v-for="f in lista" :key="f.name" :f="f" :class="sel?.name === f.name ? '!bg-zinc-50' : ''"
            :quien="quienDe" :con-proyecto="!(modo === 'equipo' && agrupar === 'proyecto' && grupo !== TODOS)"
            @abrir="sel = f"
          />
        </template>
      </section>
    </div>

    <DetalleAsignacion :f="sel" @cerrar="sel = null" @cambio="cargar" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import Icono from "@/components/Icono.vue";
import VacioEstado from "@/components/produccion/VacioEstado.vue";
import DetalleAsignacion from "@/components/asignaciones/DetalleAsignacion.vue";
import FilaAsignacion from "@/components/asignaciones/FilaAsignacion.vue";
import { getEquipo, getMios, version } from "@/composables/useEncargos.js";
import { colorAvatar, iniciales } from "@/utils/formato.js";

const props = defineProps({
  modo: { type: String, default: "equipo" },
  movil: { type: Boolean, default: false },
});
const TODOS = "__todos";
const FILTROS = [["abiertas", "Abiertas"], ["vencidas", "Vencidas"], ["cerradas", "Cerradas"]];

const filas = ref([]);
const cargando = ref(false);
const error = ref("");
const agrupar = ref("persona");
const grupo = ref(TODOS);
const filtro = ref("abiertas");
const sel = ref(null);

const urgente = (f) => f.estado === "abierto" && (f.vencido || f.vence_hoy);
const pasa = (f, k) => (k === "abiertas" ? f.estado === "abierto" : k === "vencidas" ? urgente(f) : f.estado !== "abierto");

const grupos = computed(() => {
  const base = (clave, nombre, extra = {}) => ({ clave, nombre, abiertas: 0, vencidas: 0, filas: [], ...extra });
  const out = new Map();
  if (props.modo === "mias") {
    out.set("mi", base("mi", "Me asignaron"));
    out.set("yo", base("yo", "Asigné"));
    for (const f of filas.value) out.get(f._grupo).filas.push(f);
  } else {
    out.set(TODOS, base(TODOS, agrupar.value === "persona" ? "Todo el equipo" : "Todos los proyectos", { filas: filas.value }));
    for (const f of filas.value) {
      const clave = agrupar.value === "persona" ? f.para : f.costeo;
      if (!out.has(clave)) {
        out.set(clave, agrupar.value === "persona"
          ? base(clave, f.para_nombre, { persona: true })
          : base(clave, f.proyecto, { detalle: [f.cliente, f.costeo].filter(Boolean).join(" · "),
              ruta: f.ruta.split("?")[0] + (f.compania ? `?compania=${encodeURIComponent(f.compania)}` : "") }));
      }
      out.get(clave).filas.push(f);
    }
  }
  for (const g of out.values()) {
    g.abiertas = g.filas.filter((f) => f.estado === "abierto").length;
    g.vencidas = g.filas.filter(urgente).length;
  }
  const [primero, ...resto] = [...out.values()];
  return props.modo === "mias" ? [primero, ...resto]
    : [primero, ...resto.sort((a, b) => b.vencidas - a.vencidas || b.abiertas - a.abiertas || a.nombre.localeCompare(b.nombre))];
});
const actual = computed(() => grupos.value.find((g) => g.clave === grupo.value) || grupos.value[0]);
const cuenta = (k) => (actual.value?.filas || []).filter((f) => pasa(f, k)).length;
const lista = computed(() => (actual.value?.filas || []).filter((f) => pasa(f, filtro.value)));
const quienDe = computed(() => {
  if (props.modo === "mias") return grupo.value === "yo" ? "para" : "de";
  return agrupar.value === "persona" && grupo.value !== TODOS ? "de" : "ambos";
});

watch(agrupar, () => { grupo.value = TODOS; });
watch(grupos, (gs) => { if (!gs.some((g) => g.clave === grupo.value)) grupo.value = gs[0]?.clave; });

async function cargar() {
  cargando.value = true; error.value = "";
  try {
    if (props.modo === "mias") {
      // Sin filtro de compañía: las asignaciones son de la persona (el contador del
      // menú también las cuenta todas); cada renglón dice si es de otra compañía.
      const r = await getMios();
      filas.value = [...(r.para_mi || []).map((f) => ({ ...f, _grupo: "mi" })), ...(r.encargue || []).map((f) => ({ ...f, _grupo: "yo" }))];
      if (grupo.value === TODOS) grupo.value = (r.para_mi || []).length || !(r.encargue || []).length ? "mi" : "yo";
    } else {
      filas.value = (await getEquipo()).encargos || [];
    }
    if (sel.value) sel.value = filas.value.find((f) => f.name === sel.value.name) || null;
  } catch (e) { error.value = e.message || "No se pudieron cargar las asignaciones."; }
  finally { cargando.value = false; }
}
watch(() => [version.value, props.modo], cargar);
onMounted(cargar);
</script>
