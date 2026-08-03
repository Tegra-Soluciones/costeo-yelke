<template>
  <div class="flex flex-col h-full">
    <PageHeader title="Facturas de Venta" subtitle="Facturación a clientes">
      <button
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
        @click="router.push('/facturas/nueva')"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        Nueva Factura
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
        <option value="Unpaid">Sin Pagar</option>
        <option value="Paid">Pagada</option>
        <option value="Partly Paid">Pago Parcial</option>
        <option value="Overdue">Vencida</option>
        <option value="Cancelled">Cancelada</option>
      </select>
      <button v-if="filterStatus || search" class="text-xs text-gray-400 hover:text-gray-600" @click="filterStatus = ''; search = ''">Limpiar</button>
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
        <svg class="w-8 h-8 mb-2 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
        <p class="text-sm">No hay facturas</p>
      </div>
      <table v-else class="w-full text-sm">
        <thead class="sticky top-0 bg-white z-10">
          <tr class="border-b border-gray-100">
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Factura / Cliente</th>
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Emisión</th>
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Vencimiento</th>
            <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
            <th class="text-right py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Total</th>
            <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Saldo</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr
            v-for="inv in filtered"
            :key="inv.name"
            class="group cursor-pointer hover:bg-gray-50 transition-colors"
            @click="router.push(`/facturas/${encodeURIComponent(inv.name)}`)"
          >
            <td class="py-3 pr-3">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold" :style="{ background: avatarColor(inv.customer_name || inv.customer) }">
                  {{ initials(inv.customer_name || inv.customer) }}
                </div>
                <div>
                  <p class="font-semibold text-gray-800 text-xs">{{ inv.name }}</p>
                  <p class="text-xs text-gray-400 truncate max-w-[180px]">{{ inv.customer_name || inv.customer }}</p>
                </div>
              </div>
            </td>
            <td class="py-3 pr-3 text-xs text-gray-600">{{ fmtDate(inv.posting_date) }}</td>
            <td class="py-3 pr-3 text-xs" :class="isDueOverdue(inv) ? 'text-red-500 font-medium' : 'text-gray-600'">
              {{ inv.due_date ? fmtDate(inv.due_date) : '—' }}
            </td>
            <td class="py-3 pr-3"><StatusBadge :docstatus="inv.docstatus" :status="inv.status" /></td>
            <td class="py-3 pr-3 text-right text-xs font-semibold text-gray-800">{{ fmtC(inv.grand_total) }}</td>
            <td class="py-3 text-right text-xs" :class="(inv.outstanding_amount || 0) > 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'">
              {{ inv.docstatus === 1 ? fmtC(inv.outstanding_amount) : '—' }}
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
function initials(name) { if (!name) return "?"; return name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase(); }
const AVATAR_COLORS = ["#6366f1","#f59e0b","#10b981","#3b82f6","#ef4444","#8b5cf6","#ec4899","#14b8a6"];
function avatarColor(name) { let h = 0; for (let i = 0; i < (name||"").length; i++) h = (h*31+name.charCodeAt(i)) % AVATAR_COLORS.length; return AVATAR_COLORS[Math.abs(h)]; }

onMounted(async () => {
  try {
    const rows = await call("costeo_yelke.api.sales_invoice_api.get_sales_invoices", { limit: 100 });
    invoices.value = rows || [];
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
});
</script>
