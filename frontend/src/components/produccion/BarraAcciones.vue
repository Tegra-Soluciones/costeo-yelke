<!--
  Barra de acciones fija al pie del área principal (docs/plan-ui-produccion.md §4.2).

  Es LA regla del diseño v2: todas las acciones de la pantalla viven aquí, siempre
  en el mismo lugar. No hay botones de acción principales dentro de tarjetas ni
  tablas (única excepción: acciones por fila que no avanzan el flujo, como
  "Registrar devolución").

    izquierda  "← <anterior>" (fantasma; se oculta si no hay anterior)
    centro     punto de color + UNA línea que explica por qué el botón está así
    derecha    0–2 secundarias + 1 primaria

  La primaria SIEMPRE avanza: es la acción pendiente del paso ("Validar factura")
  o, si ya terminó, "Siguiente: <paso> →".

  Cada vista la configura con un computed:
    { atras: {texto, ir}, estado: {color, texto}, acciones: [{texto, tipo,
      deshabilitado, motivo, accion}] }
-->
<template>
  <div class="sticky bottom-0 z-30 bg-white/95 backdrop-blur border-t border-surface-border">
    <div class="px-5 lg:px-10 h-16 flex items-center gap-3">
      <button
        v-if="barra.atras" type="button" class="p-btn-ghost -ml-3 flex-shrink-0"
        @click="barra.atras.ir && barra.atras.ir()"
      >← {{ barra.atras.texto }}</button>

      <div v-if="barra.estado" class="flex-1 min-w-0 hidden sm:flex items-center gap-2">
        <EstadoPunto :estado="barra.estado.color || 'off'" />
        <p class="text-[12.5px] text-ink-muted truncate" :title="barra.estado.texto">{{ barra.estado.texto }}</p>
      </div>
      <div v-else class="flex-1"></div>

      <div class="flex items-center gap-2 ml-auto flex-shrink-0">
        <button
          v-for="(a, i) in (barra.acciones || [])" :key="i" type="button"
          :class="a.tipo === 'primaria' ? 'p-btn-primary' : 'p-btn-secondary'"
          :disabled="a.deshabilitado || ocupado"
          :title="a.deshabilitado ? (a.motivo || undefined) : undefined"
          @click="a.accion && a.accion()"
        >
          <span v-if="ocupado && a.tipo === 'primaria'" class="w-3 h-3 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
          {{ a.texto }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import EstadoPunto from "@/components/produccion/EstadoPunto.vue";

defineProps({
  barra: { type: Object, default: () => ({}) },
  // Una acción en curso deshabilita toda la barra, para no disparar dos veces.
  ocupado: { type: Boolean, default: false },
});
</script>
