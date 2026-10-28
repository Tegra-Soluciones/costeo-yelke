<!--
  Reporte final del costeo: lo planeado (paso Costear) contra lo real (documentos
  validados), sin IVA. Mismo lenguaje visual que Producción: paneles blancos, tablas
  limpias, color solo en las diferencias (verde = a favor, rojo = en contra).

  Lectura de arriba abajo: cómo terminó (indicadores) -> por qué (puente de la
  utilidad estimada a la real) -> el detalle (costos, materia prima, maquila, fletes).
-->
<template>
  <div class="max-w-5xl mx-auto space-y-5">
    <div v-if="loading" class="p-panel p-10 text-center p-meta">Calculando reporte…</div>

    <template v-else-if="r">
      <!-- Encabezado -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p class="p-eyebrow">Reporte final</p>
          <p class="p-h1 mt-0.5">{{ r.cliente }}</p>
          <p class="p-meta mt-0.5">Plan del costeo contra lo real de los documentos validados · montos sin IVA</p>
        </div>
        <span :class="r.completo ? 'p-pill-ok' : 'p-pill-wait'">{{ r.completo ? 'Proceso cerrado' : 'Con pendientes' }}</span>
      </div>

      <p v-if="!r.completo" class="text-[12.5px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
        Los números reales todavía pueden moverse: {{ pendientesTexto }}.
        <span v-if="baseTexto" class="block mt-0.5">{{ baseTexto }}</span>
      </p>

      <!-- Indicadores -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
        <div v-for="k in indicadores" :key="k.titulo" class="bg-white p-4">
          <p class="p-meta">{{ k.titulo }}</p>
          <p class="text-[22px] font-semibold p-num mt-1 text-ink">{{ k.valor }}</p>
          <p class="text-[12px] p-num mt-0.5">
            <span class="text-ink-light">{{ k.plan }}</span>
            <span v-if="k.dif" class="ml-1.5" :class="k.difClase">{{ k.dif }}</span>
          </p>
          <p v-if="k.extra" class="text-[12px] p-num text-ink-muted mt-0.5">{{ k.extra }}</p>
        </div>
      </div>

      <!-- Operación: tiempos, material y dinero pendiente -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
        <div v-for="k in operacion" :key="k.titulo" class="bg-white p-4">
          <p class="p-meta">{{ k.titulo }}</p>
          <p class="text-[18px] font-semibold p-num mt-1 text-ink">{{ k.valor }}</p>
          <p class="text-[12px] p-num mt-0.5" :class="k.clase || 'text-ink-muted'">{{ k.detalle }}</p>
        </div>
      </div>

      <!-- Comparativo visual (las gráficas que pidió Yelke) -->
      <section class="p-panel p-4 space-y-5">
        <div>
          <p class="text-[14px] font-semibold text-ink">Comparativo visual</p>
          <p class="p-meta">Plan del costeo en gris, real en naranja.</p>
        </div>
        <div>
          <p class="text-[12px] font-medium text-ink-muted mb-2">Costo total</p>
          <div class="space-y-1.5">
            <div v-for="b in [{ t: 'Plan', v: r.estimado.costo_total, plan: true }, { t: 'Real', v: r.real.costo_total }]" :key="b.t" class="flex items-center gap-3">
              <span class="text-[11.5px] text-ink-light w-10 flex-shrink-0">{{ b.t }}</span>
              <div class="flex-1 h-5 bg-zinc-50 rounded overflow-hidden">
                <div class="h-full rounded" :class="b.plan ? 'bg-zinc-300' : 'bg-brand-500'" :style="{ width: ancho(b.v, maxCosto) + '%' }"></div>
              </div>
              <span class="text-[12.5px] p-num w-32 text-right flex-shrink-0" :class="b.plan ? 'text-ink-muted' : 'font-medium'">{{ fmtC(b.v) }}</span>
            </div>
          </div>
        </div>
        <div>
          <p class="text-[12px] font-medium text-ink-muted mb-2">Por concepto</p>
          <div class="grid sm:grid-cols-2 gap-x-8 gap-y-4">
            <div v-for="c in costos" :key="c.label">
              <div class="flex items-baseline justify-between mb-1">
                <span class="text-[12.5px] text-ink">{{ c.label }}</span>
                <span class="text-[11.5px] p-num" :class="clase(c.plan - c.real)">{{ signedC(c.real - c.plan) }}</span>
              </div>
              <div class="space-y-1">
                <div class="h-2.5 bg-zinc-50 rounded overflow-hidden"><div class="h-full bg-zinc-300 rounded" :style="{ width: ancho(c.plan, maxConcepto) + '%' }" :title="`Plan ${fmtC(c.plan)}`"></div></div>
                <div class="h-2.5 bg-zinc-50 rounded overflow-hidden"><div class="h-full bg-brand-500 rounded" :style="{ width: ancho(c.real, maxConcepto) + '%' }" :title="`Real ${fmtC(c.real)}`"></div></div>
              </div>
              <div class="flex justify-between text-[11px] p-num text-ink-light mt-0.5"><span>plan {{ fmtC(c.plan) }}</span><span>real {{ fmtC(c.real) }}</span></div>
            </div>
          </div>
        </div>
        <div>
          <p class="text-[12px] font-medium text-ink-muted mb-2">¿En qué se fue el costo real?</p>
          <div class="flex h-4 rounded overflow-hidden gap-0.5">
            <div v-for="seg in composicion" :key="seg.label" :class="seg.color" :style="{ width: seg.pct + '%' }" :title="`${seg.label}: ${fmtC(seg.v)} (${seg.pct.toFixed(1)}%)`"></div>
          </div>
          <div class="flex flex-wrap gap-x-5 gap-y-1 mt-2">
            <span v-for="seg in composicion" :key="'l' + seg.label" class="flex items-center gap-1.5 text-[12px] text-ink-muted">
              <span class="w-2.5 h-2.5 rounded-sm" :class="seg.color"></span>{{ seg.label }} <span class="p-num text-ink">{{ seg.pct.toFixed(1) }}%</span>
            </span>
          </div>
        </div>
        <div>
          <p class="text-[12px] font-medium text-ink-muted mb-2">De cada peso de venta</p>
          <div class="flex h-4 rounded overflow-hidden gap-0.5">
            <div v-for="seg in pesoVenta" :key="seg.label" :class="seg.color" :style="{ width: seg.pct + '%' }" :title="`${seg.label}: ${fmtC(seg.v)}`"></div>
          </div>
          <div class="flex flex-wrap gap-x-5 gap-y-1 mt-2">
            <span v-for="seg in pesoVenta" :key="'p' + seg.label" class="flex items-center gap-1.5 text-[12px] text-ink-muted">
              <span class="w-2.5 h-2.5 rounded-sm" :class="seg.color"></span>{{ seg.label }} <span class="p-num text-ink">{{ (seg.pct / 100).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' }) }}</span>
            </span>
          </div>
        </div>
      </section>

      <!-- Puente: de la utilidad estimada a la real -->
      <section v-if="r.real.sales_invoice" class="p-panel">
        <div class="px-4 pt-4 pb-2">
          <p class="text-[14px] font-semibold text-ink">De la utilidad estimada a la real</p>
          <p class="p-meta">Qué movió el resultado contra el costeo. A favor suma utilidad; en contra la resta.</p>
        </div>
        <table class="p-tbl">
          <tbody>
            <tr>
              <td class="text-ink-muted">Utilidad estimada</td>
              <td class="w-1/3"></td>
              <td class="text-right p-num font-medium w-40">{{ fmtC(r.estimado.rentabilidad_monto) }}</td>
            </tr>
            <tr v-for="p in puente" :key="p.label">
              <td class="pl-8">{{ p.label }}</td>
              <td class="w-1/3">
                <div class="h-1.5 rounded-full bg-zinc-100 overflow-hidden flex" :class="p.v >= 0 ? 'justify-start' : 'justify-end'">
                  <div class="h-full rounded-full" :class="p.v >= 0 ? 'bg-emerald-500/70' : 'bg-red-500/70'" :style="{ width: barra(p.v) + '%' }"></div>
                </div>
              </td>
              <td class="text-right p-num w-40" :class="clase(p.v)">{{ signedC(p.v) }}</td>
            </tr>
            <tr class="font-semibold">
              <td>Utilidad real</td>
              <td class="w-1/3"></td>
              <td class="text-right p-num w-40">{{ fmtC(r.real.rentabilidad_monto) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Costos -->
      <section class="p-panel">
        <div class="px-4 pt-4 pb-2">
          <p class="text-[14px] font-semibold text-ink">Costos</p>
          <p class="p-meta">{{ fmtN(r.real.qty_total || r.estimado.qty_total) }} prendas · el costo real ya descuenta el material que sobró y sigue en inventario</p>
        </div>
        <table class="p-tbl">
          <thead>
            <tr><th>Concepto</th><th class="text-right">Plan</th><th class="text-right">Real</th><th class="text-right">Diferencia</th><th class="text-right">Por prenda</th><th class="text-right">% del costo</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in costos" :key="c.label">
              <td>{{ c.label }}<span v-if="c.nota" class="block text-[11.5px] text-ink-light">{{ c.nota }}</span></td>
              <td class="text-right p-num text-ink-muted">{{ fmtC(c.plan) }}</td>
              <td class="text-right p-num">{{ fmtC(c.real) }}</td>
              <td class="text-right p-num" :class="clase(c.plan - c.real)">{{ signedC(c.real - c.plan) }}</td>
              <td class="text-right p-num text-ink-muted">{{ fmtC(porPrenda(c.real)) }}</td>
              <td class="text-right p-num text-ink-muted">{{ pctDe(c.real, r.real.costo_total) }}</td>
            </tr>
            <tr class="font-semibold">
              <td>Total</td>
              <td class="text-right p-num">{{ fmtC(r.estimado.costo_total) }}</td>
              <td class="text-right p-num">{{ fmtC(r.real.costo_total) }}</td>
              <td class="text-right p-num" :class="clase(-r.variacion.costo_monto)">{{ signedC(r.variacion.costo_monto) }}</td>
              <td class="text-right p-num">{{ fmtC(porPrenda(r.real.costo_total)) }}</td>
              <td class="text-right p-num">100%</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Materia prima -->
      <section v-if="materiales.length" class="p-panel">
        <div class="px-4 pt-4 pb-2 flex items-end justify-between gap-3 flex-wrap">
          <div>
            <p class="text-[14px] font-semibold text-ink">Materia prima</p>
            <p class="p-meta">Cantidades en la unidad de inventario. La diferencia se separa en precio (pagamos distinto por unidad) y consumo (se usó más o menos de lo planeado).</p>
          </div>
          <p v-if="r.real.material_sobrante" class="p-meta">
            Sobrante en inventario <b class="text-ink p-num">{{ fmtC(r.real.material_sobrante) }}</b>
            <span v-if="r.real.material_sobrante_en_talleres"> · {{ fmtC(r.real.material_sobrante_en_talleres) }} sigue con los talleres</span>
          </p>
        </div>
        <div class="overflow-x-auto">
          <table class="p-tbl min-w-[760px] text-[12.5px] [&_td]:px-2.5 [&_th]:px-2.5 [&_td:first-child]:pl-4 [&_th:first-child]:pl-4 [&_td:last-child]:pr-4 [&_th:last-child]:pr-4">
            <thead>
              <tr>
                <th>Material</th><th class="text-right">Plan</th><th class="text-right">Consumido</th><th class="text-right">Comprado</th>
                <th class="text-right">Sobra</th><th class="text-right">Precio plan → real</th><th class="text-right whitespace-nowrap">Por precio</th><th class="text-right whitespace-nowrap">Por consumo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in materiales" :key="m.item_code">
                <td class="min-w-[10rem]">
                  {{ m.item_name }}
                  <span class="block text-[11.5px] text-ink-light">{{ m.proveedor_real || m.proveedor_plan || '—' }}<template v-if="m.proveedor_plan && m.proveedor_real && m.proveedor_plan !== m.proveedor_real"> · costeado con {{ m.proveedor_plan }}</template></span>
                </td>
                <td class="text-right p-num whitespace-nowrap text-ink-muted">{{ cant(m.plan_qty, m.uom) }}</td>
                <td class="text-right p-num whitespace-nowrap">{{ cant(m.consumido_qty, m.uom) }}</td>
                <td class="text-right p-num whitespace-nowrap text-ink-muted">{{ cant(m.comprado_qty, m.uom) }}</td>
                <td class="text-right p-num whitespace-nowrap text-ink-muted">{{ cant(m.sobrante_qty, m.uom) }}</td>
                <td class="text-right p-num whitespace-nowrap"><span class="text-ink-muted">{{ precio(m.precio_plan) }}</span> → {{ precio(m.precio_real) }}</td>
                <td class="text-right p-num whitespace-nowrap" :class="clase(-m.efecto_precio)">{{ signedC(m.efecto_precio) }}</td>
                <td class="text-right p-num whitespace-nowrap" :class="clase(-m.efecto_consumo)">{{ signedC(m.efecto_consumo) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Maquila -->
      <section v-if="servicios.length" class="p-panel">
        <div class="px-4 pt-4 pb-2">
          <p class="text-[14px] font-semibold text-ink">Maquila</p>
          <p class="p-meta">Por servicio y taller: lo costeado contra lo facturado.</p>
        </div>
        <table class="p-tbl">
          <thead><tr><th>Servicio</th><th>Taller</th><th class="text-right">Prendas</th><th class="text-right">Plan</th><th class="text-right">Real</th><th class="text-right">Diferencia</th></tr></thead>
          <tbody>
            <tr v-for="s in servicios" :key="s.servicio + s.supplier">
              <td>{{ limpio(s.servicio_nombre) }}</td>
              <td class="text-ink-muted">{{ s.proveedor || '—' }}</td>
              <td class="text-right p-num text-ink-muted">{{ fmtN(s.qty) }}</td>
              <td class="text-right p-num text-ink-muted">{{ fmtC(s.estimado) }}</td>
              <td class="text-right p-num">{{ fmtC(s.real) }}</td>
              <td class="text-right p-num" :class="clase(s.estimado - s.real)">{{ signedC(s.real - s.estimado) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Fletes -->
      <section class="p-panel">
        <div class="px-4 pt-4 pb-2">
          <p class="text-[14px] font-semibold text-ink">Fletes</p>
          <p class="p-meta">El costeo los estima en un solo monto por prenda; aquí está dónde se pagaron.</p>
        </div>
        <table class="p-tbl">
          <tbody>
            <tr v-for="f in fletes" :key="f.label">
              <td>{{ f.label }}</td>
              <td class="text-right p-num w-40">{{ fmtC(f.v) }}</td>
            </tr>
            <tr class="font-semibold">
              <td>Total <span class="font-normal text-ink-light">· plan {{ fmtC(r.estimado.shipping_total) }} · {{ pctDe(fleteReal, r.real.ingreso || r.estimado.venta_total) }} de la venta</span></td>
              <td class="text-right p-num w-40">{{ fmtC(fleteReal) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <div class="flex items-center justify-between gap-3 flex-wrap pt-1">
        <p class="p-meta">
          <template v-if="r.real.sales_invoice">Venta real de la factura {{ r.real.sales_invoice }}. </template>
          Gastos indirectos al {{ (r.estimado.overhead_pct_promedio || 0).toFixed(1) }}% del costo directo real.
        </p>
        <!-- PDF formal (formato "Reporte Final Yelke": membrete, uso interno, firmas). -->
        <a v-if="costeo" class="p-btn-secondary no-underline hover:no-underline" :href="urlPdf" download>
          <Icono nombre="descargar" class="w-4 h-4" /> Descargar PDF
        </a>
      </div>
    </template>

    <div v-else class="p-panel p-10 text-center p-meta">No se pudo cargar el reporte.</div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Icono from "@/components/Icono.vue";

const props = defineProps({
  r: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  costeo: { type: String, default: "" },
  salesOrder: { type: String, default: "" },
});
const urlPdf = computed(() => {
  const q = new URLSearchParams({ costeo: props.costeo });
  if (props.salesOrder) q.set("sales_order", props.salesOrder);
  return `/api/method/costeo_yelke.api.reporte_impresion.descargar_reporte_final?${q}`;
});

const fmtC = (v) => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0);
const fmtN = (v, dec = 0) => (Number(v) || 0).toLocaleString("es-MX", { maximumFractionDigits: dec });
// Cero se escribe $0.00, sin signo: un guion se leía como dato faltante.
const signedC = (v) => (Math.abs(v || 0) < 0.005 ? fmtC(0) : `${v > 0 ? "+" : "−"}${fmtC(Math.abs(v))}`);
const casiCero = (v) => Math.abs(v || 0) < 0.5;
// Verde si favorece (v > 0 = ahorro o más ingreso), rojo si perjudica; gris si es ~0.
const clase = (v) => (casiCero(v) ? "text-ink-muted" : v > 0 ? "text-emerald-700" : "text-red-600");
const pctDe = (v, total) => (total ? `${((v / total) * 100).toFixed(1)}%` : "—");
const limpio = (t) => String(t || "").replace(/-+$/, "");
// «MTR - Metro» -> «m»; «H87 - Pieza» -> «pzas».
const UNIDAD = { metro: "m", pieza: "pzas", kilogramo: "kg", litro: "L" };
function cant(q, uom) {
  const nombre = String(uom || "").split(" - ").pop().toLowerCase();
  return `${fmtN(q, 2)} ${UNIDAD[nombre] || nombre}`;
}
// Precio unitario: centavos de botón necesitan más decimales que un metro de tela.
const precio = (v) => (Math.abs(v || 0) < 1
  ? `$${(v || 0).toLocaleString("es-MX", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}` : fmtC(v));

const materiaReal = computed(() => props.r ? (props.r.real.material_consumido ?? props.r.real.material_directo) : 0);
const fleteReal = computed(() => {
  const x = props.r?.real || {};
  return (x.flete_materiales || 0) + (x.flete_taller_ida || 0) + (x.flete_taller_regreso || 0) + (x.flete_cliente || 0);
});
const prendas = computed(() => props.r ? (props.r.real.qty_total || props.r.estimado.qty_total || 0) : 0);
const porPrenda = (v) => (prendas.value ? v / prendas.value : 0);

const indicadores = computed(() => {
  const r = props.r;
  if (!r) return [];
  const { estimado: e, real } = r;
  const facturado = !!real.sales_invoice;
  const costoU = porPrenda(real.costo_total);
  const costoUPlan = e.qty_total ? e.costo_total / e.qty_total : 0;
  const utilU = prendas.value ? real.rentabilidad_monto / prendas.value : 0;
  const utilUPlan = e.qty_total ? e.rentabilidad_monto / e.qty_total : 0;
  // Cambios de menos de 0.1% no se marcan: son centavos de redondeo.
  const dif = (real_, plan, favorable) => {
    const d = real_ - plan;
    const pct = (d / (plan || 1)) * 100;
    if (Math.abs(pct) < 0.05) return { dif: "", difClase: "" };
    return { dif: `${d >= 0 ? "+" : "−"}${Math.abs(pct).toFixed(1)}%`, difClase: clase(favorable ? d : -d) };
  };
  const puntos = real.rentabilidad_pct - e.rentabilidad_pct;
  return [
    { titulo: "Venta", valor: facturado ? fmtC(real.ingreso) : "Sin factura", plan: `plan ${fmtC(e.venta_total)}`,
      ...(facturado ? dif(real.ingreso, e.venta_total, true) : {}) },
    { titulo: "Costo total", valor: fmtC(real.costo_total), plan: `plan ${fmtC(e.costo_total)}`, ...dif(real.costo_total, e.costo_total, false) },
    { titulo: "Margen", valor: facturado ? `${real.rentabilidad_pct.toFixed(1)}%` : "—", plan: `plan ${e.rentabilidad_pct.toFixed(1)}%`,
      ...(facturado && Math.abs(puntos) >= 0.05 ? { dif: `${puntos >= 0 ? "+" : "−"}${Math.abs(puntos).toFixed(1)} pts`, difClase: clase(puntos) } : {}),
      extra: facturado ? `${fmtC(real.rentabilidad_monto)} de utilidad` : "" },
    { titulo: "Costo por prenda", valor: fmtC(costoU), plan: `plan ${fmtC(costoUPlan)}`, ...dif(costoU, costoUPlan, false),
      extra: facturado ? `deja ${fmtC(utilU)} por prenda (plan ${fmtC(utilUPlan)})` : "" },
  ];
});

const costos = computed(() => {
  const r = props.r;
  if (!r) return [];
  const { estimado: e, real } = r;
  return [
    { label: "Materia prima", plan: e.materiales_total, real: materiaReal.value,
      nota: real.material_sobrante ? `comprado ${fmtC(real.material_directo)} − sobrante ${fmtC(real.material_sobrante)}` : "" },
    { label: "Maquila", plan: e.servicios_total, real: real.servicio_directo },
    { label: "Fletes", plan: e.shipping_total, real: fleteReal.value },
    { label: "Gastos indirectos", plan: e.overhead_total, real: real.overhead,
      nota: `${(e.overhead_pct_promedio || 0).toFixed(1)}% del costo directo` },
  ];
});

// Puente: cada concepto con su efecto en la utilidad (ingreso de más o costo de menos = a favor).
const puente = computed(() => {
  const r = props.r;
  if (!r) return [];
  const { estimado: e, real } = r;
  return [
    { label: "Venta", v: real.ingreso - e.venta_total },
    { label: "Materia prima", v: e.materiales_total - materiaReal.value },
    { label: "Maquila", v: e.servicios_total - real.servicio_directo },
    { label: "Fletes", v: e.shipping_total - fleteReal.value },
    { label: "Gastos indirectos", v: e.overhead_total - real.overhead },
  ];
});
const maxPuente = computed(() => Math.max(1, ...puente.value.map((p) => Math.abs(p.v))));
const barra = (v) => Math.max(casiCero(v) ? 0 : 2, (Math.abs(v) / maxPuente.value) * 100);

// ── Gráficas ──
const ancho = (v, max) => (max > 0 ? Math.min(100, Math.max(0, ((v || 0) / max) * 100)) : 0);
const maxCosto = computed(() => props.r ? Math.max(props.r.estimado.costo_total, props.r.real.costo_total) : 0);
const maxConcepto = computed(() => Math.max(0, ...costos.value.flatMap((c) => [c.plan, c.real])));
// Un solo tono en distintas intensidades: se distinguen sin llenar la pantalla de colores.
const TONOS = ["bg-brand-600", "bg-brand-400", "bg-brand-200", "bg-zinc-300"];
const composicion = computed(() => {
  const segs = costos.value.map((c, i) => ({ label: c.label, v: c.real || 0, color: TONOS[i] }));
  const total = segs.reduce((a, x) => a + x.v, 0);
  return segs.filter((x) => x.v > 0).map((x) => ({ ...x, pct: total ? (x.v / total) * 100 : 0 }));
});
// De cada peso vendido: cuánto se fue a cada costo y cuánto quedó de utilidad.
const pesoVenta = computed(() => {
  const r = props.r;
  const venta = r?.real?.ingreso || r?.estimado?.venta_total || 0;
  if (!venta) return [];
  const segs = costos.value.map((c, i) => ({ label: c.label, v: c.real || 0, color: TONOS[i] }));
  const util = venta - segs.reduce((a, x) => a + x.v, 0);
  return [...segs, { label: "Utilidad", v: util, color: "bg-emerald-500" }]
    .filter((x) => x.v > 0).map((x) => ({ ...x, pct: (x.v / venta) * 100 }));
});

// ── Operación ──
const fechaCorta = (f) => (f ? new Date(`${f}T00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" }) : "");
const operacion = computed(() => {
  const o = props.r?.operacion;
  if (!o) return [];
  const comprado = materiales.value.reduce((a, m) => a + (m.comprado_importe || 0), 0);
  const usado = materiales.value.reduce((a, m) => a + (m.consumido_qty || 0) * (m.precio_real || 0), 0);
  const entrega = o.dias_entrega == null
    ? { valor: "Sin entregar", detalle: o.fecha_compromiso ? `compromiso ${fechaCorta(o.fecha_compromiso)}` : "" }
    : { valor: `${o.dias_entrega} días`,
        detalle: o.dias_atraso == null ? `${o.remisiones} remisión(es)`
          : o.dias_atraso > 0 ? `${o.dias_atraso} días tarde del compromiso` : o.dias_atraso < 0 ? `${-o.dias_atraso} días antes del compromiso` : "justo en la fecha comprometida",
        clase: o.dias_atraso > 0 ? "text-red-600" : o.dias_atraso != null ? "text-emerald-700" : "" };
  return [
    { titulo: "Entrega al cliente", ...entrega },
    { titulo: "Aprovechamiento de material", valor: comprado ? `${((usado / comprado) * 100).toFixed(1)}%` : "—",
      detalle: props.r.real.material_sobrante ? `sobran ${fmtC(props.r.real.material_sobrante)} en inventario` : "sin sobrante" },
    { titulo: "Por cobrar al cliente", valor: fmtC(o.por_cobrar),
      detalle: o.por_cobrar > 0.005 ? (o.vence_cobro ? `vence ${fechaCorta(o.vence_cobro)}` : "") : "cobrado" },
    { titulo: "Por pagar a proveedores", valor: fmtC(o.por_pagar),
      detalle: o.por_pagar > 0.005 ? `${o.facturas_compra} factura(s) de material, maquila y fletes` : "todo pagado" },
  ];
});

const materiales = computed(() => props.r?.resumen?.materiales || []);
const servicios = computed(() => props.r?.resumen?.servicios || []);
const fletes = computed(() => {
  const x = props.r?.real || {};
  return [
    { label: "Compra de materia prima", v: x.flete_materiales },
    { label: "Envío a talleres", v: x.flete_taller_ida },
    { label: "Regreso de talleres", v: x.flete_taller_regreso },
    { label: "Entrega al cliente", v: x.flete_cliente },
  ];
});

const pendientesTexto = computed(() => {
  if (!props.r) return "";
  const p = props.r.pendientes;
  const partes = [];
  if (p.ocs_materia_prima_borrador) partes.push(`${p.ocs_materia_prima_borrador} OC de materia prima`);
  if (p.ocs_subcontratacion_borrador) partes.push(`${p.ocs_subcontratacion_borrador} orden(es) a talleres`);
  if (p.sco_borrador) partes.push(`${p.sco_borrador} encargo(s)`);
  if (p.transferencias_borrador) partes.push(`${p.transferencias_borrador} envío(s) a taller`);
  if (p.recibos_borrador) partes.push(`${p.recibos_borrador} recibo(s) de taller`);
  if (p.recibos_material_borrador) partes.push(`${p.recibos_material_borrador} recibo(s) de material`);
  if (p.facturas_compra_borrador) partes.push(`${p.facturas_compra_borrador} factura(s) de compra`);
  if (p.por_facturar > 0) partes.push(`${fmtC(p.por_facturar)} que los proveedores aún no facturan`);
  if (p.remisiones_borrador) partes.push(`${p.remisiones_borrador} remisión(es)`);
  if (p.factura_venta_borrador) partes.push("la factura de venta en borrador");
  return partes.join(", ") || "falta validar la factura de venta";
});

/** De dónde sale el importe real. Vacío cuando ya todo viene de facturas. */
const baseTexto = computed(() => {
  const b = props.r?.real?.bases || [];
  if (!b.length || (b.length === 1 && b[0] === "factura")) return "";
  const nombre = {
    factura: "lo que el proveedor ya facturó",
    recibo: "lo que el taller entregó y todavía no factura",
    orden: "lo contratado en la orden de compra",
  };
  return `El costo real sale de ${b.map((x) => nombre[x] || x).join(" y de ")}.`;
});
</script>
