<!--
  Por asignar (solo Dirección, api/encargos.get_por_asignar): todo lo que ya se puede
  hacer en los proyectos activos, por proyecto · paso · lote, incluido lo que todavía
  no tiene documento ("Lote 1: faltan las órdenes de compra"). Lo que nadie tiene se
  asigna aquí mismo con el panel de asignaciones de siempre, ya con el paso y el lote
  puestos. El clic en la fila lleva al paso dentro del proyecto.
-->
<template>
  <div>
    <div class="px-4 lg:px-0 pt-3 flex items-center gap-3 flex-wrap">
      <div class="p-seg grid grid-cols-3 lg:inline-grid">
        <button v-for="[k, l] in FILTROS" :key="k" type="button" class="justify-center" :class="filtro === k ? 'on' : ''" @click="filtro = k">
          {{ l }} · {{ cuenta(k) }}
        </button>
      </div>
      <p class="p-meta flex-1 min-w-[220px]">Lo que ya puede empezarse o sigue pendiente en cada proyecto, y quién lo tiene.</p>
      <button type="button" class="p-btn-ghost h-8 px-2" :disabled="cargando" title="Actualizar" @click="cargar">
        <Icono nombre="actualizar" class="w-4 h-4" :class="cargando ? 'animate-spin' : ''" />
      </button>
    </div>

    <div v-if="cargando && !grupos.length" class="p-8 text-center p-meta">Cargando…</div>
    <p v-else-if="error" class="p-6 text-[13px] text-red-700">{{ error }}</p>
    <VacioEstado
      v-else-if="!visibles.length" icono="check-circulo"
      :titulo="filtro === 'sin' ? 'Todo tiene a alguien' : 'Nada pendiente'"
      detalle="Cuando un proyecto pase al siguiente paso, aparece aquí para asignarlo."
    />
    <div v-else class="px-4 lg:px-0 py-3 space-y-3">
      <section v-for="p in porProyecto" :key="p.costeo" class="p-panel overflow-hidden">
        <RouterLink :to="`/costeo/${encodeURIComponent(p.costeo)}`" class="px-4 pt-3 pb-2 flex items-baseline justify-between gap-3 border-b border-surface-border hover:bg-zinc-50">
          <div class="min-w-0">
            <p class="text-[14px] font-semibold truncate">{{ p.proyecto }}</p>
            <p class="p-meta truncate">{{ p.cliente }}</p>
          </div>
          <span class="text-[12px] text-ink-light whitespace-nowrap">Abrir proyecto ›</span>
        </RouterLink>
        <FilaLista
          v-for="g in p.grupos" :key="`${g.vista}|${g.lote}`"
          :estado="g.asignado.length ? 'wait' : 'bad'"
          :titulo="g.etiqueta + (g.lote ? ` · ${g.lote}` : '')"
          :meta="resumen(g)"
          @abrir="router.push(g.ruta)"
        >
          <template #derecha>
            <span v-if="g.asignado.length" class="text-[12px] text-ink-muted whitespace-nowrap flex-shrink-0 text-right">
              {{ g.asignado.map((a) => a.nombre).join(", ") }}
              <span class="block text-[11px] text-ink-light">{{ notaAsignado(g.asignado[0]) }}</span>
            </span>
            <template v-else>
              <span v-if="g.sin_documento" class="p-pill-wait flex-shrink-0">Sin empezar</span>
              <button type="button" class="p-btn-primary h-7 px-3 text-[12px] flex-shrink-0" @click.stop="asignar(g)">Asignar</button>
            </template>
          </template>
        </FilaLista>
      </section>
    </div>

    <PanelEncargos
      v-if="sel" :abierto="!!sel" :costeo="sel.costeo" :titulo="sel.proyecto"
      :paso-inicial="sel.vista" :lote-inicial="sel.lote" @cerrar="sel = null"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/utils/frappe.js";
import Icono from "@/components/Icono.vue";
import VacioEstado from "@/components/produccion/VacioEstado.vue";
import FilaLista from "@/components/produccion/FilaLista.vue";
import PanelEncargos from "@/components/encargos/PanelEncargos.vue";
import { version } from "@/composables/useEncargos.js";
import { haceCuanto } from "@/utils/formato.js";

const emit = defineEmits(["cuenta"]);
const router = useRouter();

const FILTROS = [["sin", "Sin asignar"], ["con", "Asignados"], ["todo", "Todo"]];
const filtro = ref("sin");
const grupos = ref([]);
const cargando = ref(false);
const error = ref("");
const sel = ref(null);

const pasa = (g, k) => k === "todo" || (k === "sin" ? !g.asignado.length : g.asignado.length > 0);
const cuenta = (k) => grupos.value.filter((g) => pasa(g, k)).length;
const visibles = computed(() => grupos.value.filter((g) => pasa(g, filtro.value)));
const porProyecto = computed(() => {
  const out = [];
  for (const g of visibles.value) {
    let p = out.find((x) => x.costeo === g.costeo);
    if (!p) out.push((p = { costeo: g.costeo, proyecto: g.proyecto, cliente: g.cliente, grupos: [] }));
    p.grupos.push(g);
  }
  return out;
});

// "Recibido sin facturar · MOROTEX ×2": el mismo pendiente en varios documentos va una vez.
function resumen(g) {
  const n = new Map();
  for (const x of g.pendientes) n.set(x.detalle, (n.get(x.detalle) || 0) + 1);
  return [...n].map(([d, k]) => (k > 1 ? `${d} ×${k}` : d)).join(" · ");
}

function notaAsignado(a) {
  const alcance = a.general ? "todo el proyecto" : a.todos_los_lotes ? "todos los lotes" : "";
  return [alcance, `desde ${haceCuanto(a.desde)}`].filter(Boolean).join(" · ");
}

async function cargar() {
  cargando.value = true; error.value = "";
  try {
    // Todas las compañías, como el resto del panel: con el filtro, en un celular con
    // otra compañía elegida (la de por omisión) no salía nada.
    const r = await call("costeo_yelke.api.encargos.get_por_asignar");
    grupos.value = r.grupos || [];
    emit("cuenta", r.sin_asignar || 0);
  } catch (e) { error.value = e.message || "No se pudo cargar."; }
  finally { cargando.value = false; }
}

function asignar(g) { sel.value = g; }

onMounted(cargar);
// Al asignar (PanelEncargos sube `version`) o cambiar de compañía, se recarga.
watch(version, cargar);
defineExpose({ cargar });
</script>
