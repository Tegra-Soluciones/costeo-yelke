<!--
  Elegir la imagen de un producto, como el cargador de archivos de ERPNext: desde el
  equipo (botón o arrastrar), pegada del portapapeles (Ctrl/Cmd+V) o desde un enlace.
  El enlace se descarga en el servidor (api/imagenes.py) y queda como archivo propio,
  no como liga externa que se pueda caer.
-->
<template>
  <Teleport to="body">
    <div v-if="abierto" class="fixed inset-0 z-[70] bg-black/30 flex items-end sm:items-center justify-center" @click.self="cerrar">
      <div class="w-full sm:max-w-[480px] bg-white rounded-t-[22px] sm:rounded-2xl shadow-xl flex flex-col max-h-[90vh]" style="padding-bottom: max(18px, env(safe-area-inset-bottom))" @paste="alPegar">
        <div class="w-9 h-1 rounded-full bg-zinc-300 mx-auto mt-2 mb-1 sm:hidden"></div>
        <div class="px-5 pt-3 pb-3">
          <p class="text-[17px] font-semibold">Imagen del producto</p>
          <p class="p-meta mt-0.5 leading-snug">{{ producto }}</p>
        </div>

        <div class="overflow-y-auto px-5 space-y-4">
          <div
            class="rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-2 px-4 py-5 text-center transition-colors"
            :class="arrastrando ? 'border-brand-400 bg-brand-50' : 'border-surface-border bg-surface-raised/40'"
            @dragover.prevent="arrastrando = true" @dragleave.prevent="arrastrando = false" @drop.prevent="alSoltar"
          >
            <img v-if="actual" :src="actual" class="w-28 h-28 object-cover rounded-lg border border-surface-border bg-white" alt="" />
            <p class="text-[13px] text-ink-muted leading-snug">
              Arrastra una imagen aquí o pégala con <kbd class="px-1 rounded border border-surface-border text-[11px]">Ctrl</kbd>+<kbd class="px-1 rounded border border-surface-border text-[11px]">V</kbd>
            </p>
            <button type="button" class="p-btn-secondary h-9 px-4" :disabled="ocupado" @click="elegirArchivo">Elegir del equipo</button>
          </div>

          <div>
            <label class="text-[12px] font-medium text-ink-muted block mb-1">O pega el enlace de una imagen</label>
            <div class="flex gap-2">
              <input
                ref="caja" v-model="enlace" type="url" inputmode="url" placeholder="https://…/imagen.jpg"
                class="flex-1 min-w-0 text-[14px] border border-surface-border rounded-lg px-3 h-10 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/25 focus:border-brand-400"
                :disabled="ocupado" @keydown.enter.prevent="usarEnlace"
              />
              <button type="button" class="p-btn h-10 px-4 text-white bg-brand-500 hover:bg-brand-600" :disabled="ocupado || !enlace.trim()" @click="usarEnlace">Usar</button>
            </div>
            <p class="text-[11px] text-ink-light mt-1">La imagen se descarga y se guarda en el sistema, no depende del sitio de origen.</p>
          </div>

          <p v-if="ocupado" class="text-[12.5px] text-ink-muted">Subiendo la imagen…</p>
          <p v-if="error" class="text-[12.5px] text-red-700">{{ error }}</p>
        </div>

        <div class="px-5 pt-4 flex gap-2">
          <button v-if="actual" type="button" class="p-btn-secondary h-12 sm:h-10 px-4 text-red-700" :disabled="ocupado" @click="emit('elegida', '')">Quitar imagen</button>
          <button type="button" class="p-btn-secondary h-12 sm:h-10 flex-1" :disabled="ocupado" @click="cerrar">Cerrar</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";
import { call, uploadFile } from "@/utils/frappe.js";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  producto: { type: String, default: "" },
  actual: { type: String, default: "" },
  // A qué documento queda adjunta la imagen (vacío si el costeo aún no se guarda).
  doctype: { type: String, default: "" },
  docname: { type: String, default: "" },
});
const emit = defineEmits(["cerrar", "elegida"]);

const enlace = ref("");
const error = ref("");
const ocupado = ref(false);
const arrastrando = ref(false);
const caja = ref(null);

watch(() => props.abierto, async (v) => {
  if (!v) return;
  enlace.value = ""; error.value = ""; ocupado.value = false; arrastrando.value = false;
  await nextTick();
  caja.value?.focus();
});

function cerrar() { if (!ocupado.value) emit("cerrar"); }

const destino = () => (props.doctype && props.docname ? { doctype: props.doctype, docname: props.docname } : {});

async function subir(archivo) {
  if (!archivo) return;
  if (!archivo.type.startsWith("image/")) { error.value = "Ese archivo no es una imagen."; return; }
  ocupado.value = true; error.value = "";
  try {
    const res = await uploadFile(archivo, destino());
    if (res?.file_url) emit("elegida", res.file_url);
  } catch (e) { error.value = e.message || "No se pudo subir la imagen."; }
  finally { ocupado.value = false; }
}

function elegirArchivo() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = (ev) => subir(ev.target.files?.[0]);
  input.click();
}

function alSoltar(ev) {
  arrastrando.value = false;
  const archivo = ev.dataTransfer?.files?.[0];
  if (archivo) return subir(archivo);
  // Arrastrar una imagen desde otra pestaña del navegador trae su enlace, no el archivo.
  const url = ev.dataTransfer?.getData("text/uri-list") || ev.dataTransfer?.getData("text/plain");
  if (url) { enlace.value = url.trim(); usarEnlace(); }
}

function alPegar(ev) {
  const archivo = [...(ev.clipboardData?.files || [])].find(f => f.type.startsWith("image/"));
  if (archivo) { ev.preventDefault(); subir(archivo); }
  // Si lo pegado es texto, cae solo en la caja del enlace.
}

async function usarEnlace() {
  const url = enlace.value.trim();
  if (!url || ocupado.value) return;
  ocupado.value = true; error.value = "";
  try {
    const res = await call("costeo_yelke.api.imagenes.imagen_desde_enlace", { url, ...destino() });
    if (res?.file_url) emit("elegida", res.file_url);
  } catch (e) { error.value = e.message || "No se pudo usar ese enlace."; }
  finally { ocupado.value = false; }
}
</script>
