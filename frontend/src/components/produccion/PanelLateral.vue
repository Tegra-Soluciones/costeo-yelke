<!--
  Panel lateral (drawer) de 560 px; pantalla completa en celular.
  Ver docs/plan-ui-produccion.md §4.2.

  Aquí vive el detalle de un documento suelto (una OC, un recibo, una factura, el
  formulario de "Nuevo lote"). El trabajo de varios pasos (un taller) NO va aquí:
  va en una sub-pantalla.

    encabezado  eyebrow · título · meta · pill de estado · "⋯" · ✕
    stepper     opcional, del documento
    cuerpo      con scroll
    pie 64 px   izquierda: enlaces (Vista previa, Descargar, ERPNext ↗)
                derecha: secundaria + primaria -- misma disposición que la barra
                de abajo, porque es la misma regla

  Esc o clic fuera lo cierra. Uno a la vez (el estado de useProduccion es de un
  documento a la vez, ver §10 del plan).
-->
<template>
  <Teleport to="body">
    <div
      v-show="abierto" class="fixed inset-0 bg-black/20 z-40"
      @click="emit('cerrar')"
    ></div>
    <aside
      ref="caja" tabindex="-1"
      class="fixed top-0 right-0 h-full w-full max-w-[560px] bg-white z-50 shadow-2xl border-l border-surface-border flex flex-col transition-transform duration-200 focus:outline-none"
      :class="abierto ? 'translate-x-0' : 'translate-x-full'"
      role="dialog" :aria-hidden="!abierto"
      @keydown.esc="emit('cerrar')"
    >
      <!-- Solo el panel ABIERTO monta su contenido. Los tres paneles de Producción
           viven a la vez en el DOM (Teleport) y comparten el estado de useProduccion
           (docCompra, pinvDoc, scoSel…): si todos renderizaran, el de atrás pintaría
           el documento del de adelante. Ver §10 del plan. -->
      <template v-if="abierto">
      <div class="px-6 pt-5 pb-4 border-b border-surface-border flex-shrink-0">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p v-if="eyebrow" class="p-eyebrow">{{ eyebrow }}</p>
            <p class="text-[16px] font-semibold mt-0.5 truncate">{{ titulo }}</p>
            <p v-if="meta || $slots.meta" class="p-meta"><slot name="meta">{{ meta }}</slot></p>
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            <slot name="pill" />
            <div v-if="$slots.mas" class="relative">
              <button type="button" class="p-btn-ghost h-8 px-2" title="Más acciones" @click="masAbierto = !masAbierto">⋯</button>
              <div
                v-if="masAbierto"
                class="absolute right-0 top-9 z-10 bg-white border border-surface-border rounded-lg shadow-lg py-1 min-w-[220px]"
                @click="masAbierto = false"
              ><slot name="mas" /></div>
            </div>
            <button type="button" class="p-btn-ghost h-8 px-2" title="Cerrar" @click="emit('cerrar')">✕</button>
          </div>
        </div>
        <Pasos
          v-if="pasos.length" class="mt-4" :pasos="pasos" :seleccionado="pasoActual"
          navegable @ir="(c) => emit('ir-paso', c)"
        />
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5"><slot /></div>

      <div v-if="$slots.enlaces || acciones.length || soloLectura" class="h-16 border-t border-surface-border px-6 flex items-center gap-2 flex-shrink-0">
        <div class="flex gap-1 min-w-0"><slot name="enlaces" /></div>
        <div class="flex-1"></div>
        <!-- Un paso que pertenece a otra vista se ve, pero no se captura desde aquí. -->
        <p v-if="soloLectura" class="text-[12.5px] text-ink-muted truncate">{{ soloLectura }}</p>
        <div v-else class="flex gap-2 flex-shrink-0">
          <button
            v-for="(a, i) in acciones" :key="i" type="button"
            :class="a.tipo === 'primaria' ? 'p-btn-primary' : 'p-btn-secondary'"
            :disabled="a.deshabilitado || ocupado"
            :title="a.deshabilitado ? (a.motivo || undefined) : undefined"
            @click="a.accion && a.accion()"
          >{{ a.texto }}</button>
        </div>
      </div>
      </template>
    </aside>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import Pasos from "@/components/produccion/Pasos.vue";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  eyebrow: { type: String, default: "" },
  titulo: { type: String, default: "" },
  meta: { type: String, default: "" },
  pasos: { type: Array, default: () => [] },
  pasoActual: { type: String, default: "" },
  acciones: { type: Array, default: () => [] },
  ocupado: { type: Boolean, default: false },
  // Texto tipo "La captura la hace Facturas": se muestra en lugar de los botones.
  soloLectura: { type: String, default: "" },
});
const emit = defineEmits(["cerrar", "ir-paso"]);

const masAbierto = ref(false);
const caja = ref(null);

function onKey(e) { if (e.key === "Escape" && props.abierto) emit("cerrar"); }

// El panel puede traer dentro la vista previa del PDF en un <iframe>, que al
// cargar se queda con el foco. Las teclas que se pulsan ahí dentro NO llegan al
// documento de la página, así que Esc dejaba de cerrar el panel. Como la vista
// previa se sirve desde el mismo sitio, se le pone el mismo escuchador dentro.
const iframesEscuchados = new WeakSet();
function escucharIframes() {
  for (const f of caja.value?.querySelectorAll("iframe") || []) {
    const enganchar = () => {
      try {
        const doc = f.contentDocument;
        if (!doc || iframesEscuchados.has(doc)) return;
        iframesEscuchados.add(doc);
        doc.addEventListener("keydown", onKey);
      } catch { /* otro origen: no se puede, y no pasa nada */ }
    };
    enganchar();
    f.addEventListener("load", enganchar);
  }
}

watch(() => props.abierto, async (v) => {
  if (!v) { masAbierto.value = false; return; }
  await nextTick();
  caja.value?.focus();
  escucharIframes();
  // Los iframes tardan en cargar; se vuelve a revisar un par de veces.
  setTimeout(escucharIframes, 600);
  setTimeout(escucharIframes, 2000);
});

onMounted(() => document.addEventListener("keydown", onKey));
onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>
