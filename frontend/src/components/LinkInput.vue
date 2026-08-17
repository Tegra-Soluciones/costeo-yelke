<template>
  <div class="relative" ref="wrapper">
    <input
      ref="inputEl"
      :value="modelValue"
      :placeholder="placeholder"
      :readonly="readonly"
      :class="[
        'w-full text-sm border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 transition-colors',
        readonly ? 'bg-gray-50 border-gray-200 text-gray-500 cursor-default' : 'bg-white border-gray-200',
        error ? 'border-red-400 focus:ring-red-400' : '',
      ]"
      autocomplete="off"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeydown"
    />

    <!-- Clear button -->
    <button
      v-if="modelValue && !readonly"
      class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 text-xs leading-none"
      tabindex="-1"
      @mousedown.prevent="clear"
    >✕</button>

    <!-- Loading spinner inside input -->
    <svg
      v-else-if="loading"
      class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-300 animate-spin"
      fill="none" viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
    </svg>

    <!-- Dropdown -- va en un Teleport a <body> con position:fixed calculada a mano
         (no absolute dentro de .relative) para que un ancestro con overflow (ej. el
         tablero de niveles de Preparar Manufactura, que hace scroll horizontal) no lo
         recorte ni le meta su propia barra de desplazamiento -- debe poder flotar
         encima de lo que sea, igual que un <select> nativo. -->
    <Teleport to="body">
      <Transition name="drop">
        <div
          v-if="showDrop"
          class="fixed z-[9999] bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden"
          :style="dropStyle"
        >
          <!-- Results list -->
          <div class="max-h-56 overflow-y-auto">
            <div
              v-for="(item, idx) in results"
              :key="item.value"
              class="px-3 py-2 cursor-pointer flex flex-col gap-0.5 border-b border-gray-50 last:border-0"
              :class="idx === highlighted ? 'bg-brand-50' : 'hover:bg-gray-50'"
              @mousedown.prevent="select(item)"
            >
              <!-- Primary: description (human label) if available, else the name/code -->
              <span
                class="text-sm font-medium leading-tight"
                :class="idx === highlighted ? 'text-brand-700' : 'text-gray-800'"
              >
                {{ item.description || item.value }}
              </span>
              <!-- Secondary: show code/ID only when different from description -->
              <span
                v-if="item.description && item.description !== item.value"
                class="text-xs text-gray-400 font-mono leading-tight"
              >
                {{ item.value }}
              </span>
            </div>
          </div>

          <!-- Empty state -->
          <div v-if="!loading && !results.length" class="px-3 py-3 text-xs text-gray-400 text-center">
            Sin resultados para "{{ lastQuery }}"
          </div>

          <!-- Loading inside dropdown (initial fetch) -->
          <div v-if="loading && !results.length" class="px-3 py-3 flex items-center justify-center gap-2 text-xs text-gray-400">
            <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            Buscando…
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from "vue";
import { searchLink } from "@/utils/frappe.js";

const props = defineProps({
  modelValue: { type: String, default: "" },
  doctype:    { type: String, required: true },
  filters:    { type: Array, default: () => [] },
  placeholder:{ type: String, default: "" },
  readonly:   { type: Boolean, default: false },
  error:      { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const inputEl    = ref(null);
const results    = ref([]);
const showDrop   = ref(false);
const loading    = ref(false);
const highlighted = ref(-1);
const lastQuery  = ref("");
const dropStyle  = ref({});
let timer = null;
let currentReq  = 0; // for cancelling stale requests

// ── Posición del dropdown (Teleport a body, position:fixed) ──────────────────
// Se recalcula al abrir y mientras esté abierto, en cualquier scroll de la
// página O de un contenedor interno (capture:true en window sí ve esos scrolls)
// -- así se queda anclado al input aunque el ancestro con overflow se mueva.
function updateDropPosition() {
  const el = inputEl.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  dropStyle.value = {
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 220)}px`,
  };
}
function onWindowScrollOrResize() { if (showDrop.value) updateDropPosition(); }
window.addEventListener("scroll", onWindowScrollOrResize, true);
window.addEventListener("resize", onWindowScrollOrResize);
onBeforeUnmount(() => {
  window.removeEventListener("scroll", onWindowScrollOrResize, true);
  window.removeEventListener("resize", onWindowScrollOrResize);
});

// ── Search ────────────────────────────────────────────────────────────────────
async function doSearch(txt) {
  lastQuery.value = txt;
  loading.value   = true;
  showDrop.value  = true;
  highlighted.value = -1;
  updateDropPosition();

  const req = ++currentReq;
  try {
    const res = await searchLink(props.doctype, txt, props.filters);
    if (req !== currentReq) return; // stale response
    results.value = res;
  } catch {
    if (req !== currentReq) return;
    results.value = [];
  } finally {
    if (req === currentReq) loading.value = false;
  }
}

// ── Events ────────────────────────────────────────────────────────────────────
function onInput(e) {
  const val = e.target.value;
  emit("update:modelValue", val);
  clearTimeout(timer);
  // Debounce — show dropdown immediately on empty, slight delay when typing
  const delay = val ? 220 : 0;
  timer = setTimeout(() => doSearch(val), delay);
}

function onFocus() {
  // Always show dropdown on focus, even if field is empty
  if (showDrop.value) return; // already open
  doSearch(props.modelValue ?? "");
}

function onBlur() {
  // Delay so mousedown on a result fires first
  setTimeout(() => {
    showDrop.value    = false;
    highlighted.value = -1;
  }, 180);
}

function select(item) {
  emit("update:modelValue", item.value);
  showDrop.value    = false;
  results.value     = [];
  highlighted.value = -1;
}

function clear() {
  emit("update:modelValue", "");
  results.value   = [];
  showDrop.value  = false;
  loading.value   = false;
  inputEl.value?.focus();
}

// ── Keyboard navigation ───────────────────────────────────────────────────────
function onKeydown(e) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (!showDrop.value) doSearch(props.modelValue ?? "");
    else highlighted.value = Math.min(highlighted.value + 1, results.value.length - 1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    highlighted.value = Math.max(highlighted.value - 1, 0);
  } else if (e.key === "Enter" && highlighted.value >= 0) {
    e.preventDefault();
    select(results.value[highlighted.value]);
  } else if (e.key === "Escape") {
    showDrop.value = false;
  }
}
</script>

<style scoped>
.drop-enter-active { transition: opacity 0.1s ease, transform 0.1s ease; }
.drop-leave-active { transition: opacity 0.07s ease, transform 0.07s ease; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
