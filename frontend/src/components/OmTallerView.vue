<template>
  <!-- La OM tal como la recibe ESTE taller: un registro por producto que trabaja, con
       la info general y las tallas completas y solo lo que se le asignó en la OM
       general (om_general.om_de_oc). Se captura en Preparación · Orden de manufactura. -->
  <div class="rounded-lg border border-surface-border bg-white p-3 space-y-3">
    <div class="flex items-center justify-between gap-2">
      <p class="section-title">Orden de manufactura de este taller</p>
      <span class="text-[11px] text-ink-light">Se captura en Preparación · Orden de manufactura</span>
    </div>
    <div v-for="r in registros" :key="r.producto" class="border-t border-surface-border first:border-t-0 pt-2.5 first:pt-0 space-y-2.5">
      <p class="text-[12.5px] font-medium text-ink">{{ r.item_name || r.producto }}</p>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-1 text-[12px]">
        <div v-for="c in campos" :key="c.f" v-show="r.general[c.f]"><span class="text-ink-light">{{ c.label }}:</span> <span class="text-ink">{{ valor(r.general, c.f) }}</span></div>
      </div>
      <p v-if="marcas(r.general)" class="text-[12px] text-ink"><span class="text-ink-light">Lleva:</span> {{ marcas(r.general) }}</p>

      <div v-if="r.tallas.length" class="flex flex-wrap gap-1.5">
        <span v-for="(t, i) in r.tallas" :key="i" class="text-[11.5px] px-2 py-0.5 rounded bg-surface-raised text-ink">{{ [t.genero, t.talla].filter(Boolean).join(' ') }} <strong class="tabular-nums">{{ (t.cantidad || 0).toLocaleString('es-MX') }}</strong></span>
      </div>

      <div v-if="r.procesos.length">
        <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-0.5">Procesos</p>
        <p v-for="(p, i) in r.procesos" :key="i" class="text-[12px] text-ink">{{ p.nombre_proceso }}<span v-if="p.ubicacion" class="text-ink-muted"> · {{ p.ubicacion }}</span><span v-if="p.colores" class="text-ink-muted"> · {{ p.colores }}</span></p>
      </div>
      <div v-if="r.observaciones.length">
        <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-0.5">Observaciones</p>
        <p v-for="(o, i) in r.observaciones" :key="i" class="text-[12px] text-ink whitespace-pre-line">{{ o.texto }}</p>
      </div>
      <div v-if="r.tablas.length">
        <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-0.5">Tablas de medidas</p>
        <div v-for="(t, ti) in r.tablas" :key="ti" class="mb-2 overflow-x-auto">
          <p class="text-[12px] text-ink mb-0.5">{{ t.name }}<span v-if="t.unit" class="text-ink-light"> ({{ t.unit }})</span></p>
          <table class="text-[12px] border border-surface-border">
            <tr v-for="row in t.rows" :key="row.id"><td v-for="c in t.columns" :key="c" class="border border-surface-border px-2 py-0.5 text-center">{{ row.cells[c] }}</td></tr>
          </table>
        </div>
      </div>
      <div v-if="r.archivos.length" class="flex flex-wrap gap-2">
        <a v-for="(a, i) in r.archivos" :key="i" :href="a.archivo" target="_blank" class="flex items-center gap-1.5 text-[11.5px] text-brand-600 hover:underline">
          <img v-if="esImagen(a.archivo)" :src="a.archivo" class="w-10 h-10 object-cover rounded border border-surface-border" alt="" />
          <span>{{ a.descripcion || 'Archivo' }}</span>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ registros: { type: Array, default: () => [] } });
const campos = [
  { f: "om_modelo", label: "Modelo" }, { f: "om_tela", label: "Tela" }, { f: "om_color", label: "Color" },
  { f: "om_color_principal", label: "Color principal" }, { f: "om_forro", label: "Forro" },
  { f: "om_combinacion", label: "Combinación" }, { f: "om_ubicacion", label: "Ubicación" },
  { f: "om_aberturas", label: "Aberturas" }, { f: "om_fecha_requerida", label: "Fecha requerida" },
];
function valor(g, f) {
  const v = g[f];
  if (f === "om_fecha_requerida" && v) { const [y, m, d] = String(v).slice(0, 10).split("-"); return `${d}/${m}/${y}`; }
  return v;
}
const marcas = (g) => [["om_bordado", "Bordado"], ["om_estampado", "Estampado"], ["om_sublimado", "Sublimado"], ["om_reflejante", "Reflejante"]]
  .filter(([f]) => Number(g[f])).map(([, l]) => l).join(", ");
const esImagen = (u) => /\.(png|jpe?g|gif|webp|svg|bmp)(\?.*)?$/i.test(u || "");
</script>
