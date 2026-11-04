<!--
  Fotos (la prenda) y adjuntos de una asignación (api/encargos.get_archivos /
  subir_archivo / quitar_archivo). Dos modos:
    con `encargo`   lista lo que tiene y sube al momento
    sin `encargo`   (al asignar) junta los archivos en `modelValue`; quien crea la
                    asignación los sube después con subirArchivosAsignacion().
-->
<template>
  <div class="space-y-4">
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <p class="p-field-label !mb-0">Fotos <span class="text-ink-light font-normal">(la prenda, detalles)</span></p>
        <button v-if="editable" type="button" class="text-[12.5px] font-medium text-brand-600 disabled:opacity-50" :disabled="subiendo" @click="elegir(true)">+ Agregar fotos</button>
      </div>
      <p v-if="!fotos.length" class="text-[12px] text-ink-light">{{ cargando ? "Cargando…" : "Sin fotos." }}</p>
      <div v-else class="grid grid-cols-3 sm:grid-cols-4 gap-2">
        <div v-for="a in fotos" :key="a.key" class="relative aspect-square rounded-lg overflow-hidden bg-surface-raised border border-surface-border">
          <a :href="a.url" target="_blank" rel="noopener"><img :src="a.url" :alt="a.nombre" class="w-full h-full object-cover" loading="lazy" /></a>
          <button v-if="editable && a.puedeQuitar" type="button" class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/55 text-white text-[13px] leading-none flex items-center justify-center" title="Quitar" @click="quitar(a)">×</button>
        </div>
      </div>
    </div>
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <p class="p-field-label !mb-0">Adjuntos</p>
        <button v-if="editable" type="button" class="text-[12.5px] font-medium text-brand-600 disabled:opacity-50" :disabled="subiendo" @click="elegir(false)">+ Adjuntar archivo</button>
      </div>
      <p v-if="!docs.length" class="text-[12px] text-ink-light">{{ cargando ? "Cargando…" : "Sin adjuntos." }}</p>
      <ul v-else class="space-y-1.5">
        <li v-for="a in docs" :key="a.key" class="flex items-center gap-2 bg-surface-raised rounded-lg px-3 py-2 text-[12.5px]">
          <a :href="a.url" target="_blank" rel="noopener" class="truncate flex-1 text-brand-700 hover:underline">{{ a.nombre }}</a>
          <button v-if="editable && a.puedeQuitar" type="button" class="text-ink-light hover:text-red-600" @click="quitar(a)">Quitar</button>
        </li>
      </ul>
    </div>
    <p v-if="subiendo" class="text-[12px] text-ink-muted">Subiendo…</p>
    <p v-if="error" class="text-[12px] text-red-700">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { call, uploadToMethod } from "@/utils/frappe.js";

const props = defineProps({
  encargo: { type: String, default: "" },
  modelValue: { type: Array, default: () => [] },   // File[] pendientes (sin encargo)
  editable: { type: Boolean, default: true },
});
const emit = defineEmits(["update:modelValue"]);

const IMG = /\.(jpe?g|png|gif|webp|heic|heif|bmp)$/i;
const remotos = ref([]);
const cargando = ref(false);
const subiendo = ref(false);
const error = ref("");
const previas = new Map();   // File -> object URL

const urlLocal = (f) => { if (!previas.has(f)) previas.set(f, URL.createObjectURL(f)); return previas.get(f); };
onBeforeUnmount(() => previas.forEach((u) => URL.revokeObjectURL(u)));

const todos = computed(() => (props.encargo
  ? remotos.value.map((a) => ({ key: a.name, nombre: a.file_name, url: a.file_url, foto: a.es_foto, puedeQuitar: true, remoto: a }))
  : props.modelValue.map((f, i) => ({ key: `${i}-${f.name}`, nombre: f.name, url: urlLocal(f), foto: (f.type || "").startsWith("image/") || IMG.test(f.name), puedeQuitar: true, local: f }))));
const fotos = computed(() => todos.value.filter((a) => a.foto));
const docs = computed(() => todos.value.filter((a) => !a.foto));

async function cargar() {
  if (!props.encargo) { remotos.value = []; return; }
  cargando.value = true; error.value = "";
  try { remotos.value = await call("costeo_yelke.api.encargos.get_archivos", { name: props.encargo }); }
  catch (e) { error.value = e.message || "No se pudieron cargar los archivos."; }
  finally { cargando.value = false; }
}
watch(() => props.encargo, cargar, { immediate: true });

function elegir(soloFotos) {
  const input = document.createElement("input");
  input.type = "file"; input.multiple = true;
  if (soloFotos) input.accept = "image/*";
  input.onchange = async () => {
    const files = [...(input.files || [])];
    if (!files.length) return;
    if (!props.encargo) { emit("update:modelValue", [...props.modelValue, ...files]); return; }
    subiendo.value = true; error.value = "";
    try { for (const f of files) await uploadToMethod("costeo_yelke.api.encargos.subir_archivo", f, { name: props.encargo }); }
    catch (e) { error.value = e.message || "No se pudo subir."; }
    finally { subiendo.value = false; await cargar(); }
  };
  input.click();
}

async function quitar(a) {
  if (a.local) { emit("update:modelValue", props.modelValue.filter((f) => f !== a.local)); return; }
  error.value = "";
  try { await call("costeo_yelke.api.encargos.quitar_archivo", { name: props.encargo, archivo: a.remoto.name }); await cargar(); }
  catch (e) { error.value = e.message || "No se pudo quitar."; }
}
</script>
