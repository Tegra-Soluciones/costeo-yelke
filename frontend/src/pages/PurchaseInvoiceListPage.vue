<template>
  <DocumentListPage
    title="Facturas de Compra"
    subtitle="Cuentas por pagar a proveedores"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    desk-doctype="Purchase Invoice"
    v-model:search="search"
    search-placeholder="Buscar proveedor, número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay facturas de compra"
    empty-icon="M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="Unpaid">Sin pagar</option>
        <option value="Paid">Pagada</option>
        <option value="Overdue">Vencida</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Factura / Proveedor</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
    </template>

    <template #row="{ row: pi }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ pi.name }}</p>
        <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ pi.supplier_name || pi.supplier }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ pi.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(pi.posting_date) }}</td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="pi.docstatus" :status="pi.status" /></td>
      <td class="py-3 text-right"><span class="font-semibold text-gray-800 text-xs">{{ fmtC(pi.grand_total) }}</span></td>
    </template>
  </DocumentListPage>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from "vue";
import { useRouter } from "vue-router";
import DocumentListPage from "@/components/DocumentListPage.vue";
import { call } from "@/utils/frappe.js";

const router = useRouter();
const loading = ref(true);
const rows = ref([]);
const search = ref("");
const filterStatus = ref("");

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = { "Draft": "Borrador", "Unpaid": "Sin pagar", "Paid": "Pagada", "Overdue": "Vencida", "Cancelled": "Cancelada" };
    const COLOR = { "Unpaid": "bg-amber-100 text-amber-700", "Paid": "bg-green-100 text-green-700", "Overdue": "bg-red-100 text-red-600" };
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
    list = list.filter((r) => (r.name || "").toLowerCase().includes(q) || (r.supplier_name || "").toLowerCase().includes(q));
  }
  return list;
});

const stats = computed(() => {
  const all = rows.value;
  const unpaid = all.filter((r) => r.docstatus === 1 && r.status !== "Paid" && r.status !== "Cancelled");
  const totalUnpaid = unpaid.reduce((s, r) => s + (r.outstanding_amount || 0), 0);
  const overdue = all.filter((r) => r.status === "Overdue").length;
  return [
    { label: "Total", value: all.length, color: "#1e293b" },
    { label: "Sin pagar", value: unpaid.length, color: "#f59e0b", sub: fmtC(totalUnpaid) },
    { label: "Vencidas", value: overdue, color: overdue > 0 ? "#ef4444" : "#94a3b8" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }

function openRow(pi) {
  if (pi.costeo) router.push({ name: "CosteoDetail", params: { name: pi.costeo }, query: { step: "6", highlight: pi.name, doctype: "Purchase Invoice" } });
}

onMounted(async () => {
  try { rows.value = await call("costeo_yelke.api.documentos_api.get_purchase_invoices", { limit: 100 }) || []; }
  catch (e) { console.error(e); }
  finally { loading.value = false; }
});
</script>
