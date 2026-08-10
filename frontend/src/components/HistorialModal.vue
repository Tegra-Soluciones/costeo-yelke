<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] flex flex-col">
      <div class="flex items-start justify-between px-5 py-4 border-b border-surface-border flex-shrink-0">
        <div>
          <p class="text-sm font-semibold text-ink">Historial del costeo</p>
          <p class="text-[11.5px] text-ink-muted mt-0.5">Cómo se llegó hasta aquí — costeos y cotizaciones, en orden</p>
        </div>
        <button class="w-7 h-7 rounded-full hover:bg-surface-raised flex items-center justify-center text-ink-light flex-shrink-0" @click="$emit('close')">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-5 py-5">
        <div v-if="loading" class="flex items-center justify-center py-12">
          <svg class="w-6 h-6 animate-spin text-ink-light" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        </div>

        <div v-else-if="!cadena.length" class="text-center py-12 text-[13px] text-ink-light">
          Sin historial todavía.
        </div>

        <div v-else class="relative">
          <div class="absolute left-[15px] top-3 bottom-3 w-px bg-surface-border" />

          <div v-for="(c, idx) in cadena" :key="c.name" class="relative pl-10" :class="idx < cadena.length - 1 ? 'pb-7' : ''">
            <!-- Nodo del costeo -->
            <span
              class="absolute left-0 top-0 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              :class="c.name === costeo ? 'bg-brand-500 text-white ring-4 ring-brand-100' : (costeoBadge(c, idx).tone === 'gray' ? 'bg-surface-raised text-ink-light border border-surface-border' : 'bg-brand-50 text-brand-600 border border-brand-100')"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M9 7h6M9 11h6M9 15h4M6 3h12a1 1 0 011 1v16a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z"/></svg>
            </span>

            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13px] font-semibold text-ink font-mono">{{ c.name }}</span>
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full" :class="badgeClass(costeoBadge(c, idx).tone)">{{ costeoBadge(c, idx).label }}</span>
              <span v-if="c.name === costeo" class="text-[10.5px] font-semibold text-brand-600">· estás viendo esta</span>
            </div>
            <p class="text-[11px] text-ink-light mt-0.5">{{ fmtDate(c.creation) }}</p>
            <p v-if="c.motivo_revision" class="text-[12px] text-ink-muted mt-1 italic">"{{ c.motivo_revision }}"</p>

            <!-- Cotizaciones generadas por esta versión del costeo -->
            <div v-if="cotizacionesDe(c.name).length" class="mt-3 space-y-2.5">
              <div v-for="q in cotizacionesDe(c.name)" :key="q.name" class="ml-1 pl-3 border-l-2" :class="q.name === currentQuotation ? 'border-brand-300' : 'border-surface-border'">
                <div class="flex items-center gap-2 flex-wrap">
                  <svg class="w-3.5 h-3.5 text-ink-light flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  <span class="text-[12.5px] font-medium text-ink-muted font-mono">{{ q.name }}</span>
                  <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded-full" :class="badgeClass(quotBadge(q).tone)">{{ quotBadge(q).label }}</span>
                  <span v-if="q.name === currentQuotation" class="text-[10px] font-semibold text-brand-600">· esta cotización</span>
                </div>
                <p class="text-[11px] text-ink-light mt-0.5">{{ fmtDate(q.creation) }}<template v-if="q.grand_total"> · {{ fmtC(q.grand_total) }}</template></p>
                <p v-if="q.order_lost_reason" class="text-[11.5px] text-red-500 mt-0.5">{{ q.order_lost_reason }}</p>
              </div>
            </div>
            <p v-else class="text-[11.5px] text-ink-xlight mt-2 ml-1">Sin cotización generada todavía</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({
  open: { type: Boolean, default: false },
  costeo: { type: String, default: "" },
  // Nombre de la cotización que se está viendo actualmente (opcional, solo para resaltarla en la lista).
  currentQuotation: { type: String, default: "" },
});
defineEmits(["close"]);

const loading = ref(false);
const cadena = ref([]);
const cotizaciones = ref([]);

watch(() => props.open, async (isOpen) => {
  if (!isOpen || !props.costeo) return;
  loading.value = true;
  cadena.value = [];
  cotizaciones.value = [];
  try {
    const res = await call("costeo_yelke.api.costeo_api.get_historial_costeo", { costeo: props.costeo });
    cadena.value = res?.cadena || [];
    cotizaciones.value = res?.cotizaciones || [];
  } finally {
    loading.value = false;
  }
});

function cotizacionesDe(costeoName) {
  return cotizaciones.value.filter((q) => q.costeo === costeoName);
}

function fmtDate(s) {
  if (!s) return "";
  return new Date(s).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}
function fmtC(v) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0);
}

// Un costeo quedó "Reemplazado" si existe una revisión posterior en la cadena (no es
// el último eslabón) -- eso importa más para trazabilidad que su docstatus crudo.
function costeoBadge(c, idx) {
  if (idx < cadena.value.length - 1) return { label: "Reemplazado", tone: "gray" };
  if (c.docstatus === 2) return { label: "Cancelado", tone: "red" };
  if (c.docstatus === 1) return { label: "Vigente", tone: "green" };
  return { label: "Borrador", tone: "amber" };
}

const QUOT_LABELS = {
  Draft: "Borrador", Open: "Vigente", Ordered: "Convertida a venta",
  "Partially Ordered": "Parcialmente ordenada", Lost: "Rechazada",
  Cancelled: "Cancelada", Expired: "Vencida",
};
function quotBadge(q) {
  const label = QUOT_LABELS[q.status] || q.status;
  let tone = "amber";
  if (q.status === "Lost" || q.status === "Cancelled") tone = "red";
  else if (q.status === "Ordered" || q.status === "Partially Ordered") tone = "green";
  else if (q.status === "Expired") tone = "gray";
  return { label, tone };
}

function badgeClass(tone) {
  return {
    green: "bg-green-50 text-green-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-600",
    gray: "bg-surface-raised text-ink-light",
  }[tone];
}
</script>
