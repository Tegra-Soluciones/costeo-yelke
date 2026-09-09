<template>
  <DocumentListPage
    title="Cotizaciones"
    subtitle="Gestión de cotizaciones a clientes"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    v-model:search="search"
    search-placeholder="Buscar cliente, número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay cotizaciones"
    empty-icon="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #actions>
      <RouterLink
        to="/cotizaciones/nueva"
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-medium rounded-md hover:bg-brand-600 transition-colors flex items-center gap-1.5"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        Nueva Cotización
      </RouterLink>
    </template>

    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="Open">Abierta</option>
        <option value="Ordered">Ordenada</option>
        <option value="Lost">Perdida</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Cotización / Cliente</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Válida hasta</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
    </template>

    <template #row="{ row: q }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ q.name }}</p>
        <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ q.customer_name || q.party_name }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ q.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(q.transaction_date) }}</td>
      <td class="py-3 pr-3 text-xs" :class="isExpired(q.valid_till) ? 'text-red-500 font-medium' : 'text-gray-600'">
        {{ q.valid_till ? fmtDate(q.valid_till) : '—' }}
      </td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="q.docstatus" :status="q.status" /></td>
      <td class="py-3 text-right"><span class="font-semibold text-gray-800 text-xs">{{ fmtC(q.grand_total) }}</span></td>
    </template>
  </DocumentListPage>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineComponent, h } from "vue";
import { RouterLink, useRouter } from "vue-router";
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
    const LABELS = { "Draft": "Borrador", "Open": "Abierta", "Ordered": "Ordenada", "Lost": "Perdida", "Cancelled": "Cancelada" };
    const STATUS_COLOR = { "Open": "bg-blue-100 text-blue-700", "Ordered": "bg-green-100 text-green-700", "Lost": "bg-red-100 text-red-600" };
    return () => {
      const ds = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Abierta");
      const cls = ds === 0 ? "bg-gray-100 text-gray-500" : ds === 2 ? "bg-gray-100 text-gray-400" : (STATUS_COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

const filtered = computed(() => {
  let list = rows.value;
  if (filterStatus.value) list = list.filter(r => r.status === filterStatus.value);
  if (search.value) {
    const q = search.value.toLowerCase();
    list = list.filter(r =>
      (r.name || "").toLowerCase().includes(q) ||
      (r.customer_name || "").toLowerCase().includes(q) ||
      (r.party_name || "").toLowerCase().includes(q)
    );
  }
  return list;
});

const stats = computed(() => {
  const all = rows.value;
  const open = all.filter(r => r.status === "Open" || r.docstatus === 0);
  const ordered = all.filter(r => r.status === "Ordered");
  const expired = all.filter(r => r.valid_till && isExpired(r.valid_till) && r.docstatus !== 2);
  const totalOpen = open.reduce((s, r) => s + (r.grand_total || 0), 0);
  return [
    { label: "Total", value: all.length, color: "#1e293b" },
    { label: "En pipeline", value: open.length, color: "#3b82f6", sub: fmtC(totalOpen) },
    { label: "Ordenadas", value: ordered.length, color: "#22c55e" },
    { label: "Vencidas", value: expired.length, color: expired.length > 0 ? "#ef4444" : "#94a3b8" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function isExpired(dateStr) {
  if (!dateStr) return false;
  return new Date(dateStr + "T23:59:59") < new Date();
}

function openRow(q) {
  if (q.costeo) {
    router.push({ name: "CosteoDetail", params: { name: q.costeo }, query: { step: "1", highlight: q.name, doctype: "Quotation" } });
  } else {
    router.push(`/cotizaciones/${encodeURIComponent(q.name)}`);
  }
}

async function load() {
  loading.value = true;
  try {
    const args = { limit: 100 };
    if (filterStatus.value) args.status = filterStatus.value;
    if (companyState.selected) args.company = companyState.selected;
    rows.value = await call("costeo_yelke.api.quotation_api.get_quotations", args);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(() => companyState.selected, load);
</script>
