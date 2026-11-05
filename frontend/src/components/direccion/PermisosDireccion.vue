<!--
  Permisos (solo Director): delegar las aprobaciones por unos días (api/delegacion.py)
  y prestar los permisos de un usuario a otro (api/permisos_temporales.py). Antes vivía
  dentro del Resumen; ahora Indicadores y Permisos son pestañas separadas.
-->
<template>
  <div class="px-4 lg:px-0 py-4 space-y-4">
    <!-- Delegación de aprobaciones (vacaciones) -->
    <div v-if="dlg" class="p-panel p-4">
      <template v-if="dlg.activa">
        <p class="text-[14px] font-semibold">Delegación activa</p>
        <p class="p-meta mt-0.5">{{ dlg.activa.a_nombre }} aprueba por ti del {{ fecha(dlg.activa.desde) }} al {{ fecha(dlg.activa.hasta) }}. Termina sola.</p>
        <button type="button" class="p-btn-secondary w-full h-11 mt-3" :disabled="ocupado" @click="terminar(dlg.activa)">Terminar ahora</button>
      </template>
      <template v-else-if="dlg.programadas.length">
        <p class="text-[14px] font-semibold">Delegación programada</p>
        <p class="p-meta mt-0.5">{{ dlg.programadas[0].a_nombre }} aprobará por ti del {{ fecha(dlg.programadas[0].desde) }} al {{ fecha(dlg.programadas[0].hasta) }}.</p>
        <button type="button" class="p-btn-secondary w-full h-11 mt-3" :disabled="ocupado" @click="terminar(dlg.programadas[0])">Cancelarla</button>
      </template>
      <template v-else>
        <p class="text-[14px] font-semibold">¿Vas a salir unos días?</p>
        <p class="p-meta mt-0.5">Deja a alguien aprobando por ti. Se termina sola en la fecha que elijas.</p>
        <button type="button" class="p-btn-primary w-full h-11 mt-3" @click="emit('delegar')">Delegar mis aprobaciones</button>
      </template>
      <p v-if="errorDlg" class="text-[12px] text-red-700 mt-2">{{ errorDlg }}</p>
    </div>
    <!-- Préstamo de permisos de un usuario a otro (api/permisos_temporales.py) -->
    <PermisosPrestados />
  </div>
</template>

<script setup>
import { ref } from "vue";
import PermisosPrestados from "@/components/direccion/PermisosPrestados.vue";
import { call } from "@/utils/frappe.js";
import { fecha } from "@/utils/formato.js";

defineProps({ dlg: { type: Object, default: null } });
const emit = defineEmits(["delegar", "delegacion"]);
const ocupado = ref(false);
const errorDlg = ref("");

async function terminar(f) {
  ocupado.value = true;
  errorDlg.value = "";
  try {
    emit("delegacion", await call("costeo_yelke.api.delegacion.terminar_delegacion", { name: f.name }), "terminada");
  } catch (e) {
    errorDlg.value = e.message || "No se pudo terminar la delegación.";
  } finally {
    ocupado.value = false;
  }
}
</script>
