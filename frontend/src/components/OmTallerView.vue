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
        <!-- Información general -->
        <section v-if="generales(r.general).length || marcas(r.general).length">
          <p class="om-titulo">Información general</p>
          <dl v-if="generales(r.general).length" class="grid grid-cols-2 gap-x-4 gap-y-1.5">
            <div v-for="c in generales(r.general)" :key="c.f" class="min-w-0">
              <dt class="text-[10.5px] text-ink-light">{{ c.label }}</dt>
              <dd class="text-[12.5px] text-ink truncate">{{ r.general[c.f] }}</dd>
            </div>
          </dl>
          <div v-if="marcas(r.general).length" class="flex flex-wrap items-center gap-1.5" :class="generales(r.general).length ? 'mt-2.5' : ''">
            <span class="text-[10.5px] text-ink-light mr-0.5">Lleva</span>
            <span v-for="m in marcas(r.general)" :key="m" class="text-[11.5px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-medium">{{ m }}</span>
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
const campos = [
  { f: "om_modelo", label: "Modelo" }, { f: "om_tela", label: "Tela" }, { f: "om_color", label: "Color" },
  { f: "om_color_principal", label: "Color principal" }, { f: "om_forro", label: "Forro" },
  { f: "om_combinacion", label: "Combinación" }, { f: "om_ubicacion", label: "Ubicación" },
  { f: "om_aberturas", label: "Aberturas" },
];
// La fecha requerida ya no vive en la ficha: es de cada encargo al taller.
const generales = (g) => campos.filter((c) => g[c.f]);
const marcas = (g) => [["om_bordado", "Bordado"], ["om_estampado", "Estampado"], ["om_sublimado", "Sublimado"], ["om_reflejante", "Reflejante"]]
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
