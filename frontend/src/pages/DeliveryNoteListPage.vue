<template>
  <DocumentListPage
    title="Remisiones"
    subtitle="Entregas de producto terminado al cliente"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    desk-doctype="Delivery Note"
    v-model:search="search"
    search-placeholder="Buscar cliente, número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay remisiones"
    empty-icon="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 5H6l-2-5m16 0H4m5 5v.01M15 18v.01"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="To Bill">Por Facturar</option>
        <option value="Completed">Completada</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Remisión / Cliente</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
    </template>

    <template #row="{ row: dn }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ dn.name }}</p>
        <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ dn.customer_name || dn.customer }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ dn.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(dn.posting_date) }}</td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="dn.docstatus" :status="dn.status" /></td>
      <td class="py-3 text-right"><span class="font-semibold text-gray-800 text-xs">{{ fmtC(dn.grand_total) }}</span></td>
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
    const LABELS = { "Draft": "Borrador", "To Bill": "Por Facturar", "Completed": "Completada", "Cancelled": "Cancelada" };
    const COLOR = { "To Bill": "bg-purple-100 text-purple-700", "Completed": "bg-green-100 text-green-700" };
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
    list = list.filter((r) => (r.name || "").toLowerCase().includes(q) || (r.customer_name || "").toLowerCase().includes(q));
  }
  return list;
});

const stats = computed(() => {
  const all = rows.value;
  const active = all.filter((r) => r.docstatus === 1 && r.status !== "Completed" && r.status !== "Cancelled");
  const totalActive = active.reduce((s, r) => s + (r.grand_total || 0), 0);
  const completed = all.filter((r) => r.status === "Completed").length;
  return [
    { label: "Total", value: all.length, color: "#1e293b" },
    { label: "Activas", value: active.length, color: "#3b82f6", sub: fmtC(totalActive) },
    { label: "Completadas", value: completed, color: "#22c55e" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }

function openRow(dn) {
  if (dn.costeo) router.push({ name: "CosteoDetail", params: { name: dn.costeo }, query: { step: "6", highlight: dn.name, doctype: "Delivery Note" } });
}

async function load() {
  loading.value = true;
  try { rows.value = await call("costeo_yelke.api.documentos_api.get_delivery_notes", { limit: 100, company: companyState.selected || undefined }) || []; }
  catch (e) { console.error(e); }
  finally { loading.value = false; }
}

onMounted(load);
watch(() => companyState.selected, load);
</script>
