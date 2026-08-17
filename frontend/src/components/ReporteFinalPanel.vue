<template>
  <div class="max-w-5xl mx-auto space-y-4">
    <div v-if="loading" class="bg-white rounded-xl border border-surface-border p-10 text-center text-ink-muted text-sm">Calculando reporte…</div>

    <template v-else-if="r">
      <!-- Encabezado -->
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-semibold text-ink">Reporte final — {{ r.cliente }}</p>
          <p class="text-[12px] text-ink-muted">Costos y rentabilidad reales tomados de los documentos ya validados. Todos los montos son sin IVA.</p>
        </div>
        <span class="text-[11px] font-semibold px-2.5 py-1 rounded-full" :class="r.completo ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">
          {{ r.completo ? 'Proceso completo' : 'Con documentos pendientes' }}
        </span>
      </div>

      <p v-if="!r.completo" class="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
        Aún hay documentos en borrador — los números reales pueden seguir moviéndose: {{ pendientesTexto }}.
      </p>

      <!-- Hero: rentabilidad -->
      <div class="grid grid-cols-3 gap-3">
        <div class="bg-white rounded-xl border border-surface-border p-4">
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1">Rentabilidad estimada</p>
          <p class="text-2xl font-semibold text-ink">{{ pct(r.estimado.rentabilidad_pct) }}</p>
          <p class="text-[13px] text-ink-muted mt-0.5">{{ fmtC(r.estimado.rentabilidad_monto) }}</p>
        </div>
        <div v-if="r.real.sales_invoice" class="bg-white rounded-xl border-2 p-4" :class="r.real.rentabilidad_monto >= 0 ? 'border-green-300' : 'border-red-300'">
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1">Rentabilidad real</p>
          <p class="text-2xl font-semibold" :class="r.real.rentabilidad_monto >= 0 ? 'text-green-700' : 'text-red-600'">{{ pct(r.real.rentabilidad_pct) }}</p>
          <p class="text-[13px] mt-0.5" :class="r.real.rentabilidad_monto >= 0 ? 'text-green-700' : 'text-red-600'">{{ fmtC(r.real.rentabilidad_monto) }}</p>
        </div>
        <div v-else class="bg-white rounded-xl border border-dashed border-surface-border p-4">
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1">Rentabilidad real</p>
          <p class="text-[13px] text-ink-light mt-1">Se calcula al validar la factura de venta.</p>
        </div>
        <div class="bg-white rounded-xl border border-surface-border p-4">
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1">Variación vs estimado</p>
          <template v-if="r.real.sales_invoice">
            <p class="text-2xl font-semibold" :class="varClass(r.variacion.rentabilidad_pct_puntos)">{{ signed(r.variacion.rentabilidad_pct_puntos, 1) }} pts</p>
            <p class="text-[13px] mt-0.5" :class="varClass(r.variacion.rentabilidad_monto)">{{ signedC(r.variacion.rentabilidad_monto) }}</p>
          </template>
          <p v-else class="text-[13px] text-ink-light mt-1">—</p>
        </div>
      </div>

      <!-- Comparativo visual -->
      <div class="bg-white rounded-xl border border-surface-border p-4">
        <p class="section-title mb-3">Comparativo visual</p>

        <!-- Costo total: estimado vs real -->
        <div class="mb-4">
          <p class="text-[11.5px] font-medium text-ink-muted mb-1.5">Costo total</p>
          <div class="space-y-1.5">
            <div class="flex items-center gap-2">
              <span class="text-[10.5px] text-ink-light w-12 shrink-0">Estimado</span>
              <div class="flex-1 h-5 bg-surface-raised rounded overflow-hidden"><div class="h-full bg-gray-300 rounded" :style="{ width: barPct(r.estimado.costo_total, maxCosto) + '%' }"></div></div>
              <span class="text-[12px] font-medium w-24 text-right shrink-0">{{ fmtC(r.estimado.costo_total) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10.5px] text-ink-light w-12 shrink-0">Real</span>
              <div class="flex-1 h-5 bg-surface-raised rounded overflow-hidden"><div class="h-full rounded transition-all" :class="r.real.costo_total > r.estimado.costo_total ? 'bg-red-400' : 'bg-green-400'" :style="{ width: barPct(r.real.costo_total, maxCosto) + '%' }"></div></div>
              <span class="text-[12px] font-medium w-24 text-right shrink-0">{{ fmtC(r.real.costo_total) }}</span>
            </div>
          </div>
        </div>

        <!-- Desglose por categoría: estimado vs real -->
        <div class="space-y-3 mb-4">
          <div v-for="cat in categorias" :key="cat.label">
            <p class="text-[11.5px] font-medium text-ink-muted mb-1">{{ cat.label }}</p>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10.5px] text-ink-light w-12 shrink-0">Est.</span>
              <div class="flex-1 h-3.5 bg-surface-raised rounded overflow-hidden"><div class="h-full bg-gray-300 rounded" :style="{ width: barPct(cat.est, maxCat) + '%' }"></div></div>
              <span class="text-[11px] w-20 text-right shrink-0">{{ fmtC(cat.est) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10.5px] text-ink-light w-12 shrink-0">Real</span>
              <div class="flex-1 h-3.5 bg-surface-raised rounded overflow-hidden"><div class="h-full rounded transition-all" :class="cat.real > cat.est ? 'bg-red-400' : 'bg-brand-400'" :style="{ width: barPct(cat.real, maxCat) + '%' }"></div></div>
              <span class="text-[11px] w-20 text-right shrink-0 font-medium">{{ fmtC(cat.real) }}</span>
            </div>
          </div>
        </div>

        <!-- Composición del costo real -->
        <div>
          <p class="text-[11.5px] font-medium text-ink-muted mb-1.5">¿En qué se fue el costo real?</p>
          <div class="flex h-4 rounded overflow-hidden w-full">
            <div v-for="seg in composicionReal" :key="seg.label" :class="seg.color" :style="{ width: seg.pct + '%' }" :title="`${seg.label}: ${fmtC(seg.value)} (${seg.pct.toFixed(1)}%)`"></div>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2">
            <span v-for="seg in composicionReal" :key="'l' + seg.label" class="flex items-center gap-1.5 text-[11px] text-ink-muted">
              <span class="w-2.5 h-2.5 rounded-sm shrink-0" :class="seg.color"></span>{{ seg.label }} · {{ seg.pct.toFixed(1) }}%
            </span>
          </div>
        </div>
      </div>

      <!-- Ingresos -->
      <div class="bg-white rounded-xl border border-surface-border p-4">
        <p class="section-title mb-2">Ingresos (sin IVA)</p>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-1.5">Concepto</th><th class="py-1.5 text-right">Estimado</th><th class="py-1.5 text-right">Real</th><th class="py-1.5 text-right">Variación</th></tr></thead>
          <tbody>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Venta</td>
              <td class="py-1.5 text-right">{{ fmtC(r.estimado.venta_total) }}</td>
              <td class="py-1.5 text-right font-medium">{{ r.real.sales_invoice ? fmtC(r.real.ingreso) : '— sin factura —' }}</td>
              <td class="py-1.5 text-right" :class="varClass(r.variacion.venta_monto)">{{ r.real.sales_invoice ? `${signedC(r.variacion.venta_monto)} (${signed(r.variacion.venta_pct, 1)}%)` : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="r.real.sales_invoice" class="text-[11px] text-ink-light mt-2">Factura: {{ r.real.sales_invoice }}</p>
      </div>

      <!-- Costos -->
      <div class="bg-white rounded-xl border border-surface-border p-4">
        <p class="section-title mb-2">Costos (sin IVA)</p>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-1.5">Concepto</th><th class="py-1.5 text-right">Estimado</th><th class="py-1.5 text-right">Real</th><th class="py-1.5 text-right">Variación</th></tr></thead>
          <tbody>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Materia prima</td>
              <td class="py-1.5 text-right">{{ fmtC(r.estimado.materiales_total) }}</td>
              <td class="py-1.5 text-right">{{ fmtC(r.real.material_directo) }}</td>
              <td class="py-1.5 text-right" :class="varClass(r.real.material_directo - r.estimado.materiales_total, true)">{{ signedC(r.real.material_directo - r.estimado.materiales_total) }}</td>
            </tr>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Flete de materia prima (compra)</td>
              <td class="py-1.5 text-right text-ink-light">—</td>
              <td class="py-1.5 text-right">{{ fmtC(r.real.flete_materiales) }}</td>
              <td class="py-1.5 text-right text-ink-light">—</td>
            </tr>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Servicios de subcontratación</td>
              <td class="py-1.5 text-right">{{ fmtC(r.estimado.servicios_total) }}</td>
              <td class="py-1.5 text-right">{{ fmtC(r.real.servicio_directo) }}</td>
              <td class="py-1.5 text-right" :class="varClass(r.real.servicio_directo - r.estimado.servicios_total, true)">{{ signedC(r.real.servicio_directo - r.estimado.servicios_total) }}</td>
            </tr>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Flete al taller (ida)</td>
              <td class="py-1.5 text-right text-ink-light">—</td>
              <td class="py-1.5 text-right">{{ fmtC(r.real.flete_taller_ida) }}</td>
              <td class="py-1.5 text-right text-ink-light">—</td>
            </tr>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Flete del taller (regreso)</td>
              <td class="py-1.5 text-right text-ink-light">—</td>
              <td class="py-1.5 text-right">{{ fmtC(r.real.flete_taller_regreso) }}</td>
              <td class="py-1.5 text-right text-ink-light">—</td>
            </tr>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Flete de entrega al cliente</td>
              <td class="py-1.5 text-right">{{ fmtC(r.estimado.shipping_total) }}</td>
              <td class="py-1.5 text-right">{{ fmtC(r.real.flete_cliente) }}</td>
              <td class="py-1.5 text-right" :class="varClass(r.real.flete_cliente - r.estimado.shipping_total, true)">{{ signedC(r.real.flete_cliente - r.estimado.shipping_total) }}</td>
            </tr>
            <tr class="border-b border-surface-border/60">
              <td class="py-1.5">Overhead <span class="text-ink-light font-normal">({{ r.estimado.overhead_pct_promedio.toFixed(1) }}% prom.)</span></td>
              <td class="py-1.5 text-right">
                {{ fmtC(r.estimado.overhead_total) }}
                <span class="block text-[10.5px] text-ink-light font-normal">{{ fmtC(r.estimado.overhead_unit) }}/u · {{ r.estimado.qty_total }} u</span>
              </td>
              <td class="py-1.5 text-right">
                {{ fmtC(r.real.overhead) }}
                <span v-if="r.real.qty_total" class="block text-[10.5px] text-ink-light font-normal">{{ fmtC(r.real.overhead_unit) }}/u · {{ r.real.qty_total }} u</span>
                <span v-else class="block text-[10.5px] text-ink-light font-normal">sin remisión aún</span>
              </td>
              <td class="py-1.5 text-right" :class="varClass(r.real.overhead - r.estimado.overhead_total, true)">{{ signedC(r.real.overhead - r.estimado.overhead_total) }}</td>
            </tr>
            <tr class="font-semibold">
              <td class="py-2">Total</td>
              <td class="py-2 text-right">{{ fmtC(r.estimado.costo_total) }}</td>
              <td class="py-2 text-right">{{ fmtC(r.real.costo_total) }}</td>
              <td class="py-2 text-right" :class="varClass(r.variacion.costo_monto, true)">{{ signedC(r.variacion.costo_monto) }} ({{ signed(r.variacion.costo_pct, 1) }}%)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Detalle materiales -->
      <div class="bg-white rounded-xl border border-surface-border p-4">
        <p class="section-title mb-2">Materia prima — detalle</p>
        <p class="text-[11px] text-ink-muted mb-2">Proveedor/precio estimado (capturado en el costeo) vs. lo realmente comprado (órdenes de compra validadas).</p>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1.5">Estimado</p>
            <table class="w-full text-[12.5px]">
              <thead><tr class="text-left text-ink-light border-b border-surface-border"><th class="py-1">Material</th><th class="py-1">Proveedor</th><th class="py-1 text-right">Precio</th></tr></thead>
              <tbody>
                <tr v-for="(m, i) in r.estimado.materiales" :key="i" class="border-b border-surface-border/60">
                  <td class="py-1 pr-1 truncate max-w-[140px]">{{ m.item }}</td>
                  <td class="py-1 pr-1 truncate max-w-[100px] text-ink-muted">{{ m.proveedor || '—' }}</td>
                  <td class="py-1 text-right">{{ fmtC(m.precio_unitario) }}</td>
                </tr>
                <tr v-if="!r.estimado.materiales.length"><td colspan="3" class="py-2 text-ink-light">Sin materiales.</td></tr>
              </tbody>
            </table>
          </div>
          <div>
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1.5">Real (comprado)</p>
            <table class="w-full text-[12.5px]">
              <thead><tr class="text-left text-ink-light border-b border-surface-border"><th class="py-1">Material</th><th class="py-1">Proveedor</th><th class="py-1 text-right">Precio</th><th class="py-1 text-right">Importe</th></tr></thead>
              <tbody>
                <tr v-for="(m, i) in r.real.materiales" :key="i" class="border-b border-surface-border/60">
                  <td class="py-1 pr-1 truncate max-w-[120px]">{{ m.item_name || m.item_code }}</td>
                  <td class="py-1 pr-1 truncate max-w-[90px] text-ink-muted">{{ m.proveedor || '—' }}</td>
                  <td class="py-1 text-right">{{ fmtC(m.rate) }}</td>
                  <td class="py-1 text-right font-medium">{{ fmtC(m.amount) }}</td>
                </tr>
                <tr v-if="!r.real.materiales.length"><td colspan="4" class="py-2 text-ink-light">Sin compras validadas.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Detalle servicios -->
      <div class="bg-white rounded-xl border border-surface-border p-4">
        <p class="section-title mb-2">Servicios de subcontratación — detalle</p>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1.5">Estimado</p>
            <table class="w-full text-[12.5px]">
              <thead><tr class="text-left text-ink-light border-b border-surface-border"><th class="py-1">Etapa</th><th class="py-1">Proveedor</th><th class="py-1 text-right">Precio</th></tr></thead>
              <tbody>
                <tr v-for="(s, i) in r.estimado.servicios" :key="i" class="border-b border-surface-border/60">
                  <td class="py-1 pr-1 truncate max-w-[140px]">{{ s.servicio }}</td>
                  <td class="py-1 pr-1 truncate max-w-[100px] text-ink-muted">{{ s.proveedor || '—' }}</td>
                  <td class="py-1 text-right">{{ fmtC(s.precio) }}</td>
                </tr>
                <tr v-if="!r.estimado.servicios.length"><td colspan="3" class="py-2 text-ink-light">Sin etapas.</td></tr>
              </tbody>
            </table>
          </div>
          <div>
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1.5">Real (subcontratado)</p>
            <table class="w-full text-[12.5px]">
              <thead><tr class="text-left text-ink-light border-b border-surface-border"><th class="py-1">Servicio</th><th class="py-1">Proveedor</th><th class="py-1 text-right">Importe</th></tr></thead>
              <tbody>
                <tr v-for="(s, i) in r.real.servicios" :key="i" class="border-b border-surface-border/60">
                  <td class="py-1 pr-1 truncate max-w-[120px]">{{ s.item_name || s.item_code }}</td>
                  <td class="py-1 pr-1 truncate max-w-[90px] text-ink-muted">{{ s.proveedor || '—' }}</td>
                  <td class="py-1 text-right font-medium">{{ fmtC(s.amount) }}</td>
                </tr>
                <tr v-if="!r.real.servicios.length"><td colspan="3" class="py-2 text-ink-light">Sin órdenes validadas.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="bg-white rounded-xl border border-surface-border p-10 text-center text-ink-muted text-sm">No se pudo cargar el reporte.</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  r: { type: Object, default: null },
  loading: { type: Boolean, default: false },
});

function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function pct(v) { return `${(v || 0).toFixed(1)}%`; }
function signed(v, dec = 0) { const n = v || 0; return `${n >= 0 ? "+" : ""}${n.toFixed(dec)}`; }
function signedC(v) { const n = v || 0; return `${n >= 0 ? "+" : ""}${fmtC(n)}`; }
// Para métricas de rentabilidad, más alto = mejor (verde). Para costos, más alto = peor
// (rojo) -- por eso `varClass` recibe `invert` para los renglones de costo.
function varClass(v, invert = false) {
  const positivo = invert ? (v || 0) <= 0 : (v || 0) >= 0;
  return positivo ? "text-green-700" : "text-red-600";
}

// Ancho de barra relativo al valor más grande del grupo (est. o real) -- así ambas
// barras del mismo bloque son comparables a simple vista, no solo por el número.
function barPct(v, max) { return max > 0 ? Math.min(100, Math.max(0, ((v || 0) / max) * 100)) : 0; }

const categorias = computed(() => {
  if (!props.r) return [];
  const { estimado: e, real } = props.r;
  const fleteRealTotal = (real.flete_materiales || 0) + (real.flete_taller_ida || 0) + (real.flete_taller_regreso || 0) + (real.flete_cliente || 0);
  return [
    { label: "Materia prima", est: e.materiales_total, real: real.material_directo },
    { label: "Servicios de subcontratación", est: e.servicios_total, real: real.servicio_directo },
    { label: "Fletes (materiales + taller + cliente)", est: e.shipping_total, real: fleteRealTotal },
    { label: "Overhead", est: e.overhead_total, real: real.overhead },
  ];
});
const maxCosto = computed(() => props.r ? Math.max(props.r.estimado.costo_total, props.r.real.costo_total) : 0);
const maxCat = computed(() => categorias.value.reduce((m, c) => Math.max(m, c.est, c.real), 0));

const composicionReal = computed(() => {
  if (!props.r) return [];
  const { real } = props.r;
  const fleteRealTotal = (real.flete_materiales || 0) + (real.flete_taller_ida || 0) + (real.flete_taller_regreso || 0) + (real.flete_cliente || 0);
  const segs = [
    { label: "Materia prima", value: real.material_directo, color: "bg-blue-400" },
    { label: "Servicios", value: real.servicio_directo, color: "bg-purple-400" },
    { label: "Fletes", value: fleteRealTotal, color: "bg-orange-400" },
    { label: "Overhead", value: real.overhead, color: "bg-gray-400" },
  ];
  const total = segs.reduce((s, x) => s + (x.value || 0), 0);
  return segs.filter((s) => s.value > 0).map((s) => ({ ...s, pct: total > 0 ? (s.value / total) * 100 : 0 }));
});
const pendientesTexto = computed(() => {
  if (!props.r) return "";
  const p = props.r.pendientes;
  const partes = [];
  if (p.ocs_materia_prima_borrador) partes.push(`${p.ocs_materia_prima_borrador} OC de materia prima`);
  if (p.ocs_subcontratacion_borrador) partes.push(`${p.ocs_subcontratacion_borrador} OC de subcontratación`);
  if (p.sco_borrador) partes.push(`${p.sco_borrador} orden(es) de subcontratación`);
  if (p.transferencias_borrador) partes.push(`${p.transferencias_borrador} transferencia(s)`);
  if (p.recibos_borrador) partes.push(`${p.recibos_borrador} recibo(s)`);
  if (p.remisiones_borrador) partes.push(`${p.remisiones_borrador} remisión(es)`);
  if (p.factura_venta_borrador) partes.push("la factura de venta");
  return partes.join(", ") || "sin detalle";
});
</script>
