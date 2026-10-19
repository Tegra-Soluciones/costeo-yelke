<!--
  Inicio: el tablero del flujo costeo → venta → producción → facturación, con el
  sistema de diseño de Producción (p-*). Los números salen de api/tablero.get_tablero:
  solo lo VALIDADO, por periodo y contra el periodo anterior; las reglas de cada
  indicador están en el docstring de ese módulo y en "Cómo se calcula" al pie.

  Guía de visualización: un número principal (Vendido), fila de indicadores, una
  serie en el tiempo (columnas, 2 series con leyenda y tabla), y barras de una serie
  para las listas. Paleta validada con scripts/validate_palette.js.
-->
<template>
  <div class="flex flex-col min-h-0 bg-surface">
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-[1180px] mx-auto px-5 lg:px-8 py-6 space-y-5">

        <!-- Encabezado + filtro de periodo (una sola fila, arriba de todo) -->
        <div class="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p class="p-eyebrow">Inicio · {{ companyState.selected || "Todas las compañías" }}</p>
            <h1 class="p-h1 mt-1">{{ saludo }}{{ t?.usuario ? `, ${t.usuario.split(" ")[0]}` : "" }}</h1>
            <p class="p-lede mt-0.5">Lo validado {{ textoPeriodo }}. Montos netos, sin IVA.</p>
          </div>
          <div class="flex items-center gap-2">
            <div class="p-seg">
              <button v-for="(etq, k) in PERIODOS" :key="k" type="button" :class="periodo === k ? 'on' : ''" @click="periodo = k">{{ etq }}</button>
            </div>
            <button type="button" class="p-btn-ghost h-8" :disabled="cargando" title="Actualizar" @click="cargar">↻</button>
          </div>
        </div>

        <!-- Lo que le toca al usuario -->
        <RegresadosAMi />
        <RouterLink
          v-if="cuentaBandeja && (permisos.puede_aprobar || permisos.puede_revisar)" to="/direccion"
          class="p-panel px-4 py-3 flex items-center gap-3 hover:bg-zinc-50"
        >
          <span class="p-dot p-dot-now"></span>
          <span class="text-[13px] flex-1"><b class="font-semibold">{{ cuentaBandeja }}</b> {{ cuentaBandeja === 1 ? "documento espera" : "documentos esperan" }} tu {{ permisos.puede_aprobar ? "aprobación" : "revisión" }}</span>
          <span class="text-[12.5px] text-brand-600 font-medium">Abrir ›</span>
        </RouterLink>

        <p v-if="error" class="text-[13px] text-red-700">{{ error }}</p>

        <div v-if="t" class="space-y-5 transition-opacity" :class="cargando ? 'opacity-50' : ''">
          <!-- Número principal + indicadores -->
          <div class="grid gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border lg:grid-cols-[1.35fr_1fr_1fr]">
            <div class="bg-white p-5 lg:row-span-2 flex flex-col">
              <p class="p-meta">Vendido</p>
              <p class="text-[44px] lg:text-[52px] font-semibold tracking-tight leading-none mt-1">{{ dineroCorto(v.vendido, mon) }}</p>
              <Delta class="mt-2" :valor="t.previo?.vendido" :periodo="previoTexto" />
              <p class="p-meta mt-auto pt-4">{{ numero(v.ordenes) }} {{ v.ordenes === 1 ? "orden de venta" : "órdenes de venta" }} · {{ numero(v.prendas) }} prendas</p>
            </div>
            <Tile etiqueta="Facturado" :valor="dineroCorto(v.facturado, mon)" :delta="t.previo?.facturado" :periodo="previoTexto"
                  :nota="v.vendido ? `${pct(v.facturado, v.vendido)} % de lo vendido` : ''" :barra="pct(v.facturado, v.vendido)" />
            <Tile etiqueta="Margen estimado" :valor="v.margen == null ? '—' : `${v.margen.toFixed(1)} %`" :delta="t.previo?.margen_pts" puntos
                  :periodo="previoTexto" :nota="v.venta_costeada ? `utilidad ${dineroCorto(v.utilidad, mon)} de lo vendido` : 'sin ventas costeadas'" />
            <Tile etiqueta="Cotizaciones ganadas" :valor="v.conversion == null ? '—' : `${Math.round(v.conversion)} %`"
                  :nota="v.cotizado ? `${dineroCorto(v.ganado, mon)} de ${dineroCorto(v.cotizado, mon)} cotizado` : 'sin cotizaciones'" :barra="v.conversion" />
            <Tile etiqueta="Compras" :valor="dineroCorto(c.material + c.maquila, mon)" :delta="t.previo?.compras" neutro :periodo="previoTexto"
                  :nota="`material ${dineroCorto(c.material, mon)} · maquila ${dineroCorto(c.maquila, mon)}`" />
          </div>

          <!-- Serie en el tiempo -->
          <section class="p-panel p-5">
            <div class="mb-1">
              <p class="text-[14px] font-semibold">Vendido y facturado por mes</p>
              <p class="p-meta">{{ periodo === "anio" ? "Este año" : periodo === "mes" || periodo === "trimestre" ? "Últimos 6 meses" : "Últimos 12 meses" }} · órdenes de venta y facturas validadas</p>
            </div>
            <ColumnasMes :datos="t.serie" :series="SERIES" :moneda="mon" titulo="Vendido y facturado por mes" class="mt-3" />
          </section>

          <div class="grid gap-5 lg:grid-cols-2">
            <!-- Embudo comercial -->
            <section class="p-panel p-5">
              <p class="text-[14px] font-semibold">Del cotizado al cobrado</p>
              <p class="p-meta mb-4">{{ textoPeriodo }}</p>
              <BarrasLista :filas="embudo" :formato="(x) => dinero(x, mon)" />
              <p v-if="!t.cobros_registrados" class="text-[11.5px] text-ink-light mt-3 leading-snug">
                No hay cobros registrados en el sistema: las facturas oficiales y sus cobros se llevan en el sistema de facturación, así que “Cobrado” no aplica aquí.
              </p>
            </section>

            <!-- Producción y costeos -->
            <section class="p-panel p-5 space-y-5">
              <div>
                <p class="text-[14px] font-semibold">Maquila en curso</p>
                <p class="p-meta">Órdenes a taller validadas de los proyectos que siguen abiertos</p>
                <div v-if="t.produccion.total" class="mt-3">
                  <div class="flex items-baseline justify-between">
                    <p class="text-[26px] font-semibold tracking-tight">{{ t.produccion.avance == null ? "—" : `${Math.round(t.produccion.avance)} %` }}<span class="text-[13px] font-normal text-ink-muted"> recibido</span></p>
                    <p class="p-meta">{{ t.produccion.completas }} de {{ t.produccion.total }} órdenes completas</p>
                  </div>
                  <div class="h-2 rounded-full bg-brand-50 mt-2"><div class="h-2 rounded-full bg-brand-600" :style="{ width: `${Math.min(100, t.produccion.avance || 0)}%` }"></div></div>
                  <p class="text-[11.5px] text-ink-light mt-1.5">Avance ponderado por importe: una orden cuenta como completa solo al 100 % recibido.</p>
                </div>
                <p v-else class="p-meta mt-3">No hay órdenes a taller abiertas.</p>
              </div>
              <div>
                <p class="text-[14px] font-semibold">Proyectos por etapa</p>
                <p class="p-meta mb-3">Hoy · {{ t.costeos.total }} costeos (sin plantillas){{ t.costeos.cancelados ? ` · ${t.costeos.cancelados} cancelados aparte` : "" }}</p>
                <BarrasLista :filas="etapas" :formato="(x) => numero(x)" vacio="Sin costeos." />
              </div>
            </section>
          </div>

          <div class="grid gap-5 lg:grid-cols-3">
            <section class="p-panel p-5">
              <p class="text-[14px] font-semibold">Clientes</p>
              <p class="p-meta mb-4">Vendido {{ textoPeriodo }}</p>
              <BarrasLista :filas="lista(t.clientes, 'OV')" :formato="(x) => dineroCorto(x, mon)" vacio="Sin ventas en el periodo." />
            </section>
            <section class="p-panel p-5">
              <p class="text-[14px] font-semibold">Talleres</p>
              <p class="p-meta mb-4">Maquila encargada {{ textoPeriodo }}</p>
              <BarrasLista :filas="lista(t.talleres, 'OC')" :formato="(x) => dineroCorto(x, mon)" vacio="Sin órdenes a taller en el periodo." />
            </section>
            <section class="p-panel p-5">
              <p class="text-[14px] font-semibold">Proveedores de material</p>
              <p class="p-meta mb-4">Compras {{ textoPeriodo }}</p>
              <BarrasLista :filas="lista(t.proveedores, 'OC')" :formato="(x) => dineroCorto(x, mon)" vacio="Sin compras de material en el periodo." />
            </section>
          </div>

          <!-- Transparencia: lo que NO se sumó y cómo se calcula -->
          <section class="p-panel px-5 py-4">
            <p class="text-[13px] font-semibold">En borrador (no se suma arriba)</p>
            <div class="flex flex-wrap gap-x-6 gap-y-1 mt-1.5 text-[12.5px] text-ink-muted">
              <span v-for="b in borradores" :key="b.l"><b class="text-ink font-semibold tabular-nums">{{ b.n }}</b> {{ b.l }} · {{ dineroCorto(b.monto, mon) }}</span>
              <span v-if="!borradores.length">Nada en borrador.</span>
            </div>
            <details class="mt-3 group">
              <summary class="list-none cursor-pointer text-[12.5px] text-brand-600 font-medium">Cómo se calcula cada número ›</summary>
              <ul class="mt-2 space-y-1.5 text-[12px] text-ink-muted leading-relaxed list-disc pl-4">
                <li><b>Solo documentos validados.</b> Un borrador todavía no es venta ni compra.</li>
                <li><b>Por periodo</b>, según la fecha del documento, y contra el periodo anterior con los mismos días transcurridos.</li>
                <li><b>Margen estimado</b>: (venta − costo) ÷ venta de los costeos que se vendieron, ponderado por lo que se vendió de cada uno.</li>
                <li><b>Cotizaciones ganadas</b>: valor de las cotizaciones que se convirtieron en orden de venta ÷ valor cotizado.</li>
                <li><b>Maquila en curso</b>: una orden a taller cuenta como completa solo al 100 % recibido; el avance pondera por importe.</li>
                <li><b>Proyectos por etapa</b>: estado actual de cada costeo, sin plantillas ni versiones reemplazadas.</li>
              </ul>
            </details>
          </section>
        </div>
        <div v-else-if="cargando" class="py-20 text-center p-meta">Cargando…</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import RegresadosAMi from "@/components/aprobacion/RegresadosAMi.vue";
import BarrasLista from "@/components/tablero/BarrasLista.vue";
import ColumnasMes from "@/components/tablero/ColumnasMes.vue";
import { cuentaBandeja, usePermisosAprobacion } from "@/composables/useAprobacion.js";
import { useCompany } from "@/composables/useCompany.js";
import { call } from "@/utils/frappe.js";
import { dinero, dineroCorto, fecha, numero } from "@/utils/formato.js";

const PERIODOS = { mes: "Mes", trimestre: "Trimestre", anio: "Año", "12m": "12 meses", todo: "Todo" };
const CLAVE_PERIODO = "costeo_yelke.periodo_inicio";
// Paleta validada (validate_palette.js): marca un paso más oscuro (≥ 3:1) y azul.
const SERIES = [
  { clave: "vendido", etiqueta: "Vendido", color: "#f05208" },
  { clave: "facturado", etiqueta: "Facturado", color: "#2a78d6" },
];

const { state: companyState } = useCompany();
const permisos = usePermisosAprobacion();

const t = ref(null);
const cargando = ref(false);
const error = ref("");
const periodo = ref(leerPeriodo());

function leerPeriodo() {
  try { return PERIODOS[localStorage.getItem(CLAVE_PERIODO)] ? localStorage.getItem(CLAVE_PERIODO) : "anio"; } catch { return "anio"; }
}

const v = computed(() => t.value?.ventas || {});
const c = computed(() => t.value?.compras || { material: 0, maquila: 0 });
const mon = computed(() => t.value?.moneda || "MXN");
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const saludo = computed(() => { const hr = new Date().getHours(); return hr < 12 ? "Buenos días" : hr < 19 ? "Buenas tardes" : "Buenas noches"; });
const textoPeriodo = computed(() => {
  if (!t.value) return "";
  if (!t.value.desde) return "de todo el historial";
  return `del ${fecha(t.value.desde)} al ${fecha(t.value.hasta)}`;
});
const previoTexto = computed(() => (t.value?.previo ? `vs ${fecha(t.value.previo.desde)} – ${fecha(t.value.previo.hasta)}` : ""));

const embudo = computed(() => {
  const filas = [
    { nombre: "Cotizado", valor: v.value.cotizado || 0 },
    { nombre: "Cotizaciones ganadas", valor: v.value.ganado || 0, nota: v.value.cotizado ? `${pct(v.value.ganado, v.value.cotizado)} %` : "" },
    { nombre: "Vendido (órdenes de venta)", valor: v.value.vendido || 0,
      nota: v.value.vendido_directo ? `${dineroCorto(v.value.vendido_directo, mon.value)} sin cotización` : "" },
    { nombre: "Facturado", valor: v.value.facturado || 0, nota: v.value.vendido ? `${pct(v.value.facturado, v.value.vendido)} % de lo vendido` : "" },
  ];
  if (t.value?.cobros_registrados) filas.push({ nombre: "Cobrado", valor: v.value.cobrado || 0, nota: v.value.facturado ? `${pct(v.value.cobrado, v.value.facturado)} %` : "" });
  return filas;
});
const NOMBRE_ETAPA = { Borrador: "Costeo", Cotizado: "Cotizado", "Orden de Venta": "Orden de venta", "En Producción": "En producción", Entregado: "Entregado", Completado: "Completado" };
const etapas = computed(() => (t.value?.costeos.etapas || []).map((e) => ({ nombre: NOMBRE_ETAPA[e.etapa] || e.etapa, valor: e.n })));
const lista = (bloque, sufijo) => (bloque?.filas || []).map((f) => ({
  nombre: f.nombre, valor: f.monto, otros: !f.clave,
  nota: `${f.n} ${sufijo}${bloque.total ? ` · ${pct(f.monto, bloque.total)} %` : ""}`,
}));
const borradores = computed(() => {
  const b = t.value?.borradores || {};
  return [["Quotation", "cotizaciones"], ["Sales Order", "órdenes de venta"], ["Purchase Order", "órdenes de compra"], ["Sales Invoice", "facturas de venta"]]
    .filter(([dt]) => b[dt]?.n).map(([dt, l]) => ({ l, n: b[dt].n, monto: b[dt].monto }));
});

// ── Piezas del tablero ────────────────────────────────────────────────────────
/** Cambio contra el periodo anterior. El color dice si es bueno (verde) o malo
 *  (rojo); `neutro` (compras) no lo juzga. Siempre con flecha y texto. */
const Delta = defineComponent({
  props: { valor: Number, periodo: String, puntos: Boolean, neutro: Boolean },
  setup(p) {
    return () => {
      if (p.valor == null) return h("p", { class: "text-[11.5px] text-ink-light" }, p.periodo ? "sin datos del periodo anterior" : "");
      const sube = p.valor >= 0;
      const tono = p.neutro || Math.abs(p.valor) < 0.05 ? "text-ink-muted" : sube ? "text-emerald-700" : "text-red-700";
      const txt = `${sube ? "▲" : "▼"} ${Math.abs(p.valor).toFixed(p.puntos ? 1 : 0)}${p.puntos ? " pts" : " %"}`;
      return h("p", { class: "text-[11.5px]" }, [h("span", { class: `font-semibold ${tono}` }, txt), h("span", { class: "text-ink-light" }, ` ${p.periodo}`)]);
    };
  },
});
const Tile = defineComponent({
  props: { etiqueta: String, valor: String, delta: Number, periodo: String, nota: String, barra: Number, puntos: Boolean, neutro: Boolean },
  setup(p) {
    return () => h("div", { class: "bg-white p-4 flex flex-col" }, [
      h("p", { class: "p-meta" }, p.etiqueta),
      h("p", { class: "text-[24px] font-semibold tracking-tight leading-tight mt-0.5" }, p.valor),
      p.delta !== undefined ? h(Delta, { valor: p.delta, periodo: p.periodo, puntos: p.puntos, neutro: p.neutro, class: "mt-0.5" }) : null,
      p.barra != null ? h("div", { class: "h-1 rounded bg-brand-50 mt-2" }, [h("div", { class: "h-1 rounded bg-brand-600", style: { width: `${Math.min(100, p.barra || 0)}%` } })]) : null,
      p.nota ? h("p", { class: "text-[11.5px] text-ink-muted mt-auto pt-1.5" }, p.nota) : null,
    ]);
  },
});

async function cargar() {
  cargando.value = true;
  error.value = "";
  try {
    t.value = await call("costeo_yelke.api.tablero.get_tablero", { company: companyState.selected || undefined, periodo: periodo.value });
  } catch (e) {
    error.value = e.message || "No se pudo cargar el tablero.";
  } finally {
    cargando.value = false;
  }
}

watch(periodo, (p) => { try { localStorage.setItem(CLAVE_PERIODO, p); } catch { /* opcional */ } cargar(); });
watch(() => companyState.selected, cargar);
onMounted(cargar);
</script>
