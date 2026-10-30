<!--
  "Asignar proyecto" (Proyectos y Asignaciones): crea el costeo en borrador con su nombre,
  cliente y los almacenes de la compañía, y se lo asigna a quien costea
  (api/encargos.crear_proyecto). Quien asigna se queda donde estaba.
-->
<template>
  <PanelLateral :abierto="abierto" eyebrow="Proyecto nuevo" titulo="Asignar proyecto" meta="Se crea en borrador y le llega el aviso a quien lo va a costear" @cerrar="emit('cerrar')">
    <div class="space-y-3">
      <label class="block">
        <span class="p-field-label">Nombre del proyecto <span class="text-red-400">*</span></span>
        <input v-model="form.titulo" v-mayus class="p-field" placeholder="Ej. CAMISOLA GABARDINA FERROMEX" />
      </label>
      <div>
        <span class="p-field-label">Cliente <span class="text-red-400">*</span></span>
        <LinkInput v-model="form.cliente" doctype="Customer" placeholder="Buscar cliente…" />
      </div>
      <div>
        <span class="p-field-label">Compañía</span>
        <LinkInput v-model="form.compania" doctype="Company" placeholder="Compañía…" />
      </div>
      <label class="block">
        <span class="p-field-label">Quién lo costea <span class="text-red-400">*</span></span>
        <select v-model="form.usuario" class="p-field">
          <option value="" disabled>{{ candidatos.length ? "Elige a la persona" : "Nadie tiene Costear en Editar" }}</option>
          <option v-for="c in candidatos" :key="c.usuario" :value="c.usuario">{{ c.nombre }}{{ c.todo ? " (acceso total)" : "" }}</option>
        </select>
      </label>
      <label class="block">
        <span class="p-field-label">Mensaje</span>
        <textarea v-model="form.mensaje" rows="4" class="p-field h-auto py-2" placeholder="Qué pidió el cliente: prenda, cantidad, tela, fecha de entrega…"></textarea>
      </label>
      <label class="block w-1/2">
        <span class="p-field-label">Fecha límite (opcional)</span>
        <input v-model="form.fecha" type="date" class="p-field" />
      </label>
      <p class="text-[11.5px] text-ink-light">Se marca sola al validar el costeo o enviarlo a aprobación. Te avisamos cuando esté.</p>
      <p v-if="error" class="text-[12px] text-red-700">{{ error }}</p>
      <div class="flex justify-end gap-2 pt-1">
        <button type="button" class="p-btn-ghost" @click="emit('cerrar')">Cancelar</button>
        <button type="button" class="p-btn-primary" :disabled="ocupado || !form.titulo.trim() || !form.cliente || !form.usuario" @click="crear">
          {{ ocupado ? "Creando…" : "Crear y asignar" }}
        </button>
      </div>
    </div>
  </PanelLateral>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import LinkInput from "@/components/LinkInput.vue";
import PanelLateral from "@/components/produccion/PanelLateral.vue";
import { crearProyecto, getOpciones } from "@/composables/useEncargos.js";
import { useCompany } from "@/composables/useCompany.js";

const props = defineProps({ abierto: { type: Boolean, default: false } });
const emit = defineEmits(["cerrar", "creado"]);
const { state: companyState } = useCompany();

const form = reactive({ titulo: "", cliente: "", compania: "", usuario: "", mensaje: "", fecha: "" });
const candidatos = ref([]);
const ocupado = ref(false);
const error = ref("");

watch(() => props.abierto, async (a) => {
  if (!a) return;
  Object.assign(form, { titulo: "", cliente: "", compania: companyState.selected || "", usuario: "", mensaje: "", fecha: "" });
  error.value = "";
  try {
    const op = await getOpciones();
    candidatos.value = (op.pasos || []).find((p) => p.clave === "costear")?.candidatos || [];
    if (candidatos.value.length === 1) form.usuario = candidatos.value[0].usuario;
  } catch { candidatos.value = []; }
});

async function crear() {
  ocupado.value = true; error.value = "";
  try {
    const r = await crearProyecto({ ...form, titulo: form.titulo.trim(), fecha: form.fecha || undefined, compania: form.compania || undefined });
    const quien = candidatos.value.find((c) => c.usuario === form.usuario)?.nombre || form.usuario;
    emit("creado", { costeo: r.costeo, titulo: form.titulo.trim(), para: quien });
    emit("cerrar");
  } catch (e) { error.value = e.message || "No se pudo crear el proyecto."; }
  finally { ocupado.value = false; }
}
</script>
