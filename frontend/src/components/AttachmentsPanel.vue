<template>
  <div>
    <div class="flex items-center justify-between mb-2">
      <p class="field-label mb-0">Adjuntos</p>
      <button
        :disabled="uploading || !docname"
        class="text-xs font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1 disabled:opacity-50"
        @click="pickAndUpload"
      >
        <svg v-if="uploading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
        {{ uploading ? "Subiendo…" : "Adjuntar archivo" }}
      </button>
    </div>

    <p v-if="!docname" class="text-xs text-ink-light">Guarda primero para poder adjuntar archivos.</p>
    <div v-else-if="loading" class="text-xs text-ink-light">Cargando…</div>
    <p v-else-if="!files.length" class="text-xs text-ink-light">Sin adjuntos todavía.</p>
    <ul v-else class="space-y-1.5">
      <li v-for="f in files" :key="f.name" class="flex items-center justify-between gap-2 bg-surface-raised rounded-lg px-3 py-2">
        <a :href="f.file_url" target="_blank" class="flex items-center gap-2 text-xs text-ink hover:text-brand-600 min-w-0">
          <svg class="w-3.5 h-3.5 flex-shrink-0 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <span class="truncate">{{ f.file_name }}</span>
        </a>
        <button class="text-ink-light hover:text-red-500 flex-shrink-0 w-5 h-5 flex items-center justify-center" title="Eliminar" @click="removeFile(f)">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { call, uploadFile } from "@/utils/frappe.js";

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, default: "" },
});

const files = ref([]);
const loading = ref(false);
const uploading = ref(false);

async function loadFiles() {
  if (!props.docname) { files.value = []; return; }
  loading.value = true;
  try {
    files.value = await call("frappe.client.get_list", {
      doctype: "File",
      filters: { attached_to_doctype: props.doctype, attached_to_name: props.docname },
      fields: ["name", "file_name", "file_url", "file_size", "creation"],
      order_by: "creation desc",
      limit_page_length: 0,
    }) || [];
  } catch {
    files.value = [];
  } finally {
    loading.value = false;
  }
}

function pickAndUpload() {
  if (!props.docname) return;
  const input = document.createElement("input");
  input.type = "file";
  input.onchange = async (ev) => {
    const f = ev.target.files?.[0];
    if (!f) return;
    uploading.value = true;
    try {
      await uploadFile(f, { doctype: props.doctype, docname: props.docname });
      await loadFiles();
    } catch (e) {
      alert(e.message || "No se pudo subir el archivo");
    } finally {
      uploading.value = false;
    }
  };
  input.click();
}

async function removeFile(f) {
  if (!confirm(`¿Eliminar "${f.file_name}"?`)) return;
  try {
    await call("frappe.client.delete", { doctype: "File", name: f.name });
    files.value = files.value.filter((x) => x.name !== f.name);
  } catch (e) {
    alert(e.message || "No se pudo eliminar el archivo");
  }
}

watch(() => props.docname, loadFiles, { immediate: true });
</script>
