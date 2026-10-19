<!--
  Inicio · vista financiera (Dirección, Supervisor, Analista de costos; el backend lo
  exige en api/tablero.get_tablero). Todo lo validado del periodo, contra el anterior.
-->
<template>
  <div class="space-y-5">
    <!-- Número principal + indicadores con su tendencia -->
    <div class="grid gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border lg:grid-cols-[1.35fr_1fr_1fr]">
      <Indicador
        grande class="lg:row-span-2" etiqueta="Vendido" :valor="dineroCorto(v.vendido, mon)" :delta="t.previo?.vendido" :periodo="previoTexto"
        :tendencia="serie('vendido')" :nota="`${numero(v.ordenes)} ${v.ordenes === 1 ? 'orden de venta' : 'órdenes de venta'} · ${numero(v.prendas)} prendas`"
      />
      <Indicador etiqueta="Facturado" :valor="dineroCorto(v.facturado, mon)" :delta="t.previo?.facturado" :periodo="previoTexto"
                 :tendencia="serie('facturado')" color="#2a78d6" :nota="v.vendido ? `${pct(v.facturado, v.vendido)} % de lo vendido` : ''" />
      <Indicador etiqueta="Margen estimado" :valor="v.margen == null ? '—' : `${v.margen.toFixed(1)} %`" :delta="t.previo?.margen_pts" puntos :periodo="previoTexto"
                 :barra="v.margen" color="#6250d6" riel="#efedfb" :nota="v.venta_costeada ? `utilidad ${dineroCorto(v.utilidad, mon)} de lo vendido` : 'sin ventas costeadas'" />
      <Indicador etiqueta="Cotizaciones ganadas" :valor="v.conversion == null ? '—' : `${Math.round(v.conversion)} %`" :barra="v.conversion"
                 :nota="v.cotizado ? `${dineroCorto(v.ganado, mon)} de ${dineroCorto(v.cotizado, mon)} cotizado` : 'sin cotizaciones'" />
      <Indicador etiqueta="Compras" :valor="dineroCorto(c.material + c.maquila, mon)" :delta="t.previo?.compras" neutro :periodo="previoTexto"
                 :tendencia="serie('compras')" color="#52525b" :nota="`material ${dineroCorto(c.material, mon)} · maquila ${dineroCorto(c.maquila, mon)}`" />
    </div>

    <!-- Ventas en el tiempo: acumulado (área) o por mes (columnas) -->
    <section class="p-panel p-5">
      <div class="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <p class="text-[14px] font-semibold">Vendido y facturado</p>
          <p class="p-meta">{{ tituloSerie }} · órdenes de venta y facturas validadas</p>
        </div>
        <div class="p-seg">
          <button type="button" :class="vista === 'acumulado' ? 'on' : ''" @click="vista = 'acumulado'">Acumulado</button>
          <button type="button" :class="vista === 'mes' ? 'on' : ''" @click="vista = 'mes'">Por mes</button>
        </div>
      </div>
      <AreaAcumulada v-if="vista === 'acumulado'" :datos="t.serie" :series="SERIES" :formato="(x) => dinero(x, mon)" :compacto="(x) => dineroCorto(x, mon)" titulo="Vendido y facturado acumulados" />
      <ColumnasMes v-else :datos="t.serie" :series="SERIES" :moneda="mon" titulo="Vendido y facturado por mes" />
    </section>

    <!-- A dónde va cada peso vendido -->
    <section v-if="t.composicion.venta" class="p-panel p-5">
      <div class="flex items-baseline justify-between gap-3 flex-wrap mb-4">
        <div>
          <p class="text-[14px] font-semibold">¿A dónde va cada peso vendido?</p>
          <p class="p-meta">Según el costeo de lo vendido {{ textoPeriodo }} ({{ dineroCorto(t.composicion.venta, mon) }})</p>
        </div>
        <p class="text-[13px]">De cada $100: <b class="font-semibold">${{ cada100("material") }}</b> material · <b class="font-semibold">${{ cada100("maquila") }}</b> maquila · <b class="font-semibold">${{ cada100("utilidad") }}</b> utilidad</p>
      </div>
      <BarraComposicion :partes="t.composicion.partes" :formato="(x) => dineroCorto(x, mon)" titulo="Composición de lo vendido" />
    </section>

    <div class="grid gap-5 lg:grid-cols-2">
      <section class="p-panel p-5">
        <p class="text-[14px] font-semibold">Del cotizado al facturado</p>
        <p class="p-meta mb-4">{{ textoPeriodo }}</p>
        <BarrasLista :filas="embudo" :formato="(x) => dinero(x, mon)" />
        <p v-if="!t.cobros_registrados" class="text-[11.5px] text-ink-light mt-3 leading-snug">
          No hay cobros registrados en el sistema: las facturas oficiales y sus cobros se llevan en el sistema de facturación.
        </p>
      </section>
      <section class="p-panel p-5 space-y-6">
        <div>
          <div class="flex items-baseline justify-between gap-3">
            <p class="text-[14px] font-semibold">Maquila en curso</p>
            <p class="p-meta">{{ t.produccion.completas }} de {{ t.produccion.total }} órdenes completas</p>
          </div>
          <p class="p-meta">Órdenes a taller de los proyectos abiertos, ponderado por importe</p>
          <template v-if="t.produccion.total">
            <p class="text-[30px] font-semibold tracking-tight mt-2">{{ t.produccion.avance == null ? "—" : `${Math.round(t.produccion.avance)} %` }}<span class="text-[13px] font-normal text-ink-muted"> recibido</span></p>
            <div class="h-2.5 rounded-full bg-brand-50 mt-1"><div class="h-2.5 rounded-full bg-brand-600" :style="{ width: `${Math.min(100, t.produccion.avance || 0)}%` }"></div></div>
          </template>
          <p v-else class="p-meta mt-3">No hay órdenes a taller abiertas.</p>
        </div>
        <div>
          <p class="text-[14px] font-semibold">Proyectos por etapa</p>
          <p class="p-meta mb-4">Hoy · {{ t.costeos.total }} costeos (sin plantillas){{ t.costeos.cancelados ? ` · ${t.costeos.cancelados} cancelados aparte` : "" }}</p>
          <Recorrido :etapas="etapas" />
        </div>
      </section>
    </div>

    <div class="grid gap-5 lg:grid-cols-3">
      <section v-for="b in LISTAS" :key="b.clave" class="p-panel p-5">
        <p class="text-[14px] font-semibold">{{ b.titulo }}</p>
        <p class="p-meta mb-4">{{ b.sub }} {{ textoPeriodo }}</p>
        <BarrasLista :filas="lista(t[b.clave], b.sufijo)" :formato="(x) => dineroCorto(x, mon)" :color="b.color" :riel="b.riel" :vacio="b.vacio" />
      </section>
    </div>

    <section class="p-panel px-5 py-4">
      <p class="text-[13px] font-semibold">En borrador (no se suma arriba)</p>
      <div class="flex flex-wrap gap-x-6 gap-y-1 mt-1.5 text-[12.5px] text-ink-muted">
        <span v-for="b in borradores" :key="b.l"><b class="text-ink font-semibold tabular-nums">{{ b.n }}</b> {{ b.l }} · {{ dineroCorto(b.monto, mon) }}</span>
        <span v-if="!borradores.length">Nada en borrador.</span>
      </div>
      <details class="mt-3">
        <summary class="list-none cursor-pointer text-[12.5px] text-brand-600 font-medium">Cómo se calcula cada número ›</summary>
        <ul class="mt-2 space-y-1.5 text-[12px] text-ink-muted leading-relaxed list-disc pl-4">
          <li><b>Solo documentos validados</b>, por la fecha del documento, contra el periodo anterior con los mismos días transcurridos.</li>
          <li><b>Margen estimado</b> y <b>a dónde va cada peso</b>: el costeo de lo vendido, ponderado por lo que se vendió de cada producto.</li>
          <li><b>Cotizaciones ganadas</b>: valor de las que se convirtieron en orden de venta ÷ valor cotizado. Lo vendido sin cotización se indica aparte.</li>
          <li><b>Maquila en curso</b>: una orden a taller cuenta como completa solo al 100 % recibido.</li>
          <li><b>Proyectos por etapa</b>: estado actual, sin plantillas ni versiones reemplazadas.</li>
        </ul>
      </details>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import AreaAcumulada from "@/components/tablero/AreaAcumulada.vue";
import BarraComposicion from "@/components/tablero/BarraComposicion.vue";
import BarrasLista from "@/components/tablero/BarrasLista.vue";
import ColumnasMes from "@/components/tablero/ColumnasMes.vue";
import Indicador from "@/components/tablero/Indicador.vue";
import Recorrido from "@/components/tablero/Recorrido.vue";
import { dinero, dineroCorto, numero } from "@/utils/formato.js";

const props = defineProps({
  t: { type: Object, required: true },
  textoPeriodo: { type: String, default: "" },
  previoTexto: { type: String, default: "" },
});

// Paleta validada (validate_palette.js): marca un paso más oscuro (≥ 3:1) y azul.
const SERIES = [
  { clave: "vendido", etiqueta: "Vendido", color: "#f05208" },
  { clave: "facturado", etiqueta: "Facturado", color: "#2a78d6" },
];
const LISTAS = [
  { clave: "clientes", titulo: "Clientes", sub: "Vendido", sufijo: "OV", color: "#f05208", riel: "#fff4ef", vacio: "Sin ventas en el periodo." },
  { clave: "talleres", titulo: "Talleres", sub: "Maquila encargada", sufijo: "OC", color: "#eb6834", riel: "#fdeee8", vacio: "Sin órdenes a taller en el periodo." },
  { clave: "proveedores", titulo: "Proveedores de material", sub: "Compras", sufijo: "OC", color: "#2a78d6", riel: "#eaf2fb", vacio: "Sin compras de material en el periodo." },
];
const NOMBRE_ETAPA = { Borrador: "Costeo", Cotizado: "Cotizado", "Orden de Venta": "Orden de venta", "En Producción": "Producción", Entregado: "Entregado", Completado: "Completado" };

const vista = ref("acumulado");
const v = computed(() => props.t.ventas);
const c = computed(() => props.t.compras);
const mon = computed(() => props.t.moneda || "MXN");
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const serie = (k) => (props.t.serie || []).map((m) => m[k]);
const tituloSerie = computed(() => ({ anio: "Este año", mes: "Últimos 6 meses", trimestre: "Últimos 6 meses" }[props.t.periodo] || "Últimos 12 meses"));
const cada100 = (k) => {
  const p = props.t.composicion.partes.find((x) => x.clave === k);
  return p && props.t.composicion.venta ? Math.round((p.monto / props.t.composicion.venta) * 100) : 0;
};
const embudo = computed(() => {
  const filas = [
    { nombre: "Cotizado", valor: v.value.cotizado || 0 },
    { nombre: "Cotizaciones ganadas", valor: v.value.ganado || 0, nota: v.value.cotizado ? `${pct(v.value.ganado, v.value.cotizado)} %` : "" },
    { nombre: "Vendido (órdenes de venta)", valor: v.value.vendido || 0, nota: v.value.vendido_directo ? `${dineroCorto(v.value.vendido_directo, mon.value)} sin cotización` : "" },
    { nombre: "Facturado", valor: v.value.facturado || 0, nota: v.value.vendido ? `${pct(v.value.facturado, v.value.vendido)} % de lo vendido` : "" },
  ];
  if (props.t.cobros_registrados) filas.push({ nombre: "Cobrado", valor: v.value.cobrado || 0, nota: v.value.facturado ? `${pct(v.value.cobrado, v.value.facturado)} %` : "" });
  return filas;
});
const etapas = computed(() => (props.t.costeos.etapas || []).map((e) => ({ nombre: NOMBRE_ETAPA[e.etapa] || e.etapa, valor: e.n })));
const lista = (bloque, sufijo) => (bloque?.filas || []).map((f) => ({
  nombre: f.nombre, valor: f.monto, otros: !f.clave, nota: `${f.n} ${sufijo}${bloque.total ? ` · ${pct(f.monto, bloque.total)} %` : ""}`,
}));
const borradores = computed(() => {
  const b = props.t.borradores || {};
  return [["Quotation", "cotizaciones"], ["Sales Order", "órdenes de venta"], ["Purchase Order", "órdenes de compra"], ["Sales Invoice", "facturas de venta"]]
    .filter(([dt]) => b[dt]?.n).map(([dt, l]) => ({ l, n: b[dt].n, monto: b[dt].monto }));
});
</script>
