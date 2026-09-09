<template>
  <div class="flex flex-col h-full">
    <PageHeader title="Plantillas" subtitle="Familias de prenda reutilizables" />

    <div class="flex-1 overflow-y-auto p-5">

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </div>

      <!-- Empty -->
      <div v-else-if="!templates.length" class="max-w-md mx-auto text-center py-20">
        <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-4">
          <svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"/>
          </svg>
        </div>
        <p class="text-sm font-semibold text-ink">Aún no hay plantillas</p>
        <p class="text-[13px] text-ink-muted mt-1">
          Crea una desde cualquier costeo con el botón <span class="font-medium">Guardar como Plantilla</span>.
        </p>
      </div>

      <!-- Grid -->
      <div v-else class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));">
        <div
          v-for="t in templates"
          :key="t.name"
          class="bg-white border border-surface-border rounded-xl p-4 flex flex-col hover:border-brand-200 transition-colors group relative"
        >
          <button
            class="absolute top-2.5 right-2.5 w-6 h-6 flex items-center justify-center rounded text-gray-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
            title="Eliminar plantilla"
            @click="askDelete(t)"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
          <div class="flex items-start gap-2.5 mb-3 pr-6">
            <div class="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center flex-shrink-0">
              <svg class="w-4 h-4 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"/>
              </svg>
            </div>
            <div class="min-w-0">
              <p class="text-[13px] font-semibold text-ink truncate">{{ t.nombre_plantilla || t.familia_prenda || "Plantilla" }}</p>
              <span v-if="t.familia_prenda" class="inline-block mt-0.5 text-[10px] font-medium text-brand-700 bg-brand-50 rounded-full px-2 py-0.5">{{ t.familia_prenda }}</span>
            </div>
          </div>
          <p class="text-[12px] text-ink-muted mb-3">{{ t.productos }} producto(s)</p>
          <button
            class="mt-auto w-full text-[13px] font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg py-2 transition-colors"
            @click="openUse(t)"
          >
            Usar plantilla
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: usar plantilla -->
    <div v-if="useModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="useModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink">Nuevo costeo desde plantilla</p>
        <p class="text-[12px] text-ink-muted mt-0.5 mb-4">{{ selected?.familia_prenda || selected?.name }}</p>

        <label class="block text-[12px] text-ink-muted mb-1">Cliente</label>
        <select v-model="form.cliente" class="w-full border border-surface-border rounded-lg px-3 py-2 text-sm mb-3">
          <option value="">— Seleccionar cliente —</option>
          <option v-for="c in customers" :key="c.name" :value="c.name">{{ c.customer_name || c.name }}</option>
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
            @click="createFromTemplate"
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
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { call, db } from "@/utils/frappe";
import PageHeader from "@/components/PageHeader.vue";
import { useCompany } from "@/composables/useCompany.js";

const { state: companyState } = useCompany();

const router = useRouter();

const loading   = ref(true);
const templates = ref([]);

const useModal  = ref(false);
const selected  = ref(null);
const customers = ref([]);
const companies = ref([]);
const form      = ref({ cliente: "", compania: "" });
const creating  = ref(false);
const errorMsg  = ref("");
const delModal  = ref({ open: false, name: "", nombre: "", loading: false });

async function load() {
  loading.value = true;
  try {
    templates.value = await call("costeo_yelke.api.costeo_template_api.get_costeo_templates", { company: companyState.selected || undefined });
  } finally {
    loading.value = false;
  }
}

async function openUse(t) {
  selected.value = t;
  errorMsg.value = "";
  form.value = { cliente: "", compania: t.compañia || "" };
  useModal.value = true;

  if (!customers.value.length) {
    customers.value = await db.getList("Customer", {
      fields: ["name", "customer_name"], orderBy: "customer_name asc", limit: 0,
    });
  }
  if (!companies.value.length) {
    companies.value = await db.getList("Company", { fields: ["name"], orderBy: "name asc", limit: 0 });
  }
  if (!form.value.compania && companies.value.length) {
    form.value.compania = companies.value[0].name;
  }
}

async function createFromTemplate() {
  if (!form.value.cliente) return;
  creating.value = true;
  errorMsg.value = "";
  try {
    const res = await call("costeo_yelke.api.costeo_template_api.create_costeo_from_template", {
      template: selected.value.name,
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
  delModal.value = { open: true, name: t.name, nombre: t.nombre_plantilla || t.familia_prenda || t.name, loading: false };
}
async function doDelete() {
  delModal.value.loading = true;
  try {
    await call("costeo_yelke.api.costeo_template_api.delete_template", { name: delModal.value.name });
    templates.value = templates.value.filter(t => t.name !== delModal.value.name);
    delModal.value.open = false;
  } catch (e) {
    delModal.value.open = false;
  }
}

onMounted(load);
watch(() => companyState.selected, load);
</script>
