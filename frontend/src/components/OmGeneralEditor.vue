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
        <!-- Información general (para todos): modelo, telas, qué lleva y aberturas -->
        <div>
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-2">Información general <span class="normal-case font-normal text-ink-light">· para todos los talleres</span></p>
          <div class="max-w-xl"><label class="field-label">Modelo de prenda</label><input v-model="form.general.om_modelo" :disabled="disabled" class="field-input" /></div>

          <!-- Telas: las del costeo (materiales marcados como «Tela»). La principal es la
               de mayor consumo y va resaltada; las demás son secundarias. -->
          <p class="field-label mt-3">Telas <span class="text-ink-light font-normal">· del costeo</span></p>
          <p v-if="!form.telas.length" class="prod-empty">El costeo de este producto no tiene materiales marcados como «Tela».</p>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-2">
            <div v-for="t in form.telas" :key="t.tela" class="rounded-lg p-2.5 ring-1" :class="t.principal ? 'ring-green-300 bg-green-50/60' : 'ring-surface-border bg-white'">
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <span class="text-[10.5px] font-semibold uppercase tracking-wider" :class="t.principal ? 'text-green-700' : 'text-ink-light'">{{ t.principal ? 'Tela principal' : 'Tela secundaria' }}</span>
                <span class="text-[10.5px] text-ink-light tabular-nums">{{ t.consumo }} {{ t.uom }} por prenda</span>
              </div>
              <div class="space-y-1.5">
                <div><label class="field-label">Nombre de la tela</label><input v-model="t.nombre" :disabled="disabled" class="field-input" /></div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
                  <div><label class="field-label">Composición</label><input v-model="t.composicion" :disabled="disabled" class="field-input" /></div>
                  <div><label class="field-label">Color</label><input v-model="t.color" :disabled="disabled" class="field-input" /></div>
                  <div><label class="field-label">Ubicación</label><input v-model="t.ubicacion" :disabled="disabled" class="field-input" /></div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-4 flex-wrap mt-3 text-[13px]">
            <label v-for="c in checks" :key="c.f" class="flex items-center gap-1.5"><input type="checkbox" v-model="form.general[c.f]" :true-value="1" :false-value="0" :disabled="disabled" class="accent-brand-500" />{{ c.label }}</label>
          </div>

          <!-- Aberturas: tantas como haga falta -->
          <div class="flex items-center justify-between mt-3 mb-1">
            <p class="field-label mb-0">Aberturas</p>
            <button v-if="!disabled" type="button" class="add-link" @click="form.aberturas.push({ numero: 1, ubicacion: '', descripcion: '' })">+ Abertura</button>
          </div>
          <p v-if="!form.aberturas.length" class="prod-empty">Sin aberturas.</p>
          <div v-for="(a, i) in form.aberturas" :key="'ab' + i" class="grid grid-cols-[90px_1fr_1fr_auto] gap-2 items-center mb-1.5">
            <input v-model.number="a.numero" type="number" min="0" placeholder="Número" :disabled="disabled" class="field-input tabular-nums" />
            <input v-model="a.ubicacion" placeholder="Ubicación" :disabled="disabled" class="field-input" />
            <input v-model="a.descripcion" placeholder="Descripción" :disabled="disabled" class="field-input" />
            <button v-if="!disabled" type="button" class="del-btn" @click="form.aberturas.splice(i, 1)">✕</button>
          </div>

          <!-- Bolsas: igual que las aberturas -->
          <div class="flex items-center justify-between mt-3 mb-1">
            <p class="field-label mb-0">Bolsas</p>
            <button v-if="!disabled" type="button" class="add-link" @click="form.bolsas.push({ numero: 1, ubicacion: '', descripcion: '' })">+ Bolsa</button>
          </div>
          <p v-if="!form.bolsas.length" class="prod-empty">Sin bolsas.</p>
          <div v-for="(a, i) in form.bolsas" :key="'bo' + i" class="grid grid-cols-[90px_1fr_1fr_auto] gap-2 items-center mb-1.5">
            <input v-model.number="a.numero" type="number" min="0" placeholder="Número" :disabled="disabled" class="field-input tabular-nums" />
            <input v-model="a.ubicacion" placeholder="Ubicación" :disabled="disabled" class="field-input" />
            <input v-model="a.descripcion" placeholder="Descripción" :disabled="disabled" class="field-input" />
            <button v-if="!disabled" type="button" class="del-btn" @click="form.bolsas.splice(i, 1)">✕</button>
          </div>
        </div>

        <!-- Tallas heredadas del costeo -->
        <div>
          <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Tallas <span class="normal-case font-normal text-ink-light">· de la orden de venta, para todos los talleres</span></p>
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
          <p class="text-[11px] text-ink-light mt-1">El desglose por talla se edita en la orden de venta (tallas regulares y tallas extra).</p>
        </div>

        <!-- Tejidos (cuellos, puños u otra pieza tejida): cada uno va a UN taller. Las
             medidas se dan por bloque (tallas base / tallas extra, por género) y el
             desglose por talla y la solicitud salen solos de las tallas de la OV. -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Tejidos <span class="normal-case font-normal text-ink-light">· cuellos, puños…</span></p>
            <button v-if="!disabled" type="button" class="add-link" @click="form.tejidos.push(tejidoVacio())">+ Tejido</button>
          </div>
          <p v-if="!form.tejidos.length" class="prod-empty">Sin tejidos.</p>
          <div v-for="(t, ti) in form.tejidos" :key="'tj' + ti" class="rounded-lg ring-1 ring-surface-border p-2.5 mb-2">
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-2">
              <div><label class="field-label">Número de hebras</label><input v-model="t.hebras" :disabled="disabled" class="field-input" placeholder="3" /></div>
              <div><label class="field-label">Tipo de tejido</label><input v-model="t.tipo_tejido" :disabled="disabled" class="field-input" placeholder="Tejido liso" /></div>
              <div><label class="field-label">Color</label><input v-model="t.color" :disabled="disabled" class="field-input" placeholder="Rojo" /></div>
              <div>
                <label class="field-label">Corresponde a</label>
                <select v-model="t.corresponde" :disabled="disabled" class="field-input">
                  <option>Cuellos y puños</option><option>Cuellos</option><option>Puños</option><option>Otro</option>
                </select>
              </div>
              <div v-if="t.corresponde === 'Otro'"><label class="field-label">¿Qué pieza?</label><input v-model="t.otro" :disabled="disabled" class="field-input" /></div>
              <div>
                <label class="field-label">Taller</label>
                <select v-model="t.proveedor" :disabled="disabled" class="field-input">
                  <option value="">— Elige el taller —</option>
                  <option v-for="w in p.talleres" :key="w" :value="w">{{ w }}</option>
                </select>
              </div>
            </div>

            <!-- Medidas por bloque -->
            <div class="overflow-x-auto mt-2">
              <table class="text-[12px] w-full">
                <thead><tr class="text-[10.5px] text-ink-light text-left">
                  <th class="pr-2 font-medium">Medida</th>
                  <th v-for="b in bloquesMedida(p)" :key="b.k" class="pr-2 font-medium">{{ b.label }}</th>
                </tr></thead>
                <tbody>
                  <tr v-for="pz in piezasTejido(t)" :key="pz">
                    <td class="pr-2 py-0.5 text-ink whitespace-nowrap">{{ pz }}</td>
                    <td v-for="b in bloquesMedida(p)" :key="b.k" class="pr-2 py-0.5">
                      <input :value="medida(t, pz, b.k)" @input="setMedida(t, pz, b.k, $event.target.value)" :disabled="disabled" class="field-input" placeholder="40*8.5 cm" />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Imagen de referencia -->
            <div class="flex items-center gap-2 mt-2">
              <a v-if="t.imagen" :href="t.imagen" target="_blank"><img :src="t.imagen" class="w-14 h-14 object-cover rounded border border-surface-border" alt="" /></a>
              <label v-if="!disabled" class="add-link cursor-pointer">
                {{ t.imagen ? 'Cambiar imagen' : '+ Imagen de referencia' }}
                <input type="file" accept="image/*" class="hidden" @change="subirImagenTejido($event, t)" />
              </label>
              <button v-if="!disabled && t.imagen" type="button" class="del-btn" @click="t.imagen = ''">Quitar</button>
              <span class="flex-1"></span>
              <button v-if="!disabled" type="button" class="del-btn" @click="form.tejidos.splice(ti, 1)">✕ Quitar tejido</button>
            </div>

            <!-- Vista previa: desglose y solicitud (igual que en la orden impresa) -->
            <div v-for="g in desgloseTejido(t, p)" :key="g.genero" class="mt-2 rounded-md bg-surface-raised/50 p-2">
              <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">{{ g.genero }}</p>
              <div class="flex flex-wrap gap-3 mt-1">
                <div v-for="b in g.bloques.filter(b => b.tallas.length)" :key="b.clave" class="text-[11.5px]">
                  <span class="text-ink-light">{{ b.titulo }}:</span>
                  <span v-for="x in b.tallas" :key="x.talla" class="ml-1.5 tabular-nums">{{ x.talla }} {{ fmtN(x.cantidad) }}</span>
                  <span class="ml-1.5 font-semibold tabular-nums">= {{ fmtN(b.subtotal) }}</span>
                </div>
              </div>
              <ul class="mt-1 text-[11.5px]">
                <li v-for="l in g.solicitud" :key="l.texto" class="flex justify-between max-w-md"><span>{{ l.texto }}</span><b class="tabular-nums">{{ fmtN(l.cantidad) }}</b></li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Procesos -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Procesos</p>
            <button v-if="!disabled" type="button" class="add-link" @click="form.procesos.push({ nombre_proceso: '', ubicacion: '', colores: '', descripcion: '', medida: '', proveedores: [] })">+ Proceso</button>
          </div>
          <p v-if="!form.procesos.length" class="prod-empty">Sin procesos.</p>
          <div v-for="(r, i) in form.procesos" :key="'p' + i" class="rounded-lg ring-1 ring-surface-border p-2 mb-1.5">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-1.5">
              <input v-model="r.nombre_proceso" placeholder="Nombre del proceso" :disabled="disabled" class="field-input" />
              <input v-model="r.ubicacion" placeholder="Ubicación" :disabled="disabled" class="field-input" />
              <input v-model="r.colores" placeholder="Colores" :disabled="disabled" class="field-input" />
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-[1fr_160px] gap-2 mb-1.5">
              <textarea v-model="r.descripcion" rows="1" placeholder="Descripción del proceso" :disabled="disabled" class="field-input"></textarea>
              <input v-model="r.medida" placeholder="Medida" :disabled="disabled" class="field-input" />
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
                    <!-- Una celda puede llevar texto o una IMAGEN: se pega con Ctrl+V
                         encima del campo (un diagrama por renglón de la tabla de medidas). -->
                    <td v-for="c in t.columns" :key="c" class="p-0.5">
                      <div v-if="esImagen(r.cells[c])" class="relative inline-block">
                        <a :href="r.cells[c]" target="_blank">
                          <img :src="r.cells[c]" class="h-12 max-w-[96px] object-contain rounded border border-surface-border bg-white" alt="" />
                        </a>
                        <button
                          v-if="!disabled" type="button" title="Quitar la imagen de esta celda"
                          class="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-white border border-surface-border text-[9px] leading-none text-ink-muted hover:text-red-500"
                          @click="r.cells[c] = ''"
                        >✕</button>
                      </div>
                      <input
                        v-else v-model="r.cells[c]" :disabled="disabled" class="field-input text-center"
                        title="Escribe un valor, o pega una imagen con Ctrl+V"
                        @paste="pegarEnCelda($event, r, c)"
                      />
                    </td>
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

        <!-- Diagramas / imágenes. Se puede soltar o pegar (Ctrl+V) sobre esta zona:
             es como llega la mayoría de los planos, de una captura o de una carpeta. -->
        <div
          @dragover.prevent="arrastrando = true" @dragenter.prevent="arrastrando = true"
          @dragleave="arrastrando = false" @drop.prevent="soltar($event)"
        >
          <div class="flex items-center justify-between mb-1">
            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Diagramas / imágenes de referencia</p>
            <label v-if="!disabled" class="add-link cursor-pointer">
              {{ subiendo ? 'Subiendo…' : '+ Imagen / PDF' }}
              <input type="file" multiple :accept="ACCEPT" class="hidden" :disabled="subiendo" @change="subir($event)" />
            </label>
          </div>
          <div
            class="rounded-lg border border-dashed px-3 py-2 mb-2 text-[11px] transition-colors"
            :class="arrastrando ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-surface-border text-ink-light'"
          >
            {{ arrastrando ? 'Suelta aquí los archivos' : 'Arrastra archivos aquí o pégalos con Ctrl+V. Solo imágenes (PNG, JPG, GIF, WEBP, BMP) y PDF — los PDF se unen al final de la ficha impresa, como hojas aparte.' }}
          </div>
          <p v-if="!form.archivos.length" class="prod-empty">Sin imágenes ni archivos.</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div v-for="(a, i) in form.archivos" :key="'a' + i" class="flex gap-2 border border-surface-border rounded-lg p-2 bg-surface-raised/40">
              <a :href="a.archivo" target="_blank" class="shrink-0">
                <img v-if="esImagen(a.archivo)" :src="a.archivo" class="w-14 h-14 object-cover rounded border border-surface-border" alt="" />
                <span v-else class="w-14 h-14 flex flex-col items-center justify-center rounded border border-surface-border text-[10px] text-ink-muted leading-tight">
                  <b>PDF</b><span class="text-[8.5px]">anexo</span>
                </span>
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
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { call, uploadFile } from "@/utils/frappe.js";
import ParaTalleres from "@/components/ParaTalleres.vue";

const props = defineProps({
  costeo: { type: String, required: true },
  // OV activa: la ficha es la misma para todas las OV del costeo, pero las tallas
  // que se muestran (y que se le imprimen al taller) son las de esta.
  salesOrder: { type: String, default: "" },
  medidasTemplates: { type: Array, default: () => [] },
  tablasDePlantilla: { type: Function, default: () => [] },
  showToast: { type: Function, default: () => {} },
  disabled: { type: Boolean, default: false },
});
// `cargado` lleva al menú de Producción cuántas fichas están capturadas (n/total).
const emit = defineEmits(["saved", "cargado"]);

const productos = ref([]);
const loading = ref(false);
const abierto = ref(null);
const form = ref(null);
const guardando = ref(false);
const subiendo = ref(false);
const checks = [
  { f: "om_bordado", label: "Bordado" }, { f: "om_estampado", label: "Estampado" },
  { f: "om_sublimado", label: "Sublimado" }, { f: "om_reflejante", label: "Reflejante" },
  { f: "om_dtf", label: "DTF" }, { f: "om_vinil", label: "Vinil" },
];

async function cargar() {
  if (!props.costeo) return;
  loading.value = true;
  try {
    productos.value = (await call("costeo_yelke.api.om_general.get_oms_generales", {
      costeo: props.costeo, sales_order: props.salesOrder || null,
    })).productos || [];
    emit("cargado", {
      total: productos.value.length,
      capturadas: productos.value.filter((p) => p.om).length,
    });
  }
  catch (e) { props.showToast(e.message || "No se pudieron cargar las órdenes de manufactura", "error"); }
  finally { loading.value = false; }
}
onMounted(cargar);
watch(() => [props.costeo, props.salesOrder], cargar);

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
    general: om?.general || { om_modelo: p.modelo || p.item_name, om_bordado: 0, om_estampado: 0, om_sublimado: 0, om_reflejante: 0, om_dtf: 0, om_vinil: 0 },
    // Las telas salen siempre del costeo (con lo ya capturado de cada una).
    telas: JSON.parse(JSON.stringify(om?.telas || p.telas || [])),
    aberturas: om?.aberturas || [],
    bolsas: om?.bolsas || [],
    tejidos: (om?.tejidos || []).map((t) => ({ ...t, medidas: t.medidas || {}, proveedor: t.proveedor || "" })),
    procesos: om?.procesos || [], observaciones: om?.observaciones || [],
    tablas: (om?.tablas || []).map((t) => ({ ...t, proveedores: t.proveedores || [] })), archivos: om?.archivos || [],
    name: om?.name || null,
  };
  abierto.value = p.producto;
}
const esImagen = (u) => /\.(png|jpe?g|gif|webp|svg|bmp)(\?.*)?$/i.test(u || "");
// Lo único que el formato sabe imprimir: la imagen entra en la galería y el PDF se
// une al final como hojas aparte. Un .docx o un .xlsx habría que convertirlos, así
// que se rechazan aquí y el backend lo vuelve a validar (impresion.validar_adjuntos_om).
const EXT_IMG = ["png", "jpg", "jpeg", "gif", "webp", "bmp"];
const EXT_OK = [...EXT_IMG, "pdf"];
const ACCEPT = EXT_OK.map((e) => "." + e).join(",");
const arrastrando = ref(false);

const ext = (n) => (n || "").split("?")[0].split(".").pop().toLowerCase();
async function subirUno(file) {
  const res = await uploadFile(file, form.value.name
    ? { doctype: "Orden Manufactura", docname: form.value.name }
    : { doctype: "Costeo", docname: props.costeo });
  return res?.file_url || null;
}
// Una captura pegada del portapapeles suele llegar sin nombre (o como "image.png"):
// se le pone uno con extensión para que el servidor la acepte y se vea qué es.
function conNombre(file) {
  if (EXT_OK.includes(ext(file.name))) return file;
  const tipo = (file.type || "").split("/")[1] || "png";
  return new File([file], `pegado-${Date.now()}.${tipo === "jpeg" ? "jpg" : tipo}`, { type: file.type });
}
// Pegar una imagen DENTRO de una celda de la tabla de medidas. El pegado de texto
// se deja pasar tal cual: ahí manda el navegador.
async function pegarEnCelda(ev, fila, columna) {
  if (props.disabled) return;
  const img = Array.from(ev.clipboardData?.files || []).find((f) => /^image\//.test(f.type) || EXT_IMG.includes(ext(f.name)));
  if (!img) return;
  ev.preventDefault();
  ev.stopPropagation();
  subiendo.value = true;
  try {
    const url = await subirUno(conNombre(img));
    if (url) { fila.cells[columna] = url; props.showToast("Imagen pegada en la celda. Recuerda guardar."); }
  } catch (e) { props.showToast(e.message || "No se pudo pegar la imagen", "error"); }
  finally { subiendo.value = false; }
}

async function subirArchivos(files) {
  const lista = Array.from(files || []).filter(Boolean);
  if (!lista.length) return;
  const buenos = lista.filter((f) => EXT_OK.includes(ext(f.name)));
  const malos = lista.filter((f) => !EXT_OK.includes(ext(f.name)));
  if (malos.length) {
    props.showToast(`Solo imágenes o PDF — conviértelo antes de subirlo: ${malos.map((f) => f.name).join(", ")}`, "error");
  }
  if (!buenos.length) return;
  subiendo.value = true;
  try {
    for (const f of buenos) {
      const url = await subirUno(f);
      if (url) form.value.archivos.push({ archivo: url, descripcion: f.name || "", proveedores: [] });
    }
    props.showToast(`${buenos.length} archivo(s) subido(s). Recuerda guardar.`);
  } catch (e) { props.showToast(e.message || "Error al subir", "error"); }
  finally { subiendo.value = false; }
}
async function subir(ev) {
  await subirArchivos(ev.target.files);
  ev.target.value = "";
}
async function soltar(ev) {
  arrastrando.value = false;
  if (props.disabled || !form.value) return;
  await subirArchivos(ev.dataTransfer?.files);
}
// Pegar (Ctrl+V) una captura o un archivo del explorador. Solo actúa con una ficha
// abierta y editable, y nunca cuando se está escribiendo en un campo: ahí el pegado
// es texto y le toca al navegador.
async function pegar(ev) {
  if (props.disabled || !abierto.value || !form.value) return;
  const activo = document.activeElement;
  if (activo && /^(INPUT|TEXTAREA)$/.test(activo.tagName)) return;
  const files = Array.from(ev.clipboardData?.files || []);
  if (!files.length) return;
  ev.preventDefault();
  await subirArchivos(files);
}
onMounted(() => document.addEventListener("paste", pegar));
onBeforeUnmount(() => document.removeEventListener("paste", pegar));
// ── Tejidos ───────────────────────────────────────────────────────────────────
// Mismo cálculo que om_general.desglose_tejido (el que usa el impreso): tallas del
// producto base = bloque «base», las de sus variantes = bloque «extra», por género.
const fmtN = (n) => Number(n || 0).toLocaleString("es-MX");
function tejidoVacio() { return { hebras: "", tipo_tejido: "", color: "", corresponde: "Cuellos y puños", otro: "", medidas: {}, proveedor: "", imagen: "" }; }
function piezasTejido(t) {
  if (t.corresponde === "Otro") return [(t.otro || "Otro").trim() || "Otro"];
  return { "Cuellos": ["Cuellos"], "Puños": ["Puños"] }[t.corresponde] || ["Cuellos", "Puños"];
}
function generosDe(p) {
  const gs = [];
  for (const f of p.tallas || []) { const g = f.genero || "Sin género"; if (!gs.includes(g)) gs.push(g); }
  return gs;
}
function bloquesMedida(p) {
  const out = [];
  for (const g of generosDe(p)) {
    for (const [k, l] of [["base", "tallas base"], ["extra", "tallas extra"]]) {
      if ((p.tallas || []).some((f) => (f.genero || "Sin género") === g && ((f.producto || p.producto) === p.producto) === (k === "base"))) {
        out.push({ k: `${g}|${k}`, label: `${g} · ${l}` });
      }
    }
  }
  // Sin tallas todavía (sin orden de venta): los cuatro bloques de siempre.
  if (!out.length) for (const g of ["Caballero", "Dama"]) for (const [k, l] of [["base", "tallas base"], ["extra", "tallas extra"]]) out.push({ k: `${g}|${k}`, label: `${g} · ${l}` });
  return out;
}
const medida = (t, pz, k) => (t.medidas?.[pz] || {})[k] || "";
function setMedida(t, pz, k, v) { t.medidas = { ...(t.medidas || {}), [pz]: { ...((t.medidas || {})[pz] || {}), [k]: v } }; }
function desgloseTejido(t, p) {
  const out = [];
  for (const g of generosDe(p)) {
    const bloques = [["base", "Tallas base"], ["extra", "Tallas extra"]].map(([clave, titulo]) => {
      const tallas = [];
      for (const f of p.tallas || []) {
        if ((f.genero || "Sin género") !== g || ((f.producto || p.producto) === p.producto) !== (clave === "base")) continue;
        const x = tallas.find((y) => y.talla === f.talla);
        if (x) x.cantidad += Number(f.cantidad) || 0; else tallas.push({ talla: f.talla, cantidad: Number(f.cantidad) || 0 });
      }
      return { clave, titulo, tallas, subtotal: tallas.reduce((a, x) => a + x.cantidad, 0) };
    });
    if (!bloques.some((b) => b.tallas.length)) continue;
    const solicitud = [];
    for (const pz of piezasTejido(t)) {
      const porMedida = new Map();
      for (const b of bloques) {
        const m = medida(t, pz, `${g}|${b.clave}`);
        if (!b.tallas.length && !m) continue;
        porMedida.set(m, (porMedida.get(m) || 0) + b.subtotal);
      }
      for (const [m, n] of porMedida) {
        const nombre = pz === "Puños" ? `Pares de puños ${g.toLowerCase()}` : `${pz} ${g.toLowerCase()}`;
        solicitud.push({ texto: `${nombre}${m ? " medida " + m : ""}`, cantidad: n });
      }
    }
    out.push({ genero: g, bloques, solicitud });
  }
  return out;
}
async function subirImagenTejido(ev, t) {
  const f = ev.target.files?.[0];
  ev.target.value = "";
  if (!f) return;
  subiendo.value = true;
  try { const url = await subirUno(conNombre(f)); if (url) { t.imagen = url; props.showToast("Imagen agregada. Recuerda guardar."); } }
  catch (e) { props.showToast(e.message || "No se pudo subir la imagen", "error"); }
  finally { subiendo.value = false; }
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
