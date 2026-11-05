<!--
  Asignaciones: quién está haciendo qué (docs/plan-encargos.md). Dirección y quien tiene
  acceso total ven las de todo el equipo; los demás, las que les asignaron y las que
  asignaron ellos. Solo para verlas: los proyectos nuevos se levantan y asignan en el
  Panel de Dirección › Levantamiento.
-->
<template>
  <div class="flex flex-col min-h-0 bg-surface">
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-[1180px] mx-auto px-4 lg:px-8 py-4 lg:py-6 space-y-4 lg:space-y-5">
        <div class="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p class="p-eyebrow">Todas las compañías</p>
            <h1 class="p-h1 mt-1">Asignaciones</h1>
            <p class="p-lede mt-0.5">Quién tiene cada paso de cada proyecto. Se marcan solas cuando el paso se atiende.</p>
          </div>
          <!-- En el celular no hay menú de la app (meta.movil): la salida a las otras. -->
          <EnlacesCelular v-if="esMovil" actual="/asignaciones" class="-order-1 w-full justify-end -mb-2" />
          <div class="flex items-center gap-2 flex-wrap" :class="esMovil ? 'w-full' : ''">
            <select v-if="cuenta.ve_equipo" v-model="modo" class="p-field h-9" :class="esMovil ? 'flex-1 min-w-0' : 'w-auto'">
              <option value="equipo">Todo el equipo</option>
              <option value="mias">Solo las mías</option>
            </select>
          </div>
        </div>
        <VistaAsignaciones :key="modo" :modo="modo" :movil="esMovil" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import VistaAsignaciones from "@/components/asignaciones/VistaAsignaciones.vue";
import EnlacesCelular from "@/components/EnlacesCelular.vue";
import { cuenta, refrescarCuenta } from "@/composables/useEncargos.js";

// Celular: menú como selector arriba y la lista a todo el ancho (VistaAsignaciones › movil).
const mq = window.matchMedia("(max-width: 1023px)");
const esMovil = ref(mq.matches);
const alCambiarAncho = (e) => { esMovil.value = e.matches; };
mq.addEventListener("change", alCambiarAncho);
onBeforeUnmount(() => mq.removeEventListener("change", alCambiarAncho));
const modo = ref("mias");
// Primero lo de cada quien; el equipo completo se elige arriba (o en Dirección › Asignaciones).
onMounted(refrescarCuenta);
watch(() => cuenta.value.ve_equipo, (v) => { if (!v) modo.value = "mias"; });
</script>
