<template>
  <div class="flex flex-col min-h-0">
    <!-- Header -->
    <div class="px-6 pt-6 pb-4 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-ink">{{ nombre ? `Bienvenido, ${nombre}` : 'Bienvenido' }}</h1>
        <p class="text-[13px] text-ink-muted mt-0.5">Panel de control · costeo, venta, manufactura subcontratada y facturación · prendas personalizadas por empresa</p>
        <p class="text-[11px] text-ink-light mt-0.5 flex items-center gap-1"><svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Montos netos, sin IVA (el impuesto es trasladado, no es ingreso ni costo).</p>
      </div>
      <button class="doc-action" :disabled="loading" @click="load"><svg class="w-3.5 h-3.5" :class="loading ? 'animate-spin' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Actualizar</button>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center text-ink-light">
      <svg class="w-7 h-7 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
    </div>

    <div v-else-if="d" class="flex-1 overflow-y-auto px-6 pb-10 space-y-5">
      <!-- KPI cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <div class="kpi">
          <div class="kpi-ico bg-brand-50 text-brand-600"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m6 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg></div>
          <p class="kpi-val">{{ fmtN(av(d.total_costeos)) }}</p>
          <p class="kpi-lbl">Costeos</p>
        </div>
        <div class="kpi">
          <div class="kpi-ico bg-brand-50 text-brand-600"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg></div>
          <p class="kpi-val">{{ fmtC(av(d.valor_vendido)) }}</p>
          <p class="kpi-lbl">Valor vendido</p>
        </div>
        <div class="kpi">
          <div class="kpi-ico bg-brand-50 text-brand-600"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"/></svg></div>
          <p class="kpi-val">{{ fmtC(av(d.valor_facturado)) }}</p>
          <p class="kpi-lbl">Facturado</p>
        </div>
        <div class="kpi">
          <div class="kpi-ico bg-brand-50 text-brand-600"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg></div>
          <p class="kpi-val">{{ av(d.margen_prom).toFixed(1) }}<span class="text-base">%</span></p>
          <p class="kpi-lbl">Margen prom.</p>
        </div>
        <div class="kpi">
          <div class="kpi-ico bg-brand-50 text-brand-600"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"/></svg></div>
          <p class="kpi-val">{{ fmtN(av(d.prendas_vendidas)) }}</p>
          <p class="kpi-lbl">Prendas vendidas</p>
        </div>
        <div class="kpi">
          <div class="kpi-ico bg-brand-50 text-brand-600"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg></div>
          <p class="kpi-val">{{ fmtC(av(d.gasto_maquila)) }}</p>
          <p class="kpi-lbl">Gasto en maquila</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Pipeline de costeos -->
        <div class="card">
          <p class="card-title">Pipeline de costeos</p>
          <div class="space-y-2.5 mt-3">
            <div v-for="e in estadosArr" :key="e.key" class="flex items-center gap-3">
              <span class="w-28 text-[12px] text-ink-muted shrink-0">{{ e.label }}</span>
              <div class="flex-1 h-6 bg-surface-raised rounded-md overflow-hidden">
                <div class="h-full rounded-md flex items-center" :class="e.bar" :style="{ width: barPct(e.count, maxEstado) }"></div>
              </div>
              <span class="w-8 text-right text-[13px] font-semibold text-ink">{{ fmtN(av(e.count)) }}</span>
            </div>
          </div>
        </div>

        <!-- Embudo comercial -->
        <div class="card">
          <p class="card-title">Embudo comercial</p>
          <div class="space-y-3 mt-3">
            <div v-for="f in embudo" :key="f.label">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[12px] text-ink-muted">{{ f.label }}</span>
                <span class="text-[13px] font-semibold text-ink">{{ fmtC(av(f.val)) }}</span>
              </div>
              <div class="h-3 bg-surface-raised rounded-full overflow-hidden">
                <div class="h-full rounded-full" :class="f.bar" :style="{ width: barPct(f.val, embudo[0].val) }"></div>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-surface-border">
            <div class="text-center"><p class="text-lg font-bold text-ink">{{ fmtN(pct(d.valor_vendido, d.valor_cotizado) * prog) }}%</p><p class="text-[11px] text-ink-muted">Cotización → Venta</p></div>
            <div class="text-center"><p class="text-lg font-bold text-ink">{{ fmtN(pct(d.valor_facturado, d.valor_vendido) * prog) }}%</p><p class="text-[11px] text-ink-muted">Venta → Factura</p></div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Avance de producción -->
        <div class="card flex flex-col items-center justify-center">
          <p class="card-title self-start">Avance de maquila</p>
          <svg viewBox="0 0 120 120" class="w-40 h-40 my-2">
            <circle cx="60" cy="60" r="50" fill="none" stroke="var(--surface-raised, #f1f5f9)" stroke-width="12"/>
            <circle cx="60" cy="60" r="50" fill="none" stroke="#ff6b15" stroke-width="12" stroke-linecap="round"
              :stroke-dasharray="circ" :stroke-dashoffset="dashOffset" transform="rotate(-90 60 60)"/>
            <text x="60" y="56" text-anchor="middle" class="fill-ink" style="font-size:22px;font-weight:700">{{ fmtN(prodPct * prog) }}%</text>
            <text x="60" y="76" text-anchor="middle" class="fill-ink-muted" style="font-size:11px">{{ d.produccion.recibidas }}/{{ d.produccion.total }} recibidas</text>
          </svg>
          <div class="flex gap-4 text-[12px]">
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-brand-500"></span>Recibidas {{ d.produccion.recibidas }}</span>
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-slate-300"></span>Pendientes {{ d.produccion.pendientes }}</span>
          </div>
        </div>

        <!-- Top clientes -->
        <div class="card lg:col-span-2">
          <p class="card-title">Top clientes (por valor de venta)</p>
          <p v-if="!d.top_clientes.length" class="text-[13px] text-ink-muted mt-3">Sin ventas registradas.</p>
          <div class="space-y-3 mt-3">
            <div v-for="c in d.top_clientes" :key="c.customer">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[13px] font-medium text-ink truncate">{{ c.customer }}</span>
                <span class="text-[12px] text-ink-muted shrink-0 ml-2">{{ fmtC(av(c.monto)) }} · {{ fmtN(av(c.prendas)) }} prendas</span>
              </div>
              <div class="h-2.5 bg-surface-raised rounded-full overflow-hidden">
                <div class="h-full rounded-full bg-brand-500" :style="{ width: barPct(c.monto, maxCliente) }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Talleres -->
        <div class="card">
          <p class="card-title">Gasto de maquila por taller</p>
          <p v-if="!d.talleres.length" class="text-[13px] text-ink-muted mt-3">Sin subcontratación registrada.</p>
          <div class="space-y-3 mt-3">
            <div v-for="t in d.talleres" :key="t.supplier">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[13px] font-medium text-ink truncate">{{ t.supplier_name || t.supplier }}</span>
                <span class="text-[12px] text-ink-muted shrink-0 ml-2">{{ fmtC(av(t.monto)) }} · {{ t.ordenes }} OC</span>
              </div>
              <div class="h-2.5 bg-surface-raised rounded-full overflow-hidden">
                <div class="h-full rounded-full bg-gray-900" :style="{ width: barPct(t.monto, maxTaller) }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Estructura de costo vs venta -->
        <div class="card">
          <p class="card-title">Estructura de costo (subcontratación)</p>
          <div class="mt-3 space-y-3">
            <div class="h-6 flex rounded-md overflow-hidden text-[10px] font-semibold text-white">
              <div class="bg-gray-800 flex items-center justify-center" :style="{ width: barPct(d.compras_mp, costoBase) }" title="Materia prima">MP</div>
              <div class="bg-gray-900 flex items-center justify-center" :style="{ width: barPct(d.gasto_maquila, costoBase) }" title="Maquila">Maquila</div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="metric-box"><span class="w-2.5 h-2.5 rounded-full bg-gray-800 inline-block mr-1.5"></span><span class="text-[12px] text-ink-muted">Materia prima</span><p class="text-[15px] font-semibold text-ink mt-0.5">{{ fmtC(av(d.compras_mp)) }}</p></div>
              <div class="metric-box"><span class="w-2.5 h-2.5 rounded-full bg-gray-900 inline-block mr-1.5"></span><span class="text-[12px] text-ink-muted">Maquila</span><p class="text-[15px] font-semibold text-ink mt-0.5">{{ fmtC(av(d.gasto_maquila)) }}</p></div>
            </div>
            <div class="flex items-center justify-between pt-3 border-t border-surface-border">
              <span class="text-[13px] text-ink-muted">Utilidad bruta estimada</span>
              <span class="text-base font-bold" :class="utilidad >= 0 ? 'text-brand-600' : 'text-red-500'">{{ fmtC(av(utilidad)) }}</span>
            </div>
            <p class="text-[11px] text-ink-light">Facturado ({{ fmtC(av(d.valor_facturado)) }}) − costo de MP y maquila.</p>
          </div>
        </div>
      </div>

      <!-- Facturado por mes -->
      <div class="card">
        <p class="card-title">Facturación por mes</p>
        <p v-if="!d.facturado_mes.length" class="text-[13px] text-ink-muted mt-3">Sin facturas registradas.</p>
        <div v-else class="flex items-end gap-4 mt-4 h-40 px-2">
          <div v-for="mm in d.facturado_mes" :key="mm.mes" class="flex-1 flex flex-col items-center justify-end gap-2 h-full">
            <span class="text-[11px] font-semibold text-ink">{{ fmtCk(av(mm.monto)) }}</span>
            <div class="w-full max-w-[54px] bg-gradient-to-t from-brand-500 to-brand-400 rounded-t-md transition-all" :style="{ height: barPct(mm.monto, maxMes) }"></div>
            <span class="text-[11px] text-ink-muted">{{ mesLabel(mm.mes) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { call } from "@/utils/frappe.js";

const loading = ref(true);
const d = ref(null);
const prog = ref(0); // 0→1: progreso de la animación de entrada (count-up + barras)
function av(n) { return (Number(n) || 0) * prog.value; }

function animateIn() {
  prog.value = 0;
  const start = performance.now();
  const dur = 1000;
  function tick(now) {
    const t = Math.min(1, (now - start) / dur);
    prog.value = 1 - Math.pow(1 - t, 3); // easeOutCubic
    if (t < 1) requestAnimationFrame(tick);
    else prog.value = 1;
  }
  requestAnimationFrame(tick);
}

const MXN = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
const NUM = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 0 });
function fmtC(n) { return MXN.format(Number(n) || 0); }
function fmtN(n) { return NUM.format(Number(n) || 0); }
function fmtCk(n) { const v = Number(n) || 0; return v >= 1000 ? "$" + (v / 1000).toFixed(0) + "k" : fmtC(v); }
function pct(a, b) { return b ? Math.round((a / b) * 100) : 0; }
function barPct(v, max) { const p = max > 0 ? Math.min(100, (Number(v) / max) * 100) : 0; return (p * prog.value) + "%"; }
function mesLabel(m) { const [y, mo] = m.split("-"); return ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][+mo - 1] + " " + y.slice(2); }

const ESTADOS = [
  { key: "Borrador", label: "Borrador", bar: "bg-gray-300" },
  { key: "Cotizado", label: "Cotizado", bar: "bg-brand-200" },
  { key: "Orden de Venta", label: "Orden de venta", bar: "bg-brand-400" },
  { key: "En Producción", label: "En producción", bar: "bg-brand-600" },
  { key: "Completado", label: "Completado", bar: "bg-gray-900" },
];
const estadosArr = computed(() => ESTADOS.map(e => ({ ...e, count: d.value?.costeos_por_estado?.[e.key] || 0 })));
const maxEstado = computed(() => Math.max(1, ...estadosArr.value.map(e => e.count)));

const embudo = computed(() => [
  { label: "Cotizado", val: d.value?.valor_cotizado || 0, bar: "bg-brand-300" },
  { label: "Vendido", val: d.value?.valor_vendido || 0, bar: "bg-gray-900" },
  { label: "Facturado", val: d.value?.valor_facturado || 0, bar: "bg-gray-900" },
]);

const maxCliente = computed(() => Math.max(1, ...(d.value?.top_clientes || []).map(c => c.monto || 0)));
const maxTaller = computed(() => Math.max(1, ...(d.value?.talleres || []).map(t => t.monto || 0)));
const maxMes = computed(() => Math.max(1, ...(d.value?.facturado_mes || []).map(m => m.monto || 0)));
const costoBase = computed(() => Math.max(1, (d.value?.compras_mp || 0) + (d.value?.gasto_maquila || 0)));
const utilidad = computed(() => (d.value?.valor_facturado || 0) - ((d.value?.compras_mp || 0) + (d.value?.gasto_maquila || 0)));

const nombre = computed(() => (d.value?.usuario || "").split(" ")[0] || "");
const circ = 2 * Math.PI * 50;
const prodPct = computed(() => { const p = d.value?.produccion; return p && p.total ? Math.round((p.recibidas / p.total) * 100) : 0; });
const dashOffset = computed(() => circ * (1 - (prodPct.value * prog.value) / 100));

async function load() {
  loading.value = true;
  try {
    d.value = await call("costeo_yelke.api.costeo_api.dashboard_metrics");
    animateIn();
  } catch { d.value = null; }
  finally { loading.value = false; }
}
onMounted(load);
</script>

<style scoped>
.kpi { @apply bg-white rounded-xl border border-surface-border p-4 flex flex-col; }
.kpi-ico { @apply w-8 h-8 rounded-lg flex items-center justify-center mb-2.5; }
.kpi-val { @apply text-2xl font-bold text-ink leading-none; }
.kpi-lbl { @apply text-[12px] text-ink-muted mt-1.5; }
.card { @apply bg-white rounded-xl border border-surface-border p-5; }
.card-title { @apply text-sm font-semibold text-ink; }
.metric-box { @apply bg-surface-raised/50 rounded-lg p-2.5; }
.doc-action { @apply h-8 px-3 inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-muted border border-surface-border rounded-lg hover:bg-surface-raised transition-colors disabled:opacity-50; }
</style>
