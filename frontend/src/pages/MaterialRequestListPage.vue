<template>
  <DocumentListPage
    title="Solicitudes de Material"
    subtitle="Requisiciones de materia prima a producción"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    desk-doctype="Material Request"
    v-model:search="search"
    search-placeholder="Buscar número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay solicitudes de material"
    empty-icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="Pending">Pendiente</option>
        <option value="Partially Received">Parcialmente recibida</option>
        <option value="Received">Recibida</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Solicitud</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha requerida</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
    </template>

    <template #row="{ row: mr }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ mr.name }}</p>
        <p class="text-xs text-gray-400">{{ mr.material_request_type }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ mr.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(mr.transaction_date) }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ mr.schedule_date ? fmtDate(mr.schedule_date) : '—' }}</td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="mr.docstatus" :status="mr.status" /></td>
    </template>
  </DocumentListPage>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineComponent, h } from "vue";
import { useRouter } from "vue-router";
import DocumentListPage from "@/components/DocumentListPage.vue";
import { call } from "@/utils/frappe.js";
import { useCompany } from "@/composables/useCompany.js";

const { state: companyState } = useCompany();

const router = useRouter();
const loading = ref(true);
const rows = ref([]);
const search = ref("");
const filterStatus = ref("");

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = { "Draft": "Borrador", "Pending": "Pendiente", "Partially Received": "Parcial", "Received": "Recibida", "Cancelled": "Cancelada" };
    const COLOR = { "Pending": "bg-amber-100 text-amber-700", "Partially Received": "bg-blue-100 text-blue-700", "Received": "bg-green-100 text-green-700" };
    return () => {
      const ds = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Validada");
      const cls = ds === 0 ? "bg-gray-100 text-gray-500" : ds === 2 ? "bg-gray-100 text-gray-400" : (COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

const filtered = computed(() => {
  let list = rows.value;
  if (filterStatus.value) list = list.filter((r) => r.status === filterStatus.value);
  if (search.value) {
    const q = search.value.toLowerCase();
    list = list.filter((r) => (r.name || "").toLowerCase().includes(q));
  }
  return list;
});

const stats = computed(() => {
  const all = rows.value;
  const pending = all.filter((r) => r.docstatus === 1 && r.status !== "Received" && r.status !== "Cancelled");
  const received = all.filter((r) => r.status === "Received").length;
  return [
    { label: "Total", value: all.length, color: "#1e293b" },
    { label: "Pendientes", value: pending.length, color: "#3b82f6" },
    { label: "Recibidas", value: received, color: "#22c55e" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

function openRow(mr) {
  if (mr.costeo) router.push({ name: "CosteoDetail", params: { name: mr.costeo }, query: { step: "5", highlight: mr.name, doctype: "Material Request" } });
}

async function load() {
  loading.value = true;
  try { rows.value = await call("costeo_yelke.api.documentos_api.get_material_requests", { limit: 100, company: companyState.selected || undefined }) || []; }
  catch (e) { console.error(e); }
  finally { loading.value = false; }
}

onMounted(load);
watch(() => companyState.selected, load);
</script>
