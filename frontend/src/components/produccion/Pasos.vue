<!--
  Stepper genérico: EL MISMO componente para el lote (4 pasos), cada taller (4),
  la preparación (3) y cada documento de compra (OC → Recibo → Factura).
  Ver docs/plan-ui-produccion.md §4.1.1 y §4.3.

  `pasos`: [{ clave, texto, estado, bloqueado, motivo }]
     estado: "hecho" | "facturado" | "actual" | "bloqueado" | "espera"
     bloqueado: no se puede abrir todavía (prerrequisito o falta de rol)
     candado:   la razón es el ROL -> se dibuja 🔒 en vez del número
     motivo:    tooltip con la razón

  `seleccionado`: la clave del paso que se está viendo (anillo gris).
  `navegable`: deja hacer clic; emite `ir` con la clave.
  `compacto`: solo los números, sin texto -- para una fila de lista.
-->
<template>
  <div class="p-steps" :class="{ nav: navegable }">
    <template v-for="(paso, i) in pasos" :key="paso.clave">
      <span v-if="i" class="p-step-line"></span>
      <component
        :is="esNavegable(paso) ? 'button' : 'span'"
        class="p-step"
        :class="claseDe(paso)"
        :type="esNavegable(paso) ? 'button' : undefined"
        :disabled="esNavegable(paso) ? undefined : null"
        :title="paso.motivo || paso.texto || undefined"
        @click="esNavegable(paso) && emit('ir', paso.clave)"
      >
        <span class="n">{{ numero(paso, i) }}</span>
        <template v-if="!compacto">{{ paso.texto }}</template>
      </component>
    </template>
  </div>
</template>

<script setup>
const props = defineProps({
  pasos: { type: Array, default: () => [] },
  seleccionado: { type: String, default: "" },
  navegable: { type: Boolean, default: false },
  compacto: { type: Boolean, default: false },
});
const emit = defineEmits(["ir"]);

// Un paso bloqueado por permisos nunca es navegable, aunque el stepper lo sea.
const esNavegable = (paso) => props.navegable && !paso.bloqueado;

function claseDe(paso) {
  return {
    done: paso.estado === "hecho",
    fac: paso.estado === "facturado",
    now: paso.estado === "actual",
    bad: paso.estado === "bloqueado",
    sel: paso.clave === props.seleccionado,
    bloq: !!paso.bloqueado,
  };
}
// Hecho y facturado muestran ✓; sin rol, candado; el resto, su número -- un paso
// que solo espera a que termine el anterior sigue siendo "el paso 3", no un muro.
function numero(paso, i) {
  if (paso.candado) return "🔒";
  if (paso.estado === "hecho" || paso.estado === "facturado") return "✓";
  return i + 1;
}
</script>
