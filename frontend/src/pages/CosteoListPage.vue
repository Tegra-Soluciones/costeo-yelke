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

    <PageHeader title="Costeos" subtitle="Lista de costeos de manufactura">
      <button
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-medium rounded-md hover:bg-brand-600 transition-colors flex items-center gap-1.5"
        @click="$router.push('/costeo/nuevo')"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Nuevo Costeo
      </button>
    </PageHeader>

    <!-- View toggle + search -->
    <div class="bg-white border-b border-gray-200 px-6 py-2.5 flex items-center gap-3">
      <div class="relative flex-1 max-w-xs">
        <svg class="absolute left-2.5 top-2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="search"
          type="text"
          placeholder="Buscar por cliente o ID..."
          class="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
        />
      </div>

      <select
        v-model="filterStatus"
        class="text-sm border border-gray-200 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
      >
        <option value="">Todos los estatus</option>
        <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="flex flex-col items-center gap-3 text-gray-400">
        <svg class="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        <span class="text-sm">Cargando costeos...</span>
      </div>
    </div>

    <!-- ── List view ─────────────────────────────────────────────── -->
    <div v-else class="flex-1 overflow-y-auto p-4">
      <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">ID</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Cliente</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Compañía</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha</th>
              <th class="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Estatus</th>
              <th class="px-4 py-3 w-10"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="item in filteredItems"
              :key="item.name"
              class="hover:bg-gray-50 cursor-pointer transition-colors group"
              @click="$router.push(`/costeo/${item.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ item.name }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">{{ item.cliente }}</td>
              <td class="px-4 py-3 text-gray-600">{{ item["compañia"] }}</td>
              <td class="px-4 py-3 text-gray-500">{{ formatDate(item.fecha) }}</td>
              <td class="px-4 py-3"><StatusBadge :model-value="item.costeo_status || 'Borrador'" /></td>
              <td class="px-4 py-3 text-right" @click.stop>
                <div class="relative flex justify-end">
                  <button
                    class="w-7 h-7 flex items-center justify-center rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                    :class="openMenu === item.name ? 'text-gray-700 bg-gray-100' : ''"
                    @click.stop="toggleMenu(item.name)"
                  >
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
                    </svg>
                  </button>

                  <Transition name="panel">
                    <div
                      v-if="openMenu === item.name"
                      class="absolute right-0 top-full mt-1 w-44 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden z-50"
                    >
                      <div class="py-1">
                        <button class="ctx-item" @click="openItem(item.name)">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                          Abrir
                        </button>
                        <button class="ctx-item" @click="duplicateItem(item.name)">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                          Duplicar
                        </button>
                      </div>
                      <div class="border-t border-gray-100 py-1">
                        <button class="ctx-item text-red-500 hover:bg-red-50 hover:text-red-600" @click="askDelete(item.name)">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                          Eliminar
                        </button>
                      </div>
                    </div>
                  </Transition>
                </div>
              </td>
            </tr>
            <tr v-if="filteredItems.length === 0">
              <td colspan="6" class="px-4 py-12 text-center text-gray-400">
                <svg class="w-10 h-10 mx-auto mb-3 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p class="text-sm">No se encontraron costeos</p>
                <button
                  class="mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium"
                  @click="$router.push('/costeo/nuevo')"
                >Crear el primero →</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div
        v-if="toast.show"
        class="fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg flex items-center gap-2"
        :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'"
      >{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { db, call } from "@/utils/frappe.js";

const router = useRouter();

const loading      = ref(true);
const items        = ref([]);
const search       = ref("");
const filterStatus = ref("");
const openMenu     = ref(null); // name of card whose menu is open

const toast = reactive({ show: false, msg: "", type: "success" });

const confirmDelete = reactive({ open: false, name: "", loading: false });

const statuses = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Completado", "Cancelado"];

// ── Computed ──────────────────────────────────────────────────────────────────
const filteredItems = computed(() =>
  items.value.filter(i => {
    const q = search.value.toLowerCase();
    const matchSearch = !q ||
      (i.cliente || "").toLowerCase().includes(q) ||
      (i.name    || "").toLowerCase().includes(q);
    const matchStatus = !filterStatus.value || i.costeo_status === filterStatus.value;
    return matchSearch && matchStatus;
  })
);

function formatDate(d) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("es-MX", { year: "numeric", month: "short", day: "numeric" });
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = "success") {
  toast.msg = msg; toast.type = type; toast.show = true;
  setTimeout(() => (toast.show = false), 3000);
}

// ── Context menu ──────────────────────────────────────────────────────────────
function toggleMenu(name) {
  openMenu.value = openMenu.value === name ? null : name;
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
      items.value.unshift({ ...original, name: res.name, costeo_status: "Borrador" });
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
onMounted(async () => {
  document.addEventListener("click", closeMenus, true);
  try {
    items.value = await db.getList("Costeo", {
      fields: ["name", "cliente", "fecha", "compañia", "costeo_status"],
      orderBy: "modified desc",
      limit: 200,
    });
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});

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
