<!--
  Menú izquierdo de Producción (docs/plan-ui-produccion.md §4.2).

  Reemplaza tres cosas que hoy están repartidas: la sub-navegación del paso 5, el
  `ActiveSOSelector` de ese paso y el riel de lotes del stepper del costeo.

    [ Orden de venta ▾ ]   nombre · cantidades por producto · N lotes
    Tablero
    PREPARAR    Preparación (n/3) · Orden de manufactura (n/total)
    LOTES       un renglón por lote con su punto y su paso actual · + Nuevo lote
    BANDEJAS    Envíos (n) · Facturas (n)

  Solo muestra las vistas que el rol permite (§6.3). En celular (<1024px) se
  convierte en un <select> arriba del contenido.
-->
<template>
  <!-- ── Celular: el mismo contenido como selector, arriba del contenido ────── -->
  <select v-if="movil" class="p-field mb-5 lg:hidden" :value="valorMovil" @change="onMovil($event.target.value)">
    <option v-if="puedeVer('tablero')" value="v:tablero">Tablero</option>
    <option value="v:preparacion">Preparación ({{ prep.hechos }}/3)</option>
    <option v-if="puedeVer('preparacion')" value="v:ordenes">Órdenes a talleres ({{ ordenes.validadas }}/{{ ordenes.total }})</option>
    <option v-for="l in (puedeVerAlgunLote ? lotes : [])" :key="l.lote_ref" :value="`l:${l.lote_ref}`">
      {{ l.lote_ref }} — {{ l.resumen }}
    </option>
    <option v-if="puedeVer('envios')" value="v:envios">Envíos{{ conteos.envios ? ` (${conteos.envios})` : "" }}</option>
    <option v-if="puedeVer('facturas')" value="v:facturas">Facturas{{ conteos.facturas ? ` (${conteos.facturas})` : "" }}</option>
  </select>

  <!-- ── Escritorio ─────────────────────────────────────────────────────────── -->
  <aside v-else class="w-[248px] flex-shrink-0 border-r border-surface-border px-3 py-4 hidden lg:block">
    <!-- Orden de venta activa -->
    <div v-if="salesOrders.length" class="p-panel px-3 py-2.5">
      <p class="p-eyebrow">Orden de venta</p>
      <div class="flex items-center justify-between gap-2 mt-0.5">
        <select
          v-if="salesOrders.length > 1"
          class="text-[13px] font-semibold bg-transparent border-0 p-0 flex-1 min-w-0 focus:outline-none cursor-pointer"
          :value="activeSOName"
          @change="emit('cambiar-ov', $event.target.value)"
        >
          <option v-for="so in salesOrders" :key="so.name" :value="so.name">{{ so.name }}</option>
        </select>
        <span v-else class="text-[13px] font-semibold truncate">{{ salesOrders[0].name }}</span>
      </div>
      <p class="p-meta truncate" :title="resumenOV">{{ resumenOV }}</p>
    </div>

    <div v-if="puedeVer('tablero')" class="mt-3">
      <button type="button" class="p-rail-item" :class="{ on: vista === 'tablero' }" @click="emit('ir', { vista: 'tablero' })">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 5h7v7H4zM13 5h7v4h-7zM13 11h7v8h-7zM4 14h7v5H4z"/></svg>
        Tablero
      </button>
    </div>

    <template v-if="puedeVer('preparacion') || puedeVer('om')">
      <div class="p-rail-group">Preparar</div>
      <div class="space-y-0.5">
        <button
          type="button" class="p-rail-item"
          :class="{ on: vista === 'preparacion' }" @click="emit('ir', { vista: 'preparacion' })"
        >
          <EstadoPunto :estado="prep.estado" />Preparación<span class="p-count">{{ prep.hechos }}/3</span>
        </button>
        <button
          v-if="puedeVer('preparacion')" type="button" class="p-rail-item"
          :class="{ on: vista === 'ordenes' }" @click="emit('ir', { vista: 'ordenes' })"
        >
          <EstadoPunto :estado="ordenes.estado" />Órdenes a talleres<span class="p-count">{{ ordenes.validadas }}/{{ ordenes.total }}</span>
        </button>
      </div>
    </template>

    <template v-if="puedeVerAlgunLote">
      <div class="p-rail-group">Lotes</div>
      <div class="space-y-0.5">
        <button
          v-for="l in lotes" :key="l.lote_ref" type="button" class="p-rail-item"
          :class="{ on: vista === 'lote' && loteRef === l.lote_ref }"
          :title="l.titulo_largo"
          @click="emit('ir', { vista: 'lote', lote: l.lote_ref })"
        >
          <EstadoPunto :estado="l.estado" /><span class="truncate">{{ l.lote_ref }}</span>
          <span class="p-count truncate max-w-[92px]">{{ l.resumen }}</span>
        </button>
        <p v-if="!lotes.length" class="px-2.5 py-1 text-[12px] text-ink-light">Todavía no hay lotes.</p>
        <button
          v-if="puedeVer('preparacion')" type="button" class="p-rail-item text-brand-600"
          @click="emit('nuevo-lote')"
        ><span class="w-4 text-center flex-shrink-0">+</span>Nuevo lote</button>
      </div>
    </template>

    <template v-if="puedeVer('envios') || puedeVer('facturas')">
      <div class="p-rail-group">Bandejas</div>
      <div class="space-y-0.5">
        <button
          v-if="puedeVer('envios')" type="button" class="p-rail-item"
          :class="{ on: vista === 'envios' }" @click="emit('ir', { vista: 'envios' })"
        >
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M3 7h11v9H3zM14 10h4l3 3v3h-7z"/><circle cx="7" cy="17.5" r="1.5"/><circle cx="17" cy="17.5" r="1.5"/></svg>
          Envíos<span v-if="conteos.envios" class="p-count-hot">{{ conteos.envios }}</span>
        </button>
        <button
          v-if="puedeVer('facturas')" type="button" class="p-rail-item"
          :class="{ on: vista === 'facturas' }" @click="emit('ir', { vista: 'facturas' })"
        >
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M7 3h10v18l-2.5-1.5L12 21l-2.5-1.5L7 21zM10 8h4M10 12h4"/></svg>
          Facturas<span v-if="conteos.facturas" class="p-count-hot">{{ conteos.facturas }}</span>
        </button>
      </div>
    </template>
  </aside>
</template>

<script setup>
import { computed } from "vue";
import EstadoPunto from "@/components/produccion/EstadoPunto.vue";

const props = defineProps({
  vista: { type: String, default: "" },
  loteRef: { type: String, default: "" },
  salesOrders: { type: Array, default: () => [] },
  activeSOName: { type: String, default: "" },
  resumenOV: { type: String, default: "" },
  // [{ lote_ref, estado, resumen, titulo_largo }]
  lotes: { type: Array, default: () => [] },
  prep: { type: Object, default: () => ({ hechos: 0, estado: "off" }) },
  ordenes: { type: Object, default: () => ({ validadas: 0, total: 0, estado: "off" }) },
  conteos: { type: Object, default: () => ({ envios: 0, facturas: 0 }) },
  puedeVer: { type: Function, default: () => true },
  // En celular (<1024px) el menú es un <select> arriba del contenido, no una
  // columna: el layout monta una segunda instancia con `movil`.
  movil: { type: Boolean, default: false },
});
const emit = defineEmits(["ir", "nuevo-lote", "cambiar-ov"]);

const puedeVerAlgunLote = computed(() =>
  ["materia", "flujo", "talleres", "entrega"].some((v) => props.puedeVer(v)));

const valorMovil = computed(() =>
  props.vista === "lote" && props.loteRef ? `l:${props.loteRef}` : `v:${props.vista || "tablero"}`);

function onMovil(valor) {
  const [tipo, resto] = [valor.slice(0, 1), valor.slice(2)];
  if (tipo === "l") emit("ir", { vista: "lote", lote: resto });
  else emit("ir", { vista: resto });
}
</script>
