<template>
  <DocumentListPage
    title="Órdenes de Compra"
    subtitle="Gestión de pedidos a proveedores"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    v-model:search="search"
    search-placeholder="Buscar proveedor, número…"
    :show-clear="!!(filterStatus || search)"
    empty-label="No hay órdenes de compra"
    empty-icon="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
    @clear="filterStatus = ''; search = ''"
    @row-click="openRow"
  >
    <template #actions>
      <button
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
        @click="router.push('/ordenes-compra/nueva')"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        Nueva OC
      </button>
    </template>

    <template #filters>
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="To Receive and Bill">Por Recibir y Facturar</option>
        <option value="To Bill">Por Facturar</option>
        <option value="To Receive">Por Recibir</option>
        <option value="Completed">Completada</option>
        <option value="Cancelled">Cancelada</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">OC / Proveedor</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Costeo</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Entrega Esp.</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
    </template>

    <template #row="{ row: po }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ po.name }}</p>
        <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ po.supplier_name || po.supplier }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[160px]">{{ po.costeo || '—' }}</td>
      <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(po.transaction_date) }}</td>
      <td class="py-3 pr-3 text-xs" :class="isOverdue(po.schedule_date, po.docstatus) ? 'text-red-500 font-medium' : 'text-gray-600'">
        {{ po.schedule_date ? fmtDate(po.schedule_date) : '—' }}
      </td>
      <td class="py-3 pr-3"><StatusBadge :docstatus="po.docstatus" :status="po.status" /></td>
      <td class="py-3 text-right">
        <span class="font-semibold text-gray-800 text-xs">{{ fmtC(po.grand_total) }}</span>
      </td>
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
const orders  = ref([]);
const search  = ref("");
const filterStatus = ref("");

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = {
      "Draft": "Borrador",
      "To Receive and Bill": "Por Recibir/Facturar",
      "To Bill": "Por Facturar",
      "To Receive": "Por Recibir",
      "Completed": "Completada",
      "Cancelled": "Cancelada",
    };
    const STATUS_COLOR = {
      "To Receive and Bill": "bg-blue-100 text-blue-700",
      "To Bill": "bg-purple-100 text-purple-700",
      "To Receive": "bg-amber-100 text-amber-700",
      "Completed": "bg-green-100 text-green-700",
    };
    return () => {
      const ds    = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Confirmada");
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
      (r.supplier || "").toLowerCase().includes(q) ||
      (r.supplier_name || "").toLowerCase().includes(q)
    );
  }
  return list;
});

const stats = computed(() => {
  const all = orders.value;
  const active = all.filter(r => r.docstatus === 1 && !["Completed","Cancelled"].includes(r.status));
  const totalActive = active.reduce((s, r) => s + (r.grand_total || 0), 0);
  const completed = all.filter(r => r.status === "Completed").length;
  const overdue = all.filter(r => r.docstatus === 1 && r.schedule_date && isOverdue(r.schedule_date, r.docstatus) && r.status !== "Completed").length;
  return [
    { label: "Total",      value: all.length,    color: "#1e293b" },
    { label: "Activas",    value: active.length,  color: "#3b82f6", sub: fmtC(totalActive) },
    { label: "Completadas", value: completed,     color: "#22c55e" },
    { label: "Vencidas",   value: overdue,        color: overdue > 0 ? "#ef4444" : "#94a3b8" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function isOverdue(dateStr, docstatus) { if (!dateStr || docstatus !== 1) return false; return new Date(dateStr + "T23:59:59") < new Date(); }

// Si la OC nace de un Costeo, ir directo al paso "Producir" de ese Costeo con esta OC
// resaltada -- es donde realmente se opera (recibos, transferencias, etc.), la vista
// standalone de abajo es solo para OCs sueltas que no vienen del flujo de Costeo.
function openRow(po) {
  if (po.costeo) {
    router.push({ name: "CosteoDetail", params: { name: po.costeo }, query: { step: "5", highlight: po.name, doctype: "Purchase Order" } });
  } else {
    router.push(`/ordenes-compra/${encodeURIComponent(po.name)}`);
  }
}

async function load() {
  loading.value = true;
  try {
    const rows = await call("costeo_yelke.api.purchase_order_api.get_purchase_orders", { limit: 100, company: companyState.selected || undefined });
    orders.value = rows || [];
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
}

onMounted(load);
watch(() => companyState.selected, load);
</script>
