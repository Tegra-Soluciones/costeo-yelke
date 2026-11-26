<template>
  <!-- La OM tal como la recibe ESTE taller: un registro por producto que trabaja, con
       la info general y las tallas completas y solo lo que se le asignó en la OM
       general (om_general.om_de_oc). Se captura en Preparación · Orden de manufactura. -->
  <div class="space-y-3">
    <div v-for="r in registros" :key="r.producto" class="rounded-xl border border-surface-border bg-white overflow-hidden">
      <div class="flex items-center justify-between gap-3 px-4 py-2.5 bg-zinc-50 border-b border-surface-border">
        <p class="text-[13px] font-semibold text-ink truncate">{{ r.item_name || r.producto }}</p>
        <span v-if="r.tallas.length" class="text-[12px] text-ink-muted tabular-nums flex-shrink-0">{{ fmt(totalTallas(r.tallas)) }} prendas</span>
      </div>

      <div class="p-4 space-y-4">
        <!-- Información general: modelo, telas (la principal resaltada), qué lleva y aberturas -->
        <section v-if="r.general.om_modelo || (r.telas || []).length || marcas(r.general).length || (r.aberturas || []).length">
          <p class="om-titulo">Información general</p>
          <p v-if="r.general.om_modelo" class="text-[12.5px] text-ink"><span class="text-[10.5px] text-ink-light mr-1.5">Modelo de prenda</span>{{ r.general.om_modelo }}</p>
          <div v-if="(r.telas || []).length" class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
            <div v-for="t in r.telas" :key="t.tela" class="rounded-lg px-3 py-2 ring-1" :class="t.principal ? 'ring-green-300 bg-green-50/60' : 'ring-surface-border'">
              <p class="text-[10px] font-semibold uppercase tracking-wider" :class="t.principal ? 'text-green-700' : 'text-ink-light'">{{ t.principal ? 'Tela principal' : 'Tela secundaria' }}</p>
              <p class="text-[12.5px] text-ink font-medium">{{ t.nombre }}</p>
              <p v-if="t.composicion" class="text-[11.5px] text-ink-muted">Composición: {{ t.composicion }}</p>
              <p v-if="t.color" class="text-[11.5px] text-ink-muted">Color: {{ t.color }}</p>
              <p v-if="t.ubicacion" class="text-[11.5px] text-ink-muted">Ubicación: {{ t.ubicacion }}</p>
            </div>
          </div>
          <div v-if="marcas(r.general).length" class="flex flex-wrap items-center gap-1.5 mt-2.5">
            <span class="text-[10.5px] text-ink-light mr-0.5">Lleva</span>
            <span v-for="m in marcas(r.general)" :key="m" class="text-[11.5px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-medium">{{ m }}</span>
          </div>
          <div v-if="(r.aberturas || []).length" class="mt-2.5">
            <p class="text-[10.5px] text-ink-light mb-1">Aberturas</p>
            <ul class="divide-y divide-surface-border rounded-lg border border-surface-border">
              <li v-for="(a, i) in r.aberturas" :key="i" class="px-3 py-1.5 text-[12.5px]">
                <span class="text-ink font-medium tabular-nums">{{ a.numero }}</span>
                <span v-if="a.ubicacion" class="text-ink-muted"> · {{ a.ubicacion }}</span>
                <span v-if="a.descripcion" class="text-ink-muted"> · {{ a.descripcion }}</span>
              </li>
            </ul>
          </div>
        </section>

        <!-- Tallas: una tabla por género; las tallas extra aparte -->
        <section v-if="r.tallas.length">
          <p class="om-titulo">Tallas</p>
          <div class="space-y-2">
            <div v-for="g in gruposTallas(r)" :key="g.clave" class="rounded-lg border border-surface-border overflow-x-auto">
              <table class="w-full text-[12px]">
                <thead>
                  <tr class="bg-zinc-50 text-ink-muted">
                    <th class="text-left font-medium px-2.5 py-1.5 whitespace-nowrap">{{ g.titulo }}</th>
                    <th v-for="t in g.tallas" :key="t.talla" class="font-medium px-2 py-1.5 text-center">{{ t.talla }}</th>
                    <th class="font-semibold px-2.5 py-1.5 text-right text-ink">Total</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="px-2.5 py-1.5 text-ink-light">Piezas</td>
                    <td v-for="t in g.tallas" :key="t.talla" class="px-2 py-1.5 text-center tabular-nums text-ink">{{ fmt(t.cantidad) }}</td>
                    <td class="px-2.5 py-1.5 text-right tabular-nums font-semibold text-ink">{{ fmt(g.total) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- Procesos -->
        <section v-if="r.procesos.length">
          <p class="om-titulo">Procesos</p>
          <ul class="divide-y divide-surface-border rounded-lg border border-surface-border">
            <li v-for="(p, i) in r.procesos" :key="i" class="px-3 py-1.5 text-[12.5px]">
              <span class="text-ink font-medium">{{ p.nombre_proceso }}</span>
              <span v-if="p.ubicacion" class="text-ink-muted"> · {{ p.ubicacion }}</span>
              <span v-if="p.colores" class="text-ink-muted"> · {{ p.colores }}</span>
              <span v-if="p.medida" class="text-ink-muted"> · Medida: {{ p.medida }}</span>
              <p v-if="p.descripcion" class="text-[11.5px] text-ink-muted whitespace-pre-line mt-0.5">{{ p.descripcion }}</p>
            </li>
          </ul>
        </section>

        <!-- Observaciones -->
        <section v-if="r.observaciones.length">
          <p class="om-titulo">Observaciones</p>
          <div class="space-y-1.5">
            <p v-for="(o, i) in r.observaciones" :key="i" class="text-[12.5px] text-ink whitespace-pre-line bg-amber-50/60 border border-amber-100 rounded-lg px-3 py-2">{{ o.texto }}</p>
          </div>
        </section>

        <!-- Tablas de medidas -->
        <section v-if="r.tablas.length">
          <p class="om-titulo">Tablas de medidas</p>
          <div v-for="(t, ti) in r.tablas" :key="ti" class="mb-2.5 last:mb-0">
            <p class="text-[12px] text-ink mb-1">{{ t.name }}<span v-if="t.unit" class="text-ink-light"> · {{ t.unit }}</span></p>
            <div class="rounded-lg border border-surface-border overflow-x-auto">
              <table class="w-full text-[11.5px]">
                <tr v-for="(row, ri) in t.rows" :key="row.id" :class="ri === 0 ? 'bg-zinc-50 font-medium text-ink-muted' : 'text-ink'">
                  <td v-for="(c, ci) in t.columns" :key="c" class="px-2 py-1 border-t border-surface-border first:border-l-0" :class="[ri === 0 ? 'border-t-0' : '', ci === 0 ? 'text-left whitespace-nowrap' : 'text-center tabular-nums']">{{ row.cells[c] }}</td>
                </tr>
              </table>
            </div>
          </div>
        </section>

        <!-- Archivos -->
        <section v-if="r.archivos.length">
          <p class="om-titulo">Archivos</p>
          <div class="flex flex-wrap gap-2">
            <a v-for="(a, i) in r.archivos" :key="i" :href="a.archivo" target="_blank" class="flex items-center gap-2 rounded-lg border border-surface-border px-2 py-1.5 hover:bg-zinc-50 max-w-full">
              <img v-if="esImagen(a.archivo)" :src="a.archivo" class="w-9 h-9 object-cover rounded" alt="" />
              <Icono v-else nombre="documento" class="w-4 h-4 text-ink-light flex-shrink-0" />
              <span class="text-[12px] text-brand-700 truncate">{{ a.descripcion || "Archivo" }}</span>
            </a>
          </div>
        </section>
      </div>
    </div>
    <p class="text-[11px] text-ink-light">La ficha se captura en Preparación · Orden de manufactura.</p>
  </div>
</template>

<script setup>
import Icono from "@/components/Icono.vue";

defineProps({ registros: { type: Array, default: () => [] } });
// Info general (2026-11-26): modelo, telas, checks y aberturas. Una OM legacy (de la
// orden de compra) no trae telas ni aberturas: solo se ve lo que tenga.
const marcas = (g) => [["om_bordado", "Bordado"], ["om_estampado", "Estampado"], ["om_sublimado", "Sublimado"],
  ["om_reflejante", "Reflejante"], ["om_dtf", "DTF"], ["om_vinil", "Vinil"]]
  .filter(([f]) => Number(g[f])).map(([, l]) => l);
const esImagen = (u) => /\.(png|jpe?g|gif|webp|svg|bmp)(\?.*)?$/i.test(u || "");
const fmt = (n) => Number(n || 0).toLocaleString("es-MX");
const totalTallas = (ts) => ts.reduce((a, t) => a + (Number(t.cantidad) || 0), 0);
// Regulares del producto base por género; las de sus variantes (tallas extra), aparte.
function gruposTallas(r) {
  const grupos = [];
  for (const t of r.tallas) {
    const extra = t.producto && t.producto !== r.producto;
    const clave = `${extra ? "x" : "r"}|${t.genero || ""}`;
    let g = grupos.find((x) => x.clave === clave);
    if (!g) grupos.push(g = { clave, titulo: `${t.genero || "Sin género"}${extra ? " · tallas extra" : ""}`, tallas: [], total: 0 });
    g.tallas.push(t);
    g.total += Number(t.cantidad) || 0;
  }
  return grupos.sort((a, b) => a.clave.localeCompare(b.clave, "es"));
}
</script>

<style scoped>
.om-titulo { @apply text-[10.5px] font-semibold text-ink-muted uppercase tracking-wider mb-1.5; }
</style>
