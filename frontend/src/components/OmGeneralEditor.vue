<template>
  <!-- Órdenes de manufactura GENERALES del costeo: una por producto base (su variante
       de talla entra como tallas). La info general y las tallas van a TODOS los
       talleres; procesos, observaciones, tablas y archivos solo a los que se marquen.
       De aquí se arma la OM de cada orden de maquila (api/om_general.py). -->
  <div class="rounded-lg border border-surface-border bg-white p-3">
    <div class="flex items-start justify-between gap-3 mb-2">
      <div>
        <p class="section-title">Órdenes de manufactura</p>
        <p class="text-[11.5px] text-ink-muted">Una por producto. La info general y las tallas van a todos los talleres; lo demás, solo a los talleres que marques en "Para".</p>
      </div>
    </div>

    <p v-if="loading" class="text-[12px] text-ink-light">Cargando…</p>
    <div v-for="p in productos" :key="p.producto" class="border-t border-surface-border first:border-t-0 py-2">
      <div class="flex items-center gap-3 flex-wrap">
        <div class="min-w-0 flex-1">
          <p class="text-[12.5px] font-medium text-ink">{{ p.item_name }}<span v-if="p.variantes.length" class="font-normal text-ink-light"> · incluye {{ p.variantes.join(', ') }}</span></p>
          <p class="text-[11px] text-ink-light">{{ p.talleres.length }} talleres · {{ total(p.tallas).toLocaleString('es-MX') }} prendas</p>
        </div>
        <span class="text-[10.5px] font-semibold px-2 py-0.5 rounded-full" :class="p.om ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ p.om ? 'Capturada' : 'Sin capturar' }}</span>
        <button type="button" class="doc-action" @click="toggle(p)">{{ abierto === p.producto ? 'Cerrar' : (p.om ? 'Editar' : 'Capturar') }}</button>
      </div>

      <div v-if="abierto === p.producto && form" class="mt-3 space-y-4">
        <!-- Info general (para todos) -->
        <div>
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-2">Info general <span class="normal-case font-normal text-ink-light">· para todos los talleres</span></p>
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div><label class="field-label">Modelo</label><input v-model="form.general.om_modelo" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Tela</label><input v-model="form.general.om_tela" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Color</label><input v-model="form.general.om_color" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Color principal</label><input v-model="form.general.om_color_principal" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Forro</label><input v-model="form.general.om_forro" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Combinación</label><input v-model="form.general.om_combinacion" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Ubicación</label><input v-model="form.general.om_ubicacion" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Aberturas</label><input v-model.number="form.general.om_aberturas" type="number" min="0" :disabled="disabled" class="field-input" /></div>
            <div><label class="field-label">Fecha requerida</label><input v-model="form.general.om_fecha_requerida" type="date" :disabled="disabled" class="field-input" /></div>
          </div>
          <div class="flex items-center gap-4 mt-2 text-[13px]">
            <label v-for="c in checks" :key="c.f" class="flex items-center gap-1.5"><input type="checkbox" v-model="form.general[c.f]" :true-value="1" :false-value="0" :disabled="disabled" class="accent-brand-500" />{{ c.label }}</label>
          </div>
        </div>

        <!-- Tallas heredadas del costeo -->
        <div>
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Tallas <span class="normal-case font-normal text-ink-light">· del costeo, para todos los talleres</span></p>
          <table class="text-[12.5px]">
            <thead><tr class="text-[10.5px] text-ink-light text-left"><th class="pr-6 font-medium">Género</th><th class="pr-6 font-medium">Talla</th><th class="pr-6 font-medium">Producto</th><th class="font-medium text-right">Cantidad</th></tr></thead>
            <tbody>
              <tr v-for="(t, i) in p.tallas" :key="i">
                <td class="pr-6">{{ t.genero || '—' }}</td><td class="pr-6">{{ t.talla }}</td>
                <td class="pr-6 text-ink-muted text-[11.5px]">{{ t.producto }}</td>
                <td class="text-right tabular-nums">{{ (t.cantidad || 0).toLocaleString('es-MX') }}</td>
              </tr>
              <tr class="border-t border-surface-border"><td colspan="3" class="pr-6 text-ink-muted">Total</td><td class="text-right tabular-nums font-medium">{{ total(p.tallas).toLocaleString('es-MX') }}</td></tr>
            </tbody>
          </table>
          <p class="text-[11px] text-ink-light mt-1">Para cambiar el desglose por talla, edítalo en Costear (tallas del producto).</p>
        </div>

        <!-- Procesos -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Procesos</p>
            <button v-if="!disabled" type="button" class="add-link" @click="form.procesos.push({ nombre_proceso: '', ubicacion: '', colores: '', proveedores: [] })">+ Proceso</button>
          </div>
          <p v-if="!form.procesos.length" class="prod-empty">Sin procesos.</p>
          <div v-for="(r, i) in form.procesos" :key="'p' + i" class="rounded-lg ring-1 ring-surface-border p-2 mb-1.5">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-1.5">
              <input v-model="r.nombre_proceso" placeholder="Nombre del proceso" :disabled="disabled" class="field-input" />
              <input v-model="r.ubicacion" placeholder="Ubicación" :disabled="disabled" class="field-input" />
              <input v-model="r.colores" placeholder="Colores" :disabled="disabled" class="field-input" />
            </div>
            <div class="flex items-center justify-between gap-2">
              <ParaTalleres v-model="r.proveedores" :talleres="p.talleres" :disabled="disabled" />
              <button v-if="!disabled" type="button" class="del-btn" @click="form.procesos.splice(i, 1)">✕</button>
            </div>
          </div>
        </div>

        <!-- Observaciones -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Observaciones</p>
            <button v-if="!disabled" type="button" class="add-link" @click="form.observaciones.push({ texto: '', proveedores: [] })">+ Observación</button>
          </div>
          <p v-if="!form.observaciones.length" class="prod-empty">Sin observaciones.</p>
          <div v-for="(r, i) in form.observaciones" :key="'o' + i" class="rounded-lg ring-1 ring-surface-border p-2 mb-1.5">
            <textarea v-model="r.texto" rows="2" :disabled="disabled" class="field-input mb-1.5" placeholder="Indicación para el taller…"></textarea>
            <div class="flex items-center justify-between gap-2">
              <ParaTalleres v-model="r.proveedores" :talleres="p.talleres" :disabled="disabled" />
              <button v-if="!disabled" type="button" class="del-btn" @click="form.observaciones.splice(i, 1)">✕</button>
            </div>
          </div>
        </div>

        <!-- Tablas de medidas -->
        <div>
          <div class="flex items-center justify-between mb-1 flex-wrap gap-2">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Tablas de medidas</p>
            <div v-if="!disabled" class="flex items-center gap-2">
              <select class="field-input text-[12.5px] py-1" :value="''" @change="agregarPlantilla($event.target.value); $event.target.value = ''">
                <option value="">Usar plantilla…</option>
                <option v-for="t in medidasTemplates" :key="t.key" :value="t.key">{{ t.label }}</option>
              </select>
              <button type="button" class="add-link" @click="form.tablas.push(tablaVacia())">+ Tabla en blanco</button>
            </div>
          </div>
          <p v-if="!form.tablas.length" class="prod-empty">Sin tablas de medidas.</p>
          <div v-for="(t, ti) in form.tablas" :key="'t' + ti" class="border border-surface-border rounded-lg p-2.5 mb-2 bg-surface-raised/40">
            <div class="flex items-center gap-2 mb-2 flex-wrap">
              <input v-model="t.name" placeholder="Nombre de la tabla" :disabled="disabled" class="field-input flex-1 min-w-[140px]" />
              <input v-model="t.unit" placeholder="Unidad (ej. cm)" :disabled="disabled" class="field-input w-28" />
              <button v-if="!disabled" type="button" class="del-btn" @click="form.tablas.splice(ti, 1)">✕</button>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-[13px]">
                <tbody>
                  <tr v-for="(r, ri) in t.rows" :key="r.id">
                    <td v-for="c in t.columns" :key="c" class="p-0.5"><input v-model="r.cells[c]" :disabled="disabled" class="field-input text-center" /></td>
                    <td class="p-0.5 w-6 text-center"><button v-if="!disabled && t.rows.length > 1" type="button" class="text-ink-muted hover:text-red-500" @click="t.rows.splice(ri, 1)">✕</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="flex items-center justify-between gap-2 mt-1.5 flex-wrap">
              <ParaTalleres v-model="t.proveedores" :talleres="p.talleres" :disabled="disabled" />
              <div v-if="!disabled" class="flex items-center gap-3">
                <button type="button" class="add-link" @click="agregarColumna(t)">+ Columna</button>
                <button v-if="t.columns.length > 1" type="button" class="add-link" @click="quitarColumna(t)">− Columna</button>
                <button type="button" class="add-link" @click="agregarFila(t)">+ Fila</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Diagramas / imágenes -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Diagramas / imágenes de referencia</p>
            <label v-if="!disabled" class="add-link cursor-pointer">
              {{ subiendo ? 'Subiendo…' : '+ Imagen / archivo' }}
              <input type="file" multiple accept="image/*,.pdf" class="hidden" :disabled="subiendo" @change="subir($event)" />
            </label>
          </div>
          <p v-if="!form.archivos.length" class="prod-empty">Sin imágenes ni archivos.</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div v-for="(a, i) in form.archivos" :key="'a' + i" class="flex gap-2 border border-surface-border rounded-lg p-2 bg-surface-raised/40">
              <a :href="a.archivo" target="_blank" class="shrink-0">
                <img v-if="esImagen(a.archivo)" :src="a.archivo" class="w-14 h-14 object-cover rounded border border-surface-border" alt="" />
                <span v-else class="w-14 h-14 flex items-center justify-center rounded border border-surface-border text-[10px] text-ink-muted">PDF</span>
              </a>
              <div class="flex-1 min-w-0 space-y-1">
                <input v-model="a.descripcion" placeholder="Descripción…" :disabled="disabled" class="field-input" />
                <div class="flex items-center justify-between gap-2">
                  <ParaTalleres v-model="a.proveedores" :talleres="p.talleres" :disabled="disabled" />
                  <button v-if="!disabled" type="button" class="del-btn" @click="form.archivos.splice(i, 1)">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <button type="button" :disabled="disabled || guardando" class="h-9 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="guardar(p)">
            {{ guardando ? 'Guardando…' : 'Guardar orden de manufactura' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { call, uploadFile } from "@/utils/frappe.js";
import ParaTalleres from "@/components/ParaTalleres.vue";

const props = defineProps({
  costeo: { type: String, required: true },
  medidasTemplates: { type: Array, default: () => [] },
  tablasDePlantilla: { type: Function, default: () => [] },
  showToast: { type: Function, default: () => {} },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);

const productos = ref([]);
const loading = ref(false);
const abierto = ref(null);
const form = ref(null);
const guardando = ref(false);
const subiendo = ref(false);
const checks = [
  { f: "om_bordado", label: "Bordado" }, { f: "om_estampado", label: "Estampado" },
  { f: "om_sublimado", label: "Sublimado" }, { f: "om_reflejante", label: "Reflejante" },
];

async function cargar() {
  if (!props.costeo) return;
  loading.value = true;
  try { productos.value = (await call("costeo_yelke.api.om_general.get_oms_generales", { costeo: props.costeo })).productos || []; }
  catch (e) { props.showToast(e.message || "No se pudieron cargar las órdenes de manufactura", "error"); }
  finally { loading.value = false; }
}
onMounted(cargar);
watch(() => props.costeo, cargar);

const total = (tallas) => (tallas || []).reduce((a, t) => a + (Number(t.cantidad) || 0), 0);
function tablaVacia() { return { name: `Tabla ${form.value.tablas.length + 1}`, unit: "", columns: ["c1", "c2"], rows: [{ id: "r1", cells: { c1: "", c2: "" } }], proveedores: [] }; }
function sigId(prefix, existentes) {
  let max = 0;
  for (const v of existentes) { const m = new RegExp(`^${prefix}(\\d+)$`).exec(String(v)); if (m) max = Math.max(max, +m[1]); }
  return `${prefix}${max + 1}`;
}
function agregarColumna(t) { const c = sigId("c", t.columns); t.columns.push(c); t.rows.forEach((r) => { r.cells[c] = ""; }); }
function quitarColumna(t) { const c = t.columns.pop(); t.rows.forEach((r) => { delete r.cells[c]; }); }
function agregarFila(t) { const cells = {}; t.columns.forEach((c) => { cells[c] = ""; }); t.rows.push({ id: sigId("r", t.rows.map((r) => r.id)), cells }); }
function agregarPlantilla(key) {
  if (!key) return;
  for (const t of props.tablasDePlantilla(key)) form.value.tablas.push({ ...t, proveedores: [] });
}
function toggle(p) {
  if (abierto.value === p.producto) { abierto.value = null; form.value = null; return; }
  const om = p.om ? JSON.parse(JSON.stringify(p.om)) : null;
  form.value = {
    general: om?.general || { om_bordado: 0, om_estampado: 0, om_sublimado: 0, om_reflejante: 0, om_aberturas: 0 },
    procesos: om?.procesos || [], observaciones: om?.observaciones || [],
    tablas: (om?.tablas || []).map((t) => ({ ...t, proveedores: t.proveedores || [] })), archivos: om?.archivos || [],
    name: om?.name || null,
  };
  abierto.value = p.producto;
}
const esImagen = (u) => /\.(png|jpe?g|gif|webp|svg|bmp)(\?.*)?$/i.test(u || "");
async function subir(ev) {
  const files = Array.from(ev.target.files || []);
  if (!files.length) return;
  subiendo.value = true;
  try {
    for (const f of files) {
      const res = await uploadFile(f, form.value.name ? { doctype: "Orden Manufactura", docname: form.value.name } : { doctype: "Costeo", docname: props.costeo });
      if (res?.file_url) form.value.archivos.push({ archivo: res.file_url, descripcion: res.file_name || "", proveedores: [] });
    }
    props.showToast("Archivo(s) subido(s). Recuerda guardar.");
  } catch (e) { props.showToast(e.message || "Error al subir", "error"); }
  finally { subiendo.value = false; ev.target.value = ""; }
}
async function guardar(p) {
  guardando.value = true;
  try {
    const r = await call("costeo_yelke.api.om_general.guardar_om_general", {
      costeo: props.costeo, producto: p.producto, datos: JSON.stringify(form.value),
    });
    form.value.name = r.name;
    await cargar();
    props.showToast("Orden de manufactura guardada — ya aparece en la orden de maquila de cada taller");
    emit("saved");
  } catch (e) { props.showToast(e.message || "No se pudo guardar", "error"); }
  finally { guardando.value = false; }
}
</script>
