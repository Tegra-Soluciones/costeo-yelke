<template>
  <DocumentListPage
    title="Órdenes de Venta"
    subtitle="Seguimiento de pedidos confirmados"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    v-model:search="search"
    search-placeholder="Buscar cliente, número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay órdenes de venta"
    empty-icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #actions>
      <button
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
        @click="router.push('/ordenes-venta/nueva')"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        Nueva OV
      </button>
    </template>

    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="To Deliver and Bill">Por Entregar y Facturar</option>
        <option value="To Bill">Por Facturar</option>
        <option value="To Deliver">Por Entregar</option>
        <option value="Completed">Completada</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">OV / Cliente</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Entrega</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
    </template>

    <template #row="{ row: so }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ so.name }}</p>
        <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ so.customer_name || so.customer }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ so.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(so.transaction_date) }}</td>
      <td class="py-3 pr-3 text-xs" :class="isOverdue(so.delivery_date, so.docstatus) ? 'text-red-500 font-medium' : 'text-gray-600'">
        {{ so.delivery_date ? fmtDate(so.delivery_date) : '—' }}
      </td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="so.docstatus" :status="so.status" /></td>
      <td class="py-3 text-right"><span class="font-semibold text-gray-800 text-xs">{{ fmtC(so.grand_total) }}</span></td>
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
const orders  = ref([]);
const search  = ref("");
const filterStatus = ref("");

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = {
      "Draft": "Borrador",
      "To Deliver and Bill": "Por Entregar/Facturar",
      "To Bill": "Por Facturar",
      "To Deliver": "Por Entregar",
      "Completed": "Completada",
      "Cancelled": "Cancelada",
    };
    const STATUS_COLOR = {
      "To Deliver and Bill": "bg-blue-100 text-blue-700",
      "To Bill": "bg-purple-100 text-purple-700",
      "To Deliver": "bg-amber-100 text-amber-700",
      "Completed": "bg-green-100 text-green-700",
    };
    return () => {
      const ds  = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Abierta");
      const cls   = ds === 0 ? "bg-gray-100 text-gray-500" : ds === 2 ? "bg-gray-100 text-gray-400" : (STATUS_COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

const filtered = computed(() => {
  let list = orders.value;
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
  const all = orders.value;
  const active = all.filter(r => r.docstatus === 1 && !["Completed","Cancelled"].includes(r.status));
  const totalActive = active.reduce((s, r) => s + (r.grand_total || 0), 0);
  const completed = all.filter(r => r.status === "Completed").length;
  const overdue = all.filter(r => r.docstatus === 1 && r.delivery_date && isOverdue(r.delivery_date, r.docstatus) && r.status !== "Completed").length;
  return [
    { label: "Total",     value: all.length,       color: "#1e293b" },
    { label: "Activas",   value: active.length,    color: "#3b82f6", sub: fmtC(totalActive) },
    { label: "Completadas", value: completed,       color: "#22c55e" },
    { label: "Vencidas",  value: overdue,           color: overdue > 0 ? "#ef4444" : "#94a3b8" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function isOverdue(dateStr, docstatus) {
  if (!dateStr || docstatus !== 1) return false;
  return new Date(dateStr + "T23:59:59") < new Date();
}

// Si la OV nace de un Costeo, ir directo al paso "Vender" de ese Costeo con esta OV
// resaltada -- la vista standalone de abajo es solo para OV sueltas fuera del flujo.
function openRow(so) {
  if (so.costeo) {
    router.push({ name: "CosteoDetail", params: { name: so.costeo }, query: { step: "2", highlight: so.name, doctype: "Sales Order" } });
  } else {
    router.push(`/ordenes-venta/${encodeURIComponent(so.name)}`);
  }
}

onMounted(async () => {
  try {
    const rows = await call("costeo_yelke.api.sales_order_api.get_sales_orders", { limit: 100 });
    orders.value = rows || [];
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});
</script>
