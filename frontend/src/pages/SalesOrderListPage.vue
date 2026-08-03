<template>
  <div class="flex flex-col h-full">
    <PageHeader title="Órdenes de Venta" subtitle="Seguimiento de pedidos confirmados">
      <button
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
        @click="router.push('/ordenes-venta/nueva')"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        Nueva OV
      </button>
    </PageHeader>

    <!-- Stats -->
    <div class="px-5 pt-4 pb-2 grid grid-cols-4 gap-3 flex-shrink-0">
      <div v-for="s in stats" :key="s.label" class="bg-white border border-gray-200 rounded-xl px-4 py-3">
        <p class="text-xs text-gray-400 font-medium">{{ s.label }}</p>
        <p class="text-xl font-bold mt-1" :style="{ color: s.color || '#1e293b' }">{{ s.value }}</p>
        <p v-if="s.sub" class="text-xs text-gray-400 mt-0.5">{{ s.sub }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="px-5 py-2 flex items-center gap-3 flex-shrink-0">
      <input
        v-model="search"
        type="text"
        placeholder="Buscar cliente, número…"
        class="h-8 px-3 text-sm border border-gray-200 rounded-lg flex-1 max-w-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
      <select v-model="filterStatus" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Draft">Borrador</option>
        <option value="To Deliver and Bill">Por Entregar y Facturar</option>
        <option value="To Bill">Por Facturar</option>
        <option value="To Deliver">Por Entregar</option>
        <option value="Completed">Completada</option>
        <option value="Cancelled">Cancelada</option>
      </select>
      <button v-if="filterStatus || search" class="text-xs text-gray-400 hover:text-gray-600" @click="filterStatus = ''; search = ''">
        Limpiar
      </button>
    </div>

    <!-- Table -->
    <div class="flex-1 overflow-y-auto px-5 pb-5">
      <div v-if="loading" class="flex items-center justify-center h-40">
        <svg class="w-6 h-6 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </div>
      <div v-else-if="!filtered.length" class="flex flex-col items-center justify-center h-40 text-gray-400">
        <svg class="w-8 h-8 mb-2 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
        </svg>
        <p class="text-sm">No hay órdenes de venta</p>
      </div>
      <table v-else class="w-full text-sm">
        <thead class="sticky top-0 bg-white z-10">
          <tr class="border-b border-gray-100">
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">OV / Cliente</th>
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Entrega</th>
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
            <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr
            v-for="so in filtered"
            :key="so.name"
            class="group cursor-pointer hover:bg-gray-50 transition-colors"
            @click="router.push(`/ordenes-venta/${encodeURIComponent(so.name)}`)"
          >
            <td class="py-3 pr-3">
              <div class="flex items-center gap-2.5">
                <!-- Avatar -->
                <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold" :style="{ background: avatarColor(so.customer_name || so.customer) }">
                  {{ initials(so.customer_name || so.customer) }}
                </div>
                <div>
                  <p class="font-semibold text-gray-800 text-xs">{{ so.name }}</p>
                  <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ so.customer_name || so.customer }}</p>
                </div>
              </div>
            </td>
            <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(so.transaction_date) }}</td>
            <td class="py-3 pr-3 text-xs" :class="isOverdue(so.delivery_date, so.docstatus) ? 'text-red-500 font-medium' : 'text-gray-600'">
              {{ so.delivery_date ? fmtDate(so.delivery_date) : '—' }}
            </td>
            <td class="py-3 pr-3">
              <StatusBadge :docstatus="so.docstatus" :status="so.status" />
            </td>
            <td class="py-3 text-right">
              <span class="font-semibold text-gray-800 text-xs">{{ fmtC(so.grand_total, so.currency) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import { call } from "@/utils/frappe.js";

const router = useRouter();
const loading = ref(true);
const orders  = ref([]);
const search  = ref("");
const filterStatus = ref("");

// ── StatusBadge ───────────────────────────────────────────────────────────────
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
    const COLOR = {
      0: "bg-gray-100 text-gray-500",
      2: "bg-gray-100 text-gray-400",
    };
    const STATUS_COLOR = {
      "To Deliver and Bill": "bg-blue-100 text-blue-700",
      "To Bill": "bg-purple-100 text-purple-700",
      "To Deliver": "bg-amber-100 text-amber-700",
      "Completed": "bg-green-100 text-green-700",
      "Cancelled": "bg-gray-100 text-gray-400",
    };
    return () => {
      const ds  = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Abierta");
      const cls   = ds === 0 ? COLOR[0] : ds === 2 ? COLOR[2] : (STATUS_COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

// ── Computed ──────────────────────────────────────────────────────────────────
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

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v, currency = "MXN") {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0);
}
function isOverdue(dateStr, docstatus) {
  if (!dateStr || docstatus !== 1) return false;
  return new Date(dateStr + "T23:59:59") < new Date();
}
function initials(name) {
  if (!name) return "?";
  return name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
}
const AVATAR_COLORS = ["#6366f1","#f59e0b","#10b981","#3b82f6","#ef4444","#8b5cf6","#ec4899","#14b8a6"];
function avatarColor(name) {
  let h = 0;
  for (let i = 0; i < (name || "").length; i++) h = (h * 31 + name.charCodeAt(i)) % AVATAR_COLORS.length;
  return AVATAR_COLORS[Math.abs(h)];
}

// ── Mount ─────────────────────────────────────────────────────────────────────
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
