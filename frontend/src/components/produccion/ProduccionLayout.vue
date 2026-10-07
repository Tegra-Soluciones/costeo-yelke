<!--
  Armazón de Producción: menú + área principal + barra de acciones fija
  (docs/plan-ui-produccion.md §4.2).

    ┌ menú (248px) ┬ encabezado de la vista + contenido ┐
    │              ├────────────────────────────────────┤
    │              │ ← Anterior  ● estado   [sec] [PRI] │ ← siempre aquí
    └──────────────┴────────────────────────────────────┘

  El encabezado (eyebrow · título · una línea de ayuda · stepper) lo arma el
  layout para que TODAS las vistas se vean igual; lo de adentro lo pone cada una
  por el slot por omisión.
-->
<template>
  <div class="flex min-h-[60vh]">
    <ProduccionMenu
      v-bind="menu" :vista="vista" :lote-ref="loteRef" :puede-ver="puedeVer"
      @ir="(d) => emit('ir', d)" @nuevo-lote="emit('nuevo-lote')" @cambiar-ov="(v) => emit('cambiar-ov', v)"
    />

    <main class="flex-1 min-w-0 flex flex-col">
      <div class="flex-1 px-5 lg:px-10 py-7 pb-10 max-w-[1000px] w-full">
        <ProduccionMenu
          movil v-bind="menu" :vista="vista" :lote-ref="loteRef" :puede-ver="puedeVer"
          @ir="(d) => emit('ir', d)"
        />

        <div v-if="encabezado" class="mb-6">
          <p v-if="encabezado.eyebrow" class="p-eyebrow">{{ encabezado.eyebrow }}</p>
          <div class="flex items-end justify-between gap-4 flex-wrap mt-1">
            <div class="min-w-0">
              <h1 class="p-h1">{{ encabezado.titulo }}</h1>
              <p v-if="encabezado.meta" class="p-meta mt-0.5">{{ encabezado.meta }}</p>
            </div>
            <slot name="encabezado-derecha" />
          </div>
          <p v-if="encabezado.ayuda" class="p-lede mt-1">{{ encabezado.ayuda }}</p>
          <Pasos
            v-if="pasos.length" class="mt-5 max-w-[680px]" :pasos="pasos" :seleccionado="pasoActual"
            navegable @ir="(c) => emit('ir-paso', c)"
          />
        </div>

        <slot />
      </div>

      <BarraAcciones :barra="barra" :ocupado="ocupado" />
    </main>
  </div>
</template>

<script setup>
import ProduccionMenu from "@/components/produccion/ProduccionMenu.vue";
import BarraAcciones from "@/components/produccion/BarraAcciones.vue";
import Pasos from "@/components/produccion/Pasos.vue";

defineProps({
  menu: { type: Object, default: () => ({}) },
  vista: { type: String, default: "" },
  loteRef: { type: String, default: "" },
  encabezado: { type: Object, default: null },
  pasos: { type: Array, default: () => [] },
  pasoActual: { type: String, default: "" },
  barra: { type: Object, default: () => ({}) },
  ocupado: { type: Boolean, default: false },
  puedeVer: { type: Function, default: () => true },
});
const emit = defineEmits(["ir", "ir-paso", "nuevo-lote", "cambiar-ov"]);
</script>
