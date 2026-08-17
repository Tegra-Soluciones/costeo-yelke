<template>
  <DocumentListPage
    title="Facturas de Venta"
    subtitle="Facturación a clientes"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    v-model:search="search"
    search-placeholder="Buscar cliente, número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay facturas"
    empty-icon="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #actions>
      <button
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
        @click="router.push('/facturas/nueva')"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        Nueva Factura
      </button>
    </template>

    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="Unpaid">Sin Pagar</option>
        <option value="Paid">Pagada</option>
        <option value="Partly Paid">Pago Parcial</option>
        <option value="Overdue">Vencida</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Factura / Cliente</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Emisión</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Vencimiento</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Saldo</th>
    </template>

    <template #row="{ row: inv }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ inv.name }}</p>
        <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ inv.customer_name || inv.customer }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ inv.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(inv.posting_date) }}</td>
      <td class="py-3 pr-3 text-xs" :class="isDueOverdue(inv) ? 'text-red-500 font-medium' : 'text-gray-600'">
        {{ inv.due_date ? fmtDate(inv.due_date) : '—' }}
      </td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="inv.docstatus" :status="inv.status" /></td>
      <td class="py-3 pr-3 text-right text-xs font-semibold text-gray-800">{{ fmtC(inv.grand_total) }}</td>
      <td class="py-3 text-right text-xs" :class="(inv.outstanding_amount || 0) > 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'">
        {{ inv.docstatus === 1 ? fmtC(inv.outstanding_amount) : '—' }}
      </td>
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
const invoices = ref([]);
const search   = ref("");
const filterStatus = ref("");

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = {
      "Draft": "Borrador", "Unpaid": "Sin Pagar", "Paid": "Pagada",
      "Partly Paid": "Pago Parcial", "Overdue": "Vencida",
      "Return": "Devolución", "Cancelled": "Cancelada",
    };
    const STATUS_COLOR = {
      "Unpaid": "bg-amber-100 text-amber-700",
      "Paid": "bg-green-100 text-green-700",
      "Partly Paid": "bg-blue-100 text-blue-700",
      "Overdue": "bg-red-100 text-red-700",
      "Return": "bg-gray-100 text-gray-500",
    };
    return () => {
      const ds    = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Enviada");
      const cls   = ds === 0 ? "bg-gray-100 text-gray-500" : ds === 2 ? "bg-gray-100 text-gray-400" : (STATUS_COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

const filtered = computed(() => {
  let list = invoices.value;
  if (filterStatus.value) list = list.filter(r => r.status === filterStatus.value);
  if (search.value) {
    const q = search.value.toLowerCase();
    list = list.filter(r =>
      (r.name || "").toLowerCase().includes(q) ||
      (r.customer || "").toLowerCase().includes(q) ||
      (r.customer_name || "").toLowerCase().includes(q)
    );
  }
  return list;
});

const stats = computed(() => {
  const all = invoices.value;
  const unpaid = all.filter(r => r.docstatus === 1 && ["Unpaid","Partly Paid","Overdue"].includes(r.status));
  const totalUnpaid = unpaid.reduce((s, r) => s + (r.outstanding_amount || 0), 0);
  const paid = all.filter(r => r.status === "Paid").length;
  const overdue = all.filter(r => r.status === "Overdue").length;
  return [
    { label: "Total",         value: all.length,    color: "#1e293b" },
    { label: "Por Cobrar",    value: unpaid.length,  color: "#f59e0b", sub: fmtC(totalUnpaid) },
    { label: "Pagadas",       value: paid,           color: "#22c55e" },
    { label: "Vencidas",      value: overdue,        color: overdue > 0 ? "#ef4444" : "#94a3b8" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function isDueOverdue(inv) { if (!inv.due_date || inv.docstatus !== 1) return false; return new Date(inv.due_date + "T23:59:59") < new Date() && (inv.outstanding_amount || 0) > 0; }

function openRow(inv) {
  if (inv.costeo) {
    router.push({ name: "CosteoDetail", params: { name: inv.costeo }, query: { step: "6", highlight: inv.name, doctype: "Sales Invoice" } });
  } else {
    router.push(`/facturas/${encodeURIComponent(inv.name)}`);
  }
}

onMounted(async () => {
  try {
    const rows = await call("costeo_yelke.api.sales_invoice_api.get_sales_invoices", { limit: 100 });
    invoices.value = rows || [];
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
});
</script>
