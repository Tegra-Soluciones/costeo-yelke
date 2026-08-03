<template>
  <div class="flex flex-col h-full">
    <PageHeader title="Cotizaciones" subtitle="Gestión de cotizaciones a clientes">
      <RouterLink
        to="/cotizaciones/nueva"
        class="px-3 py-1.5 bg-brand-500 text-white text-sm font-medium rounded-md hover:bg-brand-600 transition-colors flex items-center gap-1.5"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        Nueva Cotización
      </RouterLink>
    </PageHeader>

    <!-- Filter bar -->
    <div class="flex items-center gap-3 px-5 py-3 bg-white border-b border-gray-100 flex-shrink-0">
      <div class="flex gap-1 flex-wrap">
        <button
          v-for="s in STATUS_FILTERS"
          :key="s.value"
          class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap"
          :class="filterStatus === s.value
            ? 'bg-brand-500 text-white shadow-sm'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          @click="filterStatus = s.value; load()"
        >{{ s.label }}</button>
      </div>
      <div class="flex-1" />
      <div class="relative">
        <svg class="absolute left-2.5 top-2 w-3.5 h-3.5 text-gray-400 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input
          v-model="search"
          type="text"
          placeholder="Buscar cliente…"
          class="pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg w-48 focus:outline-none focus:ring-2 focus:ring-brand-400"
          @keyup.enter="load"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <!-- Empty -->
    <div v-else-if="!rows.length" class="flex-1 flex flex-col items-center justify-center gap-3 text-gray-400">
      <div class="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center">
        <svg class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <p class="text-sm font-medium text-gray-500">Sin cotizaciones</p>
      <RouterLink to="/cotizaciones/nueva" class="text-xs text-brand-600 hover:text-brand-700 font-medium">
        Crear primera cotización →
      </RouterLink>
    </div>

    <!-- List -->
    <div v-else class="flex-1 overflow-y-auto p-5 space-y-5">

      <!-- Summary stats -->
      <div class="grid grid-cols-4 gap-3">
        <div v-for="stat in stats" :key="stat.label" class="bg-white rounded-xl border border-gray-200 px-4 py-3">
          <p class="text-xs text-gray-400 font-medium">{{ stat.label }}</p>
          <p class="text-xl font-bold mt-0.5" :class="stat.color">{{ stat.value }}</p>
          <p v-if="stat.sub" class="text-xs text-gray-400 mt-0.5">{{ stat.sub }}</p>
        </div>
      </div>

      <!-- Quotation rows -->
      <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
        <!-- Column headers -->
        <div class="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 px-5 py-2.5 border-b border-gray-100 bg-gray-50/80">
          <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Cliente / Cotización</span>
          <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider text-right w-32">Total</span>
          <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center w-28">Válida hasta</span>
          <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center w-24">Estado</span>
        </div>

        <div class="divide-y divide-gray-50">
          <div
            v-for="row in rows"
            :key="row.name"
            class="group relative grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 px-5 py-3.5 hover:bg-brand-50/30 cursor-pointer transition-colors"
            :style="`border-left: 3px solid ${statusColor(row)}`"
            @click="$router.push(`/cotizaciones/${encodeURIComponent(row.name)}`)"
          >
            <!-- Left: avatar + customer -->
            <div class="flex items-center gap-3 min-w-0">
              <div
                class="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                :style="`background-color: ${statusColor(row)}20; color: ${statusColor(row)}`"
              >
                {{ initials(row.customer_name || row.party_name) }}
              </div>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-gray-900 truncate">{{ row.customer_name || row.party_name || '—' }}</p>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="font-mono text-xs text-gray-400">{{ row.name }}</span>
                  <span class="text-gray-200">·</span>
                  <span class="text-xs text-gray-400">{{ fmtDate(row.transaction_date) }}</span>
                </div>
              </div>
            </div>

            <!-- Total -->
            <div class="text-right w-32">
              <p class="text-sm font-bold text-gray-900">{{ fmtC(row.grand_total) }}</p>
              <p class="text-xs text-gray-400">{{ row.currency }}</p>
            </div>

            <!-- Validity -->
            <div class="w-28 text-center">
              <template v-if="row.valid_till">
                <p class="text-xs font-medium" :class="isExpired(row.valid_till) ? 'text-red-500' : daysLeft(row.valid_till) <= 7 ? 'text-amber-600' : 'text-gray-600'">
                  {{ fmtDate(row.valid_till) }}
                </p>
                <p v-if="isExpired(row.valid_till)" class="text-xs text-red-400 font-medium">Vencida</p>
                <p v-else class="text-xs text-gray-400">{{ daysLeft(row.valid_till) }}d restantes</p>
              </template>
              <span v-else class="text-xs text-gray-300">—</span>
            </div>

            <!-- Status badge -->
            <div class="w-24 flex justify-center">
              <StatusPill :status="row.status" :docstatus="row.docstatus" />
            </div>

            <!-- Hover chevron -->
            <div class="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
              <svg class="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
              </svg>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from "vue";
import { RouterLink } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import { call }   from "@/utils/frappe.js";

const STATUS_FILTERS = [
  { label: "Todos",      value: "" },
  { label: "Borrador",   value: "Draft" },
  { label: "Abiertos",   value: "Open" },
  { label: "Ordenados",  value: "Ordered" },
  { label: "Perdidos",   value: "Lost" },
  { label: "Cancelados", value: "Cancelled" },
];

const STATUS_COLOR_MAP = {
  Draft:     "#94a3b8",
  Open:      "#3b82f6",
  Ordered:   "#22c55e",
  Lost:      "#ef4444",
  Cancelled: "#d1d5db",
};

const STATUS_PILL_CLASSES = {
  Draft:     "bg-gray-100 text-gray-600",
  Open:      "bg-blue-100 text-blue-700",
  Ordered:   "bg-green-100 text-green-700",
  Lost:      "bg-red-100 text-red-600",
  Cancelled: "bg-gray-100 text-gray-400",
};

const STATUS_LABELS_ES = {
  Draft:     "Borrador",
  Open:      "Abierta",
  Ordered:   "Ordenada",
  Lost:      "Perdida",
  Cancelled: "Cancelada",
};

const StatusPill = defineComponent({
  props: { status: String, docstatus: Number },
  setup(p) {
    return () => {
      const key   = p.docstatus === 0 ? "Draft" : (p.status || "Open");
      const label = STATUS_LABELS_ES[key] || key;
      const cls   = STATUS_PILL_CLASSES[key] || "bg-gray-100 text-gray-500";
      return h("span", {
        class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`,
      }, label);
    };
  },
});

const loading      = ref(true);
const rows         = ref([]);
const filterStatus = ref("");
const search       = ref("");

function statusColor(row) {
  const key = row.docstatus === 0 ? "Draft" : (row.status || "Open");
  return STATUS_COLOR_MAP[key] || "#94a3b8";
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").slice(0, 2).map(w => w[0]?.toUpperCase() || "").join("");
}

function fmtDate(s) {
  if (!s) return "—";
  return new Date(s + "T00:00:00").toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtC(v) {
  return new Intl.NumberFormat("es-MX", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v || 0);
}
function isExpired(dateStr) {
  if (!dateStr) return false;
  return new Date(dateStr + "T23:59:59") < new Date();
}
function daysLeft(dateStr) {
  if (!dateStr) return 0;
  const diff = new Date(dateStr + "T23:59:59") - new Date();
  return Math.max(0, Math.ceil(diff / 86400000));
}

const stats = computed(() => {
  const all    = rows.value;
  const open   = all.filter(r => r.status === "Open" || r.docstatus === 0);
  const ordered = all.filter(r => r.status === "Ordered");
  const expired = all.filter(r => r.valid_till && isExpired(r.valid_till) && r.docstatus !== 2);
  const totalOpen = open.reduce((s, r) => s + (r.grand_total || 0), 0);
  return [
    { label: "Total",        value: all.length,    color: "text-gray-800",   sub: "cotizaciones" },
    { label: "En pipeline",  value: open.length,   color: "text-blue-600",   sub: `$${fmtC(totalOpen)}` },
    { label: "Ordenadas",    value: ordered.length, color: "text-green-600", sub: "convertidas" },
    { label: "Vencidas",     value: expired.length, color: "text-red-500",   sub: "sin renovar" },
  ];
});

async function load() {
  loading.value = true;
  try {
    const args = { limit: 100 };
    if (filterStatus.value) args.status = filterStatus.value;
    if (search.value.trim()) args.customer = search.value.trim();
    rows.value = await call("costeo_yelke.api.quotation_api.get_quotations", args);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
