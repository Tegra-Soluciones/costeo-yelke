<template>
  <div class="flex flex-col h-full">
    <PageHeader title="Plantillas" subtitle="Selecciona una o varias para armar un costeo nuevo" />

    <div class="flex-1 overflow-y-auto p-5 pb-24">

      <!-- Buscador y filtros -->
      <div v-if="templates.length || loading" class="flex flex-wrap items-center gap-2 mb-4">
        <div class="relative flex-1 min-w-[200px]">
          <svg class="w-4 h-4 text-gray-300 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>
          </svg>
          <input
            v-model="search"
            type="text"
            placeholder="Buscar plantilla por producto o descripción…"
            class="w-full border border-surface-border rounded-lg pl-9 pr-3 py-2 text-sm"
          />
        </div>
        <select v-model="filtroCliente" class="border border-surface-border rounded-lg px-3 py-2 text-sm">
          <option value="">Todos los clientes</option>
          <option v-for="c in clientesDisponibles" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
        <select v-model="filtroProyecto" class="border border-surface-border rounded-lg px-3 py-2 text-sm">
          <option value="">Todos los proyectos</option>
          <option v-for="p in proyectosDisponibles" :key="p" :value="p">{{ p }}</option>
        </select>
        <button
          v-if="search || filtroCliente || filtroProyecto"
          class="text-[12.5px] text-ink-muted hover:text-ink px-2 py-2"
          @click="search = ''; filtroCliente = ''; filtroProyecto = ''"
        >
          Limpiar filtros
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </div>

      <!-- Empty (sin plantillas todavía) -->
      <div v-else-if="!templates.length" class="max-w-md mx-auto text-center py-20">
        <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-4">
          <svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"/>
          </svg>
        </div>
        <p class="text-sm font-semibold text-ink">Aún no hay plantillas</p>
        <p class="text-[13px] text-ink-muted mt-1">
          Crea una desde cualquier costeo con el botón <span class="font-medium">Guardar como Plantilla</span>. Cada producto se guarda como su propia plantilla.
        </p>
      </div>

      <!-- Empty (filtros sin resultados) -->
      <div v-else-if="!templatesFiltrados.length" class="max-w-md mx-auto text-center py-20">
        <p class="text-sm font-semibold text-ink">Sin resultados</p>
        <p class="text-[13px] text-ink-muted mt-1">Ninguna plantilla coincide con la búsqueda o los filtros.</p>
      </div>

      <!-- Grid -->
      <div v-else class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));">
        <div
          v-for="t in templatesFiltrados"
          :key="t.name"
          class="bg-white border rounded-xl p-4 flex flex-col transition-colors group relative cursor-pointer"
          :class="isSelected(t.name) ? 'border-brand-400 ring-1 ring-brand-300 bg-brand-50/40' : 'border-surface-border hover:border-brand-200'"
          @click="toggle(t.name)"
        >
          <!-- Checkbox -->
          <div
            class="absolute top-3 left-3 w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 transition-colors"
            :class="isSelected(t.name) ? 'bg-brand-500 border-brand-500' : 'bg-white border-gray-300 group-hover:border-brand-300'"
          >
            <svg v-if="isSelected(t.name)" class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </div>

          <button
            class="absolute top-2.5 right-2.5 w-6 h-6 flex items-center justify-center rounded text-gray-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
            title="Eliminar plantilla"
            @click.stop="askDelete(t)"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>

          <div class="w-full aspect-square rounded-lg bg-surface-raised overflow-hidden flex items-center justify-center mb-3 mt-5">
            <img v-if="t.image" :src="t.image" class="w-full h-full object-cover" />
            <svg v-else class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14M14 8h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
          </div>

          <p class="text-[13px] font-semibold text-ink truncate" :title="t.nombre_plantilla">{{ t.nombre_plantilla || t.finished_item || "Plantilla" }}</p>
          <p v-if="t.description" class="text-[12px] text-ink-muted truncate mt-0.5">{{ t.description }}</p>
          <p class="text-[12px] font-medium text-ink mt-2">{{ formatMoney(t.total_unit_cost) }} <span class="text-ink-muted font-normal">/ unidad</span></p>

          <div v-if="t.plantilla_origen_titulo || t.origen_cliente_nombre" class="mt-2 pt-2 border-t border-surface-border/60 text-[11px] text-ink-muted leading-snug">
            <p v-if="t.plantilla_origen_titulo" class="truncate" :title="t.plantilla_origen_titulo">
              <span class="text-ink-light">Proyecto:</span> {{ t.plantilla_origen_titulo }}
            </p>
            <p v-if="t.origen_cliente_nombre" class="truncate" :title="t.origen_cliente_nombre">
              <span class="text-ink-light">Cliente:</span> {{ t.origen_cliente_nombre }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Barra flotante de selección (carrito) -->
    <div
      v-if="selected.length"
      class="fixed bottom-0 left-0 right-0 md:left-[var(--sidebar-w,0px)] z-40 bg-white border-t border-surface-border shadow-lg px-5 py-3 flex items-center justify-between gap-3"
    >
      <p class="text-[13px] text-ink">
        <span class="font-semibold">{{ selected.length }}</span> plantilla{{ selected.length === 1 ? "" : "s" }} seleccionada{{ selected.length === 1 ? "" : "s" }}
      </p>
      <div class="flex items-center gap-2">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="selected = []">Limpiar</button>
        <button class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 rounded-lg" @click="openUse">
          Crear costeo con estas
        </button>
      </div>
    </div>

    <!-- Modal: usar plantillas seleccionadas -->
    <div v-if="useModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="useModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink">Nuevo costeo desde plantillas</p>
        <p class="text-[12px] text-ink-muted mt-0.5 mb-4">
          Se combinarán {{ selected.length }} plantilla{{ selected.length === 1 ? "" : "s" }}: {{ selectedNames }}
        </p>

        <label class="block text-[12px] text-ink-muted mb-1">Cliente</label>
        <select v-model="form.cliente" class="w-full border border-surface-border rounded-lg px-3 py-2 text-sm mb-3">
          <option value="">— Seleccionar cliente —</option>
          <option v-for="c in customers" :key="c.name" :value="c.name">{{ c.nombre_comercial || c.customer_name || c.name }}</option>
        </select>

        <label class="block text-[12px] text-ink-muted mb-1">Compañía</label>
        <select v-model="form.compania" class="w-full border border-surface-border rounded-lg px-3 py-2 text-sm mb-4">
          <option v-for="c in companies" :key="c.name" :value="c.name">{{ c.name }}</option>
        </select>

        <p v-if="errorMsg" class="text-[12px] text-red-600 mb-3">{{ errorMsg }}</p>

        <div class="flex gap-2 justify-end">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="useModal = false">Cancelar</button>
          <button
            :disabled="!form.cliente || creating"
            class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2"
            @click="createFromTemplates"
          >
            <svg v-if="creating" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {{ creating ? "Creando…" : "Crear costeo" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: eliminar plantilla -->
    <div v-if="delModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="delModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink">Eliminar plantilla</p>
        <p class="text-[13px] text-ink-muted mt-1 mb-4">¿Eliminar la plantilla "{{ delModal.nombre }}"? Esta acción no se puede deshacer.</p>
        <div class="flex gap-2 justify-end">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="delModal.open = false">Cancelar</button>
          <button :disabled="delModal.loading" class="px-4 py-1.5 text-[13px] font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 rounded-lg" @click="doDelete">{{ delModal.loading ? "Eliminando…" : "Eliminar" }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { call, db } from "@/utils/frappe";
import PageHeader from "@/components/PageHeader.vue";
import { useCompany } from "@/composables/useCompany.js";

const { state: companyState } = useCompany();

const router = useRouter();

const loading   = ref(true);
const templates = ref([]);
const selected  = ref([]); // nombres (Costeo.name) de las plantillas elegidas, en orden de selección

const search        = ref("");
const filtroCliente = ref("");
const filtroProyecto = ref("");

// Opciones de los filtros, derivadas de las plantillas ya cargadas (no hay tantas
// como para justificar un endpoint aparte).
const clientesDisponibles = computed(() => {
  const vistos = new Map();
  for (const t of templates.value) {
    if (t.plantilla_origen_cliente && !vistos.has(t.plantilla_origen_cliente)) {
      vistos.set(t.plantilla_origen_cliente, t.origen_cliente_nombre || t.plantilla_origen_cliente);
    }
  }
  return [...vistos.entries()].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
});
const proyectosDisponibles = computed(() => {
  const vistos = new Set();
  for (const t of templates.value) {
    if (t.plantilla_origen_titulo) vistos.add(t.plantilla_origen_titulo);
  }
  return [...vistos].sort((a, b) => a.localeCompare(b));
});

const templatesFiltrados = computed(() => {
  const q = search.value.trim().toLowerCase();
  return templates.value.filter(t => {
    if (filtroCliente.value && t.plantilla_origen_cliente !== filtroCliente.value) return false;
    if (filtroProyecto.value && t.plantilla_origen_titulo !== filtroProyecto.value) return false;
    if (q) {
      const haystack = [t.nombre_plantilla, t.finished_item, t.description, t.plantilla_origen_titulo, t.origen_cliente_nombre]
        .filter(Boolean).join(" ").toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
});

const useModal  = ref(false);
const customers = ref([]);
const companies = ref([]);
const form      = ref({ cliente: "", compania: "" });
const creating  = ref(false);
const errorMsg  = ref("");
const delModal  = ref({ open: false, name: "", nombre: "", loading: false });

const selectedNames = computed(() => {
  const byName = Object.fromEntries(templates.value.map(t => [t.name, t.nombre_plantilla || t.finished_item || t.name]));
  return selected.value.map(n => byName[n] || n).join(", ");
});

function formatMoney(v) {
  const n = Number(v) || 0;
  return n.toLocaleString("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 2 });
}

function isSelected(name) {
  return selected.value.includes(name);
}

function toggle(name) {
  const i = selected.value.indexOf(name);
  if (i === -1) selected.value.push(name);
  else selected.value.splice(i, 1);
}

async function load() {
  loading.value = true;
  try {
    templates.value = await call("costeo_yelke.api.costeo_template_api.get_costeo_templates", { company: companyState.selected || undefined });
    // Descarta de la selección cualquier plantilla que ya no exista tras recargar.
    const names = new Set(templates.value.map(t => t.name));
    selected.value = selected.value.filter(n => names.has(n));
  } finally {
    loading.value = false;
  }
}

async function openUse() {
  if (!selected.value.length) return;
  errorMsg.value = "";
  const primero = templates.value.find(t => t.name === selected.value[0]);
  form.value = { cliente: "", compania: primero?.compañia || "" };
  useModal.value = true;

  if (!customers.value.length) {
    customers.value = await db.getList("Customer", {
      fields: ["name", "customer_name", "nombre_comercial"], orderBy: "customer_name asc", limit: 0,
    });
  }
  if (!companies.value.length) {
    companies.value = await db.getList("Company", { fields: ["name"], orderBy: "name asc", limit: 0 });
  }
  if (!form.value.compania && companies.value.length) {
    form.value.compania = companies.value[0].name;
  }
}

async function createFromTemplates() {
  if (!form.value.cliente || !selected.value.length) return;
  creating.value = true;
  errorMsg.value = "";
  try {
    const res = await call("costeo_yelke.api.costeo_template_api.create_costeo_from_templates", {
      templates: selected.value,
      cliente:  form.value.cliente,
      compania: form.value.compania,
    });
    useModal.value = false;
    router.push(`/costeo/${encodeURIComponent(res.name)}`);
  } catch (e) {
    errorMsg.value = e?.message || "No se pudo crear el costeo";
  } finally {
    creating.value = false;
  }
}

function askDelete(t) {
  delModal.value = { open: true, name: t.name, nombre: t.nombre_plantilla || t.finished_item || t.name, loading: false };
}
async function doDelete() {
  delModal.value.loading = true;
  try {
    await call("costeo_yelke.api.costeo_template_api.delete_template", { name: delModal.value.name });
    templates.value = templates.value.filter(t => t.name !== delModal.value.name);
    selected.value = selected.value.filter(n => n !== delModal.value.name);
    delModal.value.open = false;
  } catch (e) {
    delModal.value.open = false;
  }
}

onMounted(load);
watch(() => companyState.selected, load);
</script>
