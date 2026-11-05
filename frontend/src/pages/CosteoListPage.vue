<template>
  <div class="flex flex-col h-full">

    <!-- Confirm: delete -->
    <ConfirmDialog
      v-model="confirmDelete.open"
      title="Eliminar Costeo"
      :message="`¿Seguro que deseas eliminar ${confirmDelete.name}? Esta acción no se puede deshacer.`"
      confirm-label="Eliminar"
      :loading="confirmDelete.loading"
      @confirm="doDelete"
      @cancel="confirmDelete.open = false"
    />

    <EncargarProyecto :abierto="encargarAbierto" @cerrar="encargarAbierto = false"
                      @creado="(r) => { showToast(`${r.titulo}: asignado a ${r.para}. Le llegó el aviso.`); load(); }" />

    <!-- Proyectos en tarjetas (api/direccion.get_lista_proyectos): la foto del primer
         producto que se costea, el cliente con su imagen, la etapa del ciclo y lo
         esencial de la venta -- el mismo lenguaje que ve Dirección. -->
    <div class="flex-1 overflow-y-auto bg-surface">
      <div class="max-w-[1320px] mx-auto px-6 py-5 space-y-4">
        <div class="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <h1 class="p-h1">Proyectos</h1>
            <p class="p-lede mt-0.5">{{ items.length }} proyecto{{ items.length === 1 ? "" : "s" }} · los más recientes primero</p>
          </div>
          <div class="flex items-center gap-2">
            <!-- Proyecto nuevo que lo costea otra persona (asignación, api/encargos.crear_proyecto). -->
            <button v-if="puedeEditar('costear') || puede('direccion')" type="button" class="p-btn-secondary" @click="encargarAbierto = true">
              <Icono nombre="persona" class="w-4 h-4" :grosor="2" /> Asignar proyecto
            </button>
            <button v-if="rutaPermitida('CosteoNuevo', 'editar')" type="button" class="p-btn-primary" @click="$router.push('/costeo/nuevo')">
              <Icono nombre="mas" class="w-4 h-4" :grosor="2.2" /> Nuevo costeo
            </button>
          </div>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <div class="relative w-full sm:w-72">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <input v-model="search" type="text" placeholder="Buscar proyecto, cliente o folio…" class="p-field pl-9" />
          </div>
          <select v-model="filterStatus" class="p-field w-auto min-w-[200px]">
            <option v-for="f in filtrosEtapa" :key="f.k" :value="f.k">{{ f.l }} ({{ f.n }})</option>
          </select>
        </div>

        <div v-if="loading" class="py-20 text-center p-meta">Cargando proyectos…</div>

        <div v-else-if="!filteredItems.length" class="p-panel py-14 text-center">
          <Icono nombre="paquete" class="w-10 h-10 mx-auto text-ink-xlight" :grosor="1.3" />
          <p class="text-[14px] font-semibold mt-3">No hay proyectos aquí</p>
          <p class="p-meta mt-1">Prueba con otro filtro o búsqueda.</p>
          <button v-if="rutaPermitida('CosteoNuevo', 'editar')" type="button" class="mt-3 text-[13px] text-brand-600 font-medium" @click="$router.push('/costeo/nuevo')">Crear un costeo →</button>
        </div>

        <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <RouterLink
            v-for="p in filteredItems" :key="p.name" :to="`/costeo/${encodeURIComponent(p.name)}`"
            class="group p-panel overflow-hidden flex flex-col hover:border-brand-200 hover:shadow-md transition-all"
          >
            <!-- Foto del primer producto -->
            <div class="relative aspect-[16/9] bg-zinc-50 border-b border-surface-border">
              <img v-if="p.imagen" :src="p.imagen" :alt="p.producto || p.titulo" loading="lazy" class="absolute inset-0 w-full h-full object-contain p-3" />
              <!-- Sin foto: una prenda genérica. -->
              <div v-else class="absolute inset-0 flex items-center justify-center text-zinc-300">
                <svg class="w-14 h-14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" aria-hidden="true">
                  <path d="M8.5 3.5L4 5.8 2.5 10.2l3 1.3L6.3 10V20.5h11.4V10l.8 1.5 3-1.3L20 5.8l-4.5-2.3c-.6 1.6-1.9 2.5-3.5 2.5s-2.9-.9-3.5-2.5z"/>
                </svg>
              </div>
              <span class="absolute top-3 left-3 text-[11px] font-semibold rounded-full px-2.5 py-0.5 border" :class="claseEstado(p)">{{ textoEstado(p) }}</span>
              <span v-if="p.productos > 1" class="absolute bottom-3 left-3 text-[11px] font-medium bg-white/90 border border-surface-border rounded-full px-2 py-0.5 text-ink-muted">+{{ p.productos - 1 }} producto{{ p.productos > 2 ? "s" : "" }}</span>
              <button
                type="button" title="Más acciones"
                class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center rounded-lg bg-white/90 border border-surface-border text-ink-muted opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity hover:text-ink"
                :class="openMenu === p.name ? 'opacity-100' : ''"
                @click.prevent.stop="toggleMenu(p.name, $event)"
              >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
              </button>
            </div>

            <div class="p-4 flex-1 flex flex-col">
              <p class="text-[14.5px] font-semibold leading-snug line-clamp-2 group-hover:text-brand-700 transition-colors">{{ p.titulo }}</p>
              <div class="flex items-center gap-2 mt-2 min-w-0">
                <img v-if="p.cliente_imagen" :src="p.cliente_imagen" alt="" class="w-6 h-6 rounded-full object-cover border border-surface-border flex-shrink-0" />
                <span v-else class="w-6 h-6 rounded-full flex items-center justify-center text-[9.5px] font-semibold flex-shrink-0" :class="colorAvatar(p.cliente_nombre || p.name)">{{ iniciales(p.cliente_nombre || "?") }}</span>
                <span class="text-[12.5px] text-ink-muted truncate">{{ p.cliente_nombre || "Sin cliente" }}</span>
                <span v-if="p.cliente_sin_alta" class="text-[10px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 rounded px-1.5 flex-shrink-0">Sin confirmar</span>
              </div>

              <!-- Etapa del ciclo (las mismas 6 que el panel de Dirección) -->
              <div class="mt-3.5">
                <div class="flex items-center gap-1">
                  <span v-for="(e, i) in ETAPAS" :key="e" class="h-1.5 flex-1 rounded-full" :class="colorEtapa(p, i + 1)" :title="e"></span>
                </div>
                <p class="text-[11.5px] text-ink-muted mt-1.5">
                  <template v-if="p.estado === 'Cancelado'">Cancelado</template>
                  <template v-else-if="p.etapa >= 6">Completado · entregado y facturado</template>
                  <template v-else>Va en <b class="text-ink font-medium">{{ ETAPAS[p.etapa - 1] }}</b> · paso {{ p.etapa }} de 6</template>
                </p>
              </div>

              <div class="mt-auto pt-3.5 grid grid-cols-3 gap-2 border-t border-surface-border mt-3.5">
                <div class="min-w-0">
                  <p class="text-[10.5px] text-ink-light">{{ p.documento ? "Venta" : "Fecha" }}</p>
                  <p class="text-[13px] font-semibold tabular-nums truncate">{{ p.monto != null ? dineroCorto(p.monto, p.moneda) : formatDate(p.fecha) }}</p>
                </div>
                <div class="min-w-0">
                  <p class="text-[10.5px] text-ink-light">Prendas</p>
                  <p class="text-[13px] font-semibold tabular-nums">{{ p.piezas ? numero(p.piezas) : "—" }}</p>
                </div>
                <div class="min-w-0">
                  <p class="text-[10.5px] text-ink-light">Entrega</p>
                  <p class="text-[13px] font-semibold tabular-nums truncate">{{ p.entrega ? fecha(p.entrega) : "—" }}</p>
                </div>
              </div>
              <!-- Asignaciones abiertas del proyecto (api/encargos.get_por_proyecto). -->
              <p v-for="(e, i) in (encargosDe[p.name] || []).slice(0, 1)" :key="i" class="mt-2.5 text-[11.5px] truncate flex items-center gap-1.5"
                 :class="e.vencido || e.vence_hoy ? 'text-red-700' : 'text-ink-muted'">
                <Icono nombre="persona" class="w-3.5 h-3.5 flex-shrink-0" />
                <span class="truncate">{{ e.etiqueta }}{{ e.lote ? ` · ${e.lote}` : "" }} → <b class="font-medium">{{ e.para_nombre }}</b><template v-if="(encargosDe[p.name] || []).length > 1"> · y {{ encargosDe[p.name].length - 1 }} más</template></span>
              </p>
            </div>
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div
        v-if="toast.show"
        class="fixed bottom-5 left-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg flex items-center gap-2"
        :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'"
      >{{ toast.msg }}</div>
    </Transition>
  </div>
    <!-- Menú "⋯" de la fila. Va TELETRANSPORTADO al body y con posición fija: la
         tarjeta de la tabla tiene `overflow-hidden` (para las esquinas redondeadas) y
         recortaba el menú, que solo se asomaba como una franja. Al estar fuera de la
         tabla ya no hay ancestro que lo corte, y se voltea hacia arriba cuando no cabe
         abajo. -->
    <Teleport to="body">
      <Transition name="panel">
        <div
          v-if="openMenu"
          class="fixed w-44 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden z-[60]"
          :style="{ top: `${menuPos.top}px`, left: `${menuPos.left}px` }"
          @click.stop
        >
          <div class="py-1">
            <button class="ctx-item" @click="openItem(menuTarget)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
              Abrir
            </button>
            <button class="ctx-item" @click="duplicateItem(menuTarget)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              Duplicar
            </button>
          </div>
          <div class="border-t border-gray-100 py-1">
            <button class="ctx-item text-red-500 hover:bg-red-50 hover:text-red-600" @click="askDelete(menuTarget)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              Eliminar
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

</template>

<script setup>
import { puede, puedeEditar, rutaPermitida } from "@/composables/useAccesos.js";
import EncargarProyecto from "@/components/encargos/EncargarProyecto.vue";
import { getPorProyecto } from "@/composables/useEncargos.js";
import Icono from "@/components/Icono.vue";
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { RouterLink } from "vue-router";
import { colorAvatar, dineroCorto, fecha, iniciales, numero } from "@/utils/formato.js";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { db, call } from "@/utils/frappe.js";
import { useCompany } from "@/composables/useCompany.js";

const encargarAbierto = ref(false);

const { state: companyState } = useCompany();

const router = useRouter();

const loading      = ref(true);
const items        = ref([]);
const search       = ref("");
const filterStatus = ref("");
const openMenu     = ref(null); // name of card whose menu is open
const menuTarget   = ref(null); // sobre quién actúa el menú (ver toggleMenu)
const menuPos      = ref({ top: 0, left: 0 });

const toast = reactive({ show: false, msg: "", type: "success" });

const confirmDelete = reactive({ open: false, name: "", loading: false });

// Las 6 etapas del ciclo, igual que el panel de Dirección (direccion._ETAPA).
const ETAPAS = ["Costeo", "Cotización", "OV", "Producción", "Entrega", "Factura"];
const claveFiltro = (p) => (p.estado === "Cancelado" ? "cancelado" : p.etapa >= 6 ? "completado" : `e${p.etapa}`);
const filtrosEtapa = computed(() => {
  const n = (k) => items.value.filter((p) => claveFiltro(p) === k).length;
  const base = [{ k: "", l: "Todos", n: items.value.length },
    ...ETAPAS.slice(0, 5).map((e, i) => ({ k: `e${i + 1}`, l: e, n: n(`e${i + 1}`) })),
    { k: "completado", l: "Completados", n: n("completado") }];
  if (n("cancelado")) base.push({ k: "cancelado", l: "Cancelados", n: n("cancelado") });
  return base;
});
function colorEtapa(p, n) {
  if (p.estado === "Cancelado") return "bg-zinc-200";
  if (n < p.etapa || p.etapa >= 6) return "bg-emerald-500";
  return n === p.etapa ? "bg-brand-500" : "bg-zinc-200";
}
function textoEstado(p) {
  if (p.estado === "Borrador") return p.docstatus === 0 ? "En costeo" : "Costeo validado";
  return p.estado;
}
function claseEstado(p) {
  if (p.estado === "Cancelado") return "bg-zinc-100 text-ink-muted border-zinc-200";
  if (p.etapa >= 6) return "bg-emerald-50 text-emerald-800 border-emerald-200";
  if (p.etapa === 1) return "bg-white/90 text-ink-muted border-surface-border";
  return "bg-brand-50 text-brand-700 border-brand-200";
}

// ── Computed ──────────────────────────────────────────────────────────────────
const filteredItems = computed(() =>
  items.value.filter(i => {
    const q = search.value.toLowerCase();
    const matchSearch = !q ||
      (i.cliente_nombre || "").toLowerCase().includes(q) ||
      (i.titulo  || "").toLowerCase().includes(q) ||
      (i.name    || "").toLowerCase().includes(q) ||
      (i.documento || "").toLowerCase().includes(q);
    return matchSearch && (!filterStatus.value || claveFiltro(i) === filterStatus.value);
  })
);

function formatDate(d) {
  if (!d) return "-";
  // "2026-10-28" sin hora se lee como UTC y en México salía un día antes.
  return new Date(String(d).length === 10 ? `${d}T00:00` : d).toLocaleDateString("es-MX", { year: "numeric", month: "short", day: "numeric" });
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = "success") {
  toast.msg = msg; toast.type = type; toast.show = true;
  setTimeout(() => (toast.show = false), 3000);
}

// ── Context menu ──────────────────────────────────────────────────────────────
const ALTO_MENU = 116;   // los 3 renglones + separadores
const ANCHO_MENU = 176;  // w-44

/** `menuTarget` se guarda aparte de `openMenu` porque `closeMenus` corre en fase de
 *  CAPTURA, o sea ANTES del clic en el renglón del menú: si los handlers leyeran
 *  `openMenu` lo encontrarían ya en null. */
function toggleMenu(name, ev) {
  if (openMenu.value === name) { openMenu.value = null; return; }
  const r = ev.currentTarget.getBoundingClientRect();
  const cabeAbajo = window.innerHeight - r.bottom > ALTO_MENU + 8;
  menuPos.value = {
    top: cabeAbajo ? r.bottom + 4 : Math.max(8, r.top - ALTO_MENU - 4),
    left: Math.max(8, r.right - ANCHO_MENU),
  };
  menuTarget.value = name;
  openMenu.value = name;
}

function closeMenus(e) {
  // Only close if click is outside any menu button
  openMenu.value = null;
}

function openItem(name) {
  openMenu.value = null;
  router.push(`/costeo/${name}`);
}

async function duplicateItem(name) {
  openMenu.value = null;
  try {
    const res = await call("costeo_yelke.api.costeo_api.duplicate_costeo", { name });
    showToast("Costeo duplicado");
    // Add the copy to the list immediately
    const original = items.value.find(i => i.name === name);
    if (original) {
      items.value.unshift({ ...original, name: res.name, estado: "Borrador", docstatus: 0, etapa: 1, documento: null, monto: null, entrega: null });
    }
    router.push(`/costeo/${res.name}`);
  } catch (e) {
    showToast(e.message || "Error al duplicar", "error");
  }
}

function askDelete(name) {
  openMenu.value = null;
  confirmDelete.name = name;
  confirmDelete.open = true;
}

async function doDelete() {
  confirmDelete.loading = true;
  try {
    await call("costeo_yelke.api.costeo_api.delete_costeo", { name: confirmDelete.name });
    items.value = items.value.filter(i => i.name !== confirmDelete.name);
    confirmDelete.open = false;
    showToast("Costeo eliminado");
  } catch (e) {
    showToast(e.message || "Error al eliminar", "error");
  } finally {
    confirmDelete.loading = false;
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
const encargosDe = ref({});
async function loadEncargos() {
  try { encargosDe.value = await getPorProyecto(items.value.map((i) => i.name)); } catch { encargosDe.value = {}; }
}

async function load() {
  loading.value = true;
  try {
    // Sin plantillas (son costeos por dentro, pero viven en «Plantillas»).
    items.value = await call("costeo_yelke.api.direccion.get_lista_proyectos", { company: companyState.selected || null }) || [];
    await loadEncargos();
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", closeMenus, true);
  load();
});
watch(() => companyState.selected, load);

onUnmounted(() => {
  document.removeEventListener("click", closeMenus, true);
});
</script>

<style scoped>
.ctx-item {
  @apply flex items-center gap-2.5 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors text-left;
}
.panel-enter-active { transition: opacity 0.1s ease, transform 0.1s ease; }
.panel-leave-active { transition: opacity 0.07s ease, transform 0.07s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px) scale(0.97); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
