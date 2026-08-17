<template>
  <div class="flex flex-col h-full">
    <PageHeader :title="title" :subtitle="subtitle">
      <slot name="actions" />
    </PageHeader>

    <!-- Stats -->
    <div v-if="stats.length" class="px-5 pt-4 pb-2 grid gap-3 flex-shrink-0" :style="{ gridTemplateColumns: `repeat(${stats.length}, minmax(0, 1fr))` }">
      <div v-for="s in stats" :key="s.label" class="bg-white border border-gray-200 rounded-xl px-4 py-3">
        <p class="text-xs text-gray-400 font-medium">{{ s.label }}</p>
        <p class="text-xl font-bold mt-1" :style="{ color: s.color || '#1e293b' }">{{ s.value }}</p>
        <p v-if="s.sub" class="text-xs text-gray-400 mt-0.5">{{ s.sub }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="px-5 py-2 flex items-center gap-3 flex-shrink-0">
      <input
        v-if="searchPlaceholder"
        :value="search"
        type="text"
        :placeholder="searchPlaceholder"
        class="h-8 px-3 text-sm border border-gray-200 rounded-lg flex-1 max-w-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
        @input="$emit('update:search', $event.target.value)"
      />
      <slot name="filters" />
      <button v-if="showClear" class="text-xs text-gray-400 hover:text-gray-600" @click="$emit('clear')">Limpiar</button>
    </div>

    <!-- Table -->
    <div class="flex-1 overflow-y-auto px-5 pb-5">
      <div v-if="loading" class="flex items-center justify-center h-40">
        <svg class="w-6 h-6 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </div>
      <div v-else-if="!rows.length" class="flex flex-col items-center justify-center h-40 text-gray-400">
        <svg class="w-8 h-8 mb-2 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" :d="emptyIcon"/></svg>
        <p class="text-sm">{{ emptyLabel }}</p>
      </div>
      <table v-else class="w-full text-sm">
        <thead class="sticky top-0 bg-white z-10">
          <tr class="border-b border-gray-100">
            <slot name="head" />
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr
            v-for="row in rows"
            :key="row.name"
            class="group cursor-pointer hover:bg-gray-50 transition-colors"
            @click="handleRowClick(row)"
          >
            <slot name="row" :row="row" />
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Aviso para filas sin costeo vinculado (solo si el padre pasó deskDoctype) --
         no hay a dónde redirigir dentro de la app, así que se ofrece abrirlo en ERPNext
         en vez de dejar el clic sin ningún efecto ni explicación. -->
    <div v-if="toast.show" class="fixed bottom-5 right-5 z-50 bg-white border border-gray-200 shadow-lg rounded-xl px-4 py-3 flex items-center gap-3 max-w-sm">
      <svg class="w-5 h-5 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
      <p class="text-[13px] text-gray-700 flex-1">{{ toast.msg }}</p>
      <button class="text-[12.5px] font-semibold text-brand-600 hover:text-brand-700 whitespace-nowrap flex-shrink-0" @click="openInErpnext">Abrir en ERPNext</button>
    </div>
  </div>
</template>

<script setup>
// Shell genérico de "lista de documentos": PageHeader + stats + búsqueda + tabla.
// Cada doctype define sus propias columnas (slots "head"/"row") y su propia lógica de
// datos/estadísticas/filtros -- este componente solo pone el layout y los estados
// comunes (loading/empty/hover), para no repetirlo en cada ListPage nueva.
import { reactive } from "vue";
import PageHeader from "@/components/PageHeader.vue";

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  stats: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  rows: { type: Array, default: () => [] },
  search: { type: String, default: "" },
  searchPlaceholder: { type: String, default: "" },
  showClear: { type: Boolean, default: false },
  emptyLabel: { type: String, default: "Sin resultados" },
  emptyIcon: { type: String, default: "M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V17a2 2 0 01-2 2H5a2 2 0 01-2-2z" },
  // Doctype de ERPNext (ej. "Purchase Receipt") -- si se pasa, las filas SIN costeo
  // vinculado ya no emiten "row-click" (no hay detalle propio a dónde ir); en vez de
  // eso se avisa y se ofrece abrir el documento real en ERPNext en pestaña nueva.
  deskDoctype: { type: String, default: "" },
});
const emit = defineEmits(["update:search", "clear", "row-click"]);

const toast = reactive({ show: false, msg: "", url: "" });
function handleRowClick(row) {
  if (props.deskDoctype && !row.costeo) {
    toast.msg = "Este documento no está vinculado a un Costeo -- no hay a dónde llevarte dentro de la app.";
    toast.url = `/app/${props.deskDoctype.toLowerCase().replace(/\s+/g, "-")}/${encodeURIComponent(row.name)}`;
    toast.show = true;
    setTimeout(() => { toast.show = false; }, 6000);
    return;
  }
  emit("row-click", row);
}
function openInErpnext() {
  if (toast.url) window.open(toast.url, "_blank");
  toast.show = false;
}
</script>
