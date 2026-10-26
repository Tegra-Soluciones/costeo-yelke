<!--
  "Al terminar, entregar a" de una orden a taller (api/entregas_taller.py): a quién
  manda el taller cada pieza al terminar, con su dirección. Sale del flujo de
  producción; se puede apagar (no se imprime) o corregir a mano. No mueve inventario:
  es la instrucción que viaja en la orden de maquila.
-->
<template>
  <div class="rounded-xl border border-surface-border px-4 py-3 mb-4">
    <div class="flex items-center justify-between gap-2 mb-2">
      <p class="p-eyebrow">Al terminar, entregar a</p>
      <span v-if="d && d.indicar && !editando" class="text-[11px]" :class="d.editadas ? 'text-amber-700' : 'text-ink-light'">
        {{ d.editadas ? "Editado a mano" : "Del flujo de producción" }}
      </span>
    </div>
    <p v-if="!d" class="p-meta">Cargando…</p>
    <template v-else>
      <label class="flex items-start gap-2.5 cursor-pointer">
        <input type="checkbox" class="mt-0.5 accent-brand-500" :checked="d.indicar" :disabled="ocupado || editando" @change="cambiarIndicar($event.target.checked)" />
        <span>
          <span class="block text-[13px] font-medium text-ink">Indicarlo en la orden de maquila</span>
          <span class="block text-[11.5px] text-ink-muted">El taller manda cada pieza directo a quien sigue. El sistema no cambia: se recibe y se transfiere igual.</span>
        </span>
      </label>

      <!-- Lectura -->
      <template v-if="d.indicar && !editando">
        <p v-if="!d.filas.length" class="p-meta mt-3">No se pudo deducir del flujo. Captúralo a mano.</p>
        <ul v-else class="mt-3 divide-y divide-surface-border rounded-lg border border-surface-border">
          <li v-for="(f, i) in d.filas" :key="i" class="px-3 py-2">
            <p class="text-[12.5px] text-ink"><span class="font-medium">{{ f.piezas || "—" }}</span>
              <span v-if="varios && f.producto" class="text-ink-light"> · {{ d.nombres[f.producto] || f.producto }}</span></p>
            <p class="text-[12.5px] text-brand-700 font-medium mt-0.5">→ {{ f.destino || "—" }}</p>
            <p v-if="f.entregar_a && f.entregar_a === d.supplier" class="text-[11.5px] text-ink-muted">Se queda en este taller para el siguiente paso</p>
            <p v-else-if="f.direccion" class="text-[11.5px] text-ink-muted whitespace-pre-line">{{ f.direccion }}</p>
          </li>
        </ul>
        <div class="flex gap-2 mt-2.5">
          <button type="button" class="p-btn-secondary h-8 text-[12px]" :disabled="ocupado" @click="editar">Editar</button>
          <button v-if="d.editadas" type="button" class="p-btn-ghost h-8 text-[12px]" :disabled="ocupado" @click="volverAlFlujo">Volver a lo del flujo</button>
        </div>
      </template>

      <!-- Edición -->
      <template v-if="d.indicar && editando">
        <div class="mt-3 space-y-2.5">
          <div v-for="(f, i) in borrador" :key="i" class="rounded-lg border border-surface-border p-2.5 space-y-2">
            <div class="flex items-center gap-2">
              <input v-model="f.piezas" class="p-field flex-1" placeholder="Piezas (ej. Frente, Espalda)" />
              <button type="button" class="p-btn-ghost h-8 px-2 text-[12px] text-red-700" title="Quitar" @click="borrador.splice(i, 1)">Quitar</button>
            </div>
            <LinkInput :model-value="f.entregar_a || ''" doctype="Supplier" placeholder="Taller que recibe (vacío = almacén de Yelke)" @update:model-value="(v) => cambiarTaller(f, v)" />
            <input v-model="f.destino" class="p-field" placeholder="Entregar a (nombre que se imprime)" />
            <textarea v-model="f.direccion" rows="3" class="p-field" placeholder="Dirección" />
          </div>
          <button type="button" class="p-btn-ghost h-8 text-[12px]" @click="borrador.push({ producto: '', piezas: '', entregar_a: '', destino: '', direccion: '' })">+ Agregar destino</button>
        </div>
        <div class="flex gap-2 mt-2.5">
          <button type="button" class="p-btn-primary h-8 text-[12px]" :disabled="ocupado" @click="guardar">Guardar</button>
          <button type="button" class="p-btn-secondary h-8 text-[12px]" :disabled="ocupado" @click="editando = false">Cancelar</button>
        </div>
      </template>
      <p v-if="error" class="text-[12px] text-red-700 mt-2">{{ error }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import LinkInput from "@/components/LinkInput.vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({ po: { type: String, required: true } });
const API = "costeo_yelke.api.entregas_taller";
const d = ref(null);
const editando = ref(false);
const borrador = ref([]);
const ocupado = ref(false);
const error = ref("");
const varios = computed(() => new Set((d.value?.filas || []).map((f) => f.producto).filter(Boolean)).size > 1);

async function cargar() {
  error.value = "";
  editando.value = false;
  try { d.value = await call(`${API}.get_entregas`, { po: props.po }); }
  catch (e) { error.value = e.message || "No se pudo leer la entrega."; d.value = { indicar: false, filas: [], nombres: {} }; }
}
watch(() => props.po, () => { d.value = null; cargar(); }, { immediate: true });

async function enviar(indicar, filas) {
  ocupado.value = true;
  error.value = "";
  try {
    d.value = await call(`${API}.guardar_entregas`, { po: props.po, indicar: indicar ? 1 : 0, filas: filas ? JSON.stringify(filas) : null });
    editando.value = false;
  } catch (e) { error.value = e.message || "No se pudo guardar."; }
  finally { ocupado.value = false; }
}
// Apagar/encender no toca lo capturado a mano.
const cambiarIndicar = (v) => enviar(v, d.value.editadas ? d.value.filas : null);
const volverAlFlujo = () => enviar(true, null);
const guardar = () => enviar(true, borrador.value);

function editar() {
  borrador.value = d.value.filas.map((f) => ({ ...f }));
  editando.value = true;
}
async function cambiarTaller(f, v) {
  f.entregar_a = v;
  if (!v) return;
  try {
    const r = await call(`${API}.direccion_de_proveedor`, { supplier: v });
    f.destino = r.destino;
    f.direccion = r.direccion;
  } catch { /* se captura a mano */ }
}
</script>
