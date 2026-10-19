<!--
  Inicio · vista operativa (todo el equipo; api/tablero.get_tablero_operativo):
  el trabajo de cada quien y el estado de la operación HOY. Cantidades y fechas,
  sin cifras financieras de la empresa.
-->
<template>
  <div class="space-y-5">
    <!-- Tu trabajo -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
      <Indicador icono="editar" etiqueta="Tus borradores" :valor="String(o.mi_trabajo.borradores)" nota="capturados por ti, sin enviar ni validar" />
      <Indicador icono="enviar" etiqueta="En aprobación" :valor="String(o.mi_trabajo.en_aprobacion)" nota="enviados por ti, esperando revisión o Dirección" />
      <Indicador icono="regresar" etiqueta="Te regresaron" :valor="String(o.mi_trabajo.regresados)" :alerta="o.mi_trabajo.regresados > 0"
                 :nota="o.mi_trabajo.regresados ? 'corrígelos y reenvíalos (arriba)' : 'nada por corregir'" />
      <Indicador icono="check-circulo" etiqueta="Aprobados" :valor="String(o.mi_trabajo.aprobados_7d)" nota="tuyos, en los últimos 7 días" />
    </div>

    <!-- Entregas: carga por semana + las más próximas -->
    <div class="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
      <section class="p-panel p-5">
        <div class="flex items-baseline justify-between gap-3 flex-wrap">
          <p class="text-[14px] font-semibold">Prendas por entregar, por semana</p>
          <p class="p-meta">{{ o.entregas.abiertas }} órdenes abiertas<span v-if="o.entregas.vencidas" class="text-red-700"> · {{ o.entregas.vencidas }} vencidas</span></p>
        </div>
        <p class="p-meta mb-3">Lo que falta entregar de cada orden de venta, según su fecha de entrega</p>
        <ColumnasMes :datos="semanas" :series="SERIE_PRENDAS" :leyenda="false" :formato="(x) => `${numero(x)} prendas`" :formato-corto="(x) => numero(x)" titulo="Prendas por entregar por semana" />
      </section>
      <section class="p-panel p-5">
        <p class="text-[14px] font-semibold">Próximas entregas</p>
        <p class="p-meta mb-3">Las más cercanas (y las vencidas primero)</p>
        <p v-if="!o.entregas.proximas.length" class="p-meta py-6 flex items-center gap-2"><Icono nombre="check-circulo" class="w-4 h-4 text-emerald-600" />No hay entregas pendientes.</p>
        <div class="space-y-3.5">
          <RouterLink
            v-for="e in o.entregas.proximas" :key="e.name" :to="e.costeo ? `/costeo/${encodeURIComponent(e.costeo)}` : `/ordenes-venta/${encodeURIComponent(e.name)}`"
            class="block group"
          >
            <div class="flex items-baseline justify-between gap-3">
              <p class="text-[12.5px] font-medium truncate group-hover:text-brand-700">{{ e.proyecto }}</p>
              <span class="text-[11.5px] whitespace-nowrap inline-flex items-center gap-1" :class="e.vencida ? 'text-red-700 font-semibold' : 'text-ink-muted'"><Icono v-if="e.vencida" nombre="alerta" class="w-3.5 h-3.5" />{{ e.vencida ? "venció " : "" }}{{ fecha(e.fecha) }}</span>
            </div>
            <p class="text-[11.5px] text-ink-muted truncate">{{ e.cliente }} · faltan {{ numero(e.pendiente) }} de {{ numero(e.prendas) }}</p>
            <div class="h-1.5 rounded-full mt-1" :class="e.vencida ? 'bg-red-50' : 'bg-brand-50'">
              <div class="h-1.5 rounded-full" :class="e.vencida ? 'bg-red-600' : 'bg-brand-600'" :style="{ width: `${Math.max(e.entregado_pct ? 3 : 0, e.entregado_pct)}%` }"></div>
            </div>
          </RouterLink>
        </div>
      </section>
    </div>

    <!-- Compras y maquila -->
    <div class="grid gap-5 lg:grid-cols-2">
      <section class="p-panel p-5">
        <p class="text-[14px] font-semibold">Compras de material</p>
        <p class="p-meta mb-4">Órdenes de compra validadas de los proyectos abiertos</p>
        <BarraComposicion v-if="o.compras.total" :partes="estado(o.compras)" :formato="(x) => `${numero(x)} OC`" titulo="Estado de las órdenes de compra" />
        <p v-else class="p-meta">No hay órdenes de compra abiertas.</p>
        <div class="flex flex-wrap gap-2 mt-4">
          <span v-if="o.compras.vencidas" class="p-pill-bad"><Icono nombre="alerta" class="w-3.5 h-3.5" />{{ o.compras.vencidas }} con entrega vencida</span>
          <span v-if="o.compras.por_facturar" class="p-pill-wait">{{ o.compras.por_facturar }} recibidas sin factura</span>
        </div>
      </section>
      <section class="p-panel p-5">
        <div class="flex items-baseline justify-between gap-3">
          <p class="text-[14px] font-semibold">Avance por taller</p>
          <p class="p-meta">{{ o.maquila.recibidas }} de {{ o.maquila.total }} órdenes completas</p>
        </div>
        <p class="p-meta mb-4">Órdenes a taller abiertas, % recibido (lo más atrasado primero)</p>
        <BarrasLista :filas="talleres" :formato="(x) => `${x} %`" :maximo="100" color="#eb6834" riel="#fdeee8" vacio="No hay órdenes a taller abiertas." />
      </section>
    </div>

    <!-- Facturas y proyectos -->
    <div class="grid gap-5 lg:grid-cols-[1fr_2fr]">
      <div class="grid grid-cols-2 lg:grid-cols-1 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
        <Indicador icono="factura" etiqueta="Facturas de compra en borrador" :valor="String(o.facturas_borrador)" nota="por completar y validar (con su PDF)" />
        <Indicador icono="paquete" etiqueta="Recibido sin factura" :valor="String(o.compras.por_facturar + o.maquila.por_facturar)" nota="órdenes recibidas al 100 % que aún no se facturan" />
      </div>
      <section class="p-panel p-5">
        <p class="text-[14px] font-semibold">Proyectos por etapa</p>
        <p class="p-meta mb-4">Hoy · {{ o.costeos.total }} costeos</p>
        <Recorrido :etapas="etapas" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import Icono from "@/components/Icono.vue";
import BarraComposicion from "@/components/tablero/BarraComposicion.vue";
import BarrasLista from "@/components/tablero/BarrasLista.vue";
import ColumnasMes from "@/components/tablero/ColumnasMes.vue";
import Indicador from "@/components/tablero/Indicador.vue";
import Recorrido from "@/components/tablero/Recorrido.vue";
import { fecha, numero } from "@/utils/formato.js";

const props = defineProps({ o: { type: Object, required: true } });

const SERIE_PRENDAS = [{ clave: "prendas", etiqueta: "Prendas", color: "#f05208" }];
const NOMBRE_ETAPA = { Borrador: "Costeo", Cotizado: "Cotizado", "Orden de Venta": "Orden de venta", "En Producción": "Producción", Entregado: "Entregado", Completado: "Completado" };

// "Vencido" va en rojo (color de estado) y con su texto: nunca solo el color.
const semanas = computed(() => props.o.entregas.semanas.map((s, i) => ({
  mes: s.desde || `v${i}`, etiqueta: s.etiqueta, prendas: Math.round(s.prendas), ...(s.vencido ? { _color: "#dc2626" } : {}),
})));
const estado = (e) => [
  { clave: "por_recibir", etiqueta: "Por recibir", monto: e.por_recibir },
  { clave: "parcial", etiqueta: "Recibidas en parte", monto: e.parcial },
  { clave: "recibidas", etiqueta: "Recibidas", monto: e.recibidas },
];
const talleres = computed(() => props.o.talleres.map((t) => ({
  nombre: t.nombre, valor: t.avance, nota: `${t.ordenes} OC${t.vencidas ? ` · ${t.vencidas} ${t.vencidas === 1 ? "vencida" : "vencidas"}` : ""}`,
})));
const etapas = computed(() => (props.o.costeos.etapas || []).map((e) => ({ nombre: NOMBRE_ETAPA[e.etapa] || e.etapa, valor: e.n })));
</script>
