<!--
  Levantamiento (Panel de Dirección): Juan toma los datos del pedido con el cliente
  enfrente -- cliente nuevo o ya dado de alta, su nombre y correo (obligatorios), qué
  pide, fotos y adjuntos -- y se lo asigna a quien va a costear. Crea el costeo en
  borrador y la asignación de Costear (api/encargos.crear_proyecto con levantamiento).
  La pantalla de Asignaciones queda solo para ver lo que a cada quien le asignaron.
-->
<template>
  <div class="px-4 lg:px-0 py-3 max-w-[760px] space-y-4">
    <p v-if="aviso" class="text-[12.5px] text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
      {{ aviso }}
      <RouterLink v-if="ultimo" :to="`/costeo/${encodeURIComponent(ultimo)}`" class="ml-1 font-medium underline">Abrir proyecto</RouterLink>
    </p>

    <section class="p-panel p-4 space-y-3">
      <p class="text-[14px] font-semibold">Cliente</p>
      <div class="p-seg grid grid-cols-2 sm:inline-grid">
        <button type="button" class="justify-center" :class="nuevo ? 'on' : ''" @click="cambiarTipo(true)">Cliente nuevo</button>
        <button type="button" class="justify-center" :class="!nuevo ? 'on' : ''" @click="cambiarTipo(false)">Ya registrado</button>
      </div>
      <label class="block">
        <span class="p-field-label">{{ nuevo ? "Nombre o razón social" : "Cliente" }} <span class="text-red-400">*</span></span>
        <input v-if="nuevo" v-model="form.cliente_nuevo" v-mayus class="p-field" placeholder="Nombre del cliente" />
        <LinkInput v-else v-model="form.cliente" doctype="Customer" placeholder="Buscar cliente…" @update:model-value="alElegirCliente" />
      </label>
      <p v-if="nuevo" class="p-meta -mt-1">Se da de alta (RFC) antes de cotizar; el correo y teléfono ya quedan listos.</p>
      <div class="grid sm:grid-cols-2 gap-3">
        <label class="block sm:col-span-2">
          <span class="p-field-label">Persona de contacto</span>
          <input v-model="form.contacto" class="p-field" placeholder="Con quién se habla del pedido" />
        </label>
        <label class="block">
          <span class="p-field-label">Correo <span class="text-red-400">*</span></span>
          <input v-model="form.correo" type="email" inputmode="email" autocomplete="off" class="p-field" :class="correoMal ? 'border-red-400' : ''" placeholder="correo@cliente.com" />
          <span v-if="correoMal" class="text-[11.5px] text-red-600">Revisa el correo</span>
        </label>
        <label class="block">
          <span class="p-field-label">Teléfono</span>
          <input v-model="form.telefono" type="tel" inputmode="tel" class="p-field" placeholder="10 dígitos" />
        </label>
      </div>
    </section>

    <section class="p-panel p-4 space-y-3">
      <p class="text-[14px] font-semibold">Pedido</p>
      <label class="block">
        <span class="p-field-label">Nombre del proyecto <span class="text-red-400">*</span></span>
        <input v-model="form.titulo" v-mayus class="p-field" placeholder="Ej. CAMISOLA GABARDINA FERROMEX" />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="p-field-label">Cantidad aproximada</span>
          <input v-model.number="form.cantidad" type="number" min="0" inputmode="numeric" class="p-field tabular-nums" placeholder="Prendas" />
        </label>
        <label class="block">
          <span class="p-field-label">Entrega que pide</span>
          <input v-model="form.fecha_entrega" type="date" class="p-field" />
        </label>
      </div>
      <label class="block">
        <span class="p-field-label">Detalles</span>
        <textarea v-model="form.mensaje" rows="5" class="p-field h-auto py-2" placeholder="Prenda, tela, colores, tallas, bordados, empaque…"></textarea>
      </label>
      <ArchivosAsignacion v-model="archivos" />
    </section>

    <section class="p-panel p-4 space-y-3">
      <p class="text-[14px] font-semibold">Quién lo costea</p>
      <div class="grid sm:grid-cols-2 gap-3">
        <label class="block">
          <span class="p-field-label">Persona <span class="text-red-400">*</span></span>
          <select v-model="form.usuario" class="p-field">
            <option value="" disabled>{{ candidatos.length ? "Elige a la persona" : "Nadie tiene Costear en Editar" }}</option>
            <option v-for="c in candidatos" :key="c.usuario" :value="c.usuario">{{ c.nombre }}{{ c.todo ? " (acceso total)" : "" }}</option>
          </select>
        </label>
        <label class="block">
          <span class="p-field-label">Fecha límite</span>
          <input v-model="form.fecha" type="date" class="p-field" />
        </label>
        <div class="sm:col-span-2">
          <span class="p-field-label">Compañía</span>
          <LinkInput v-model="form.compania" doctype="Company" placeholder="Compañía…" />
        </div>
      </div>
      <p class="text-[11.5px] text-ink-light">Se crea el costeo en borrador y a la persona le llega el aviso con todo lo capturado.</p>
    </section>

    <p v-if="error" class="text-[12.5px] text-red-700">{{ error }}</p>
    <div class="flex justify-end gap-2 pb-2">
      <button type="button" class="p-btn-ghost" :disabled="ocupado" @click="limpiar">Limpiar</button>
      <button type="button" class="p-btn-primary" :disabled="ocupado || !listo" @click="guardar">
        {{ ocupado ? "Guardando…" : "Guardar y asignar" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import LinkInput from "@/components/LinkInput.vue";
import ArchivosAsignacion from "@/components/asignaciones/ArchivosAsignacion.vue";
import { crearProyecto, getOpciones, subirArchivosAsignacion } from "@/composables/useEncargos.js";
import { useCompany } from "@/composables/useCompany.js";
import { call } from "@/utils/frappe.js";

const { state: companyState } = useCompany();
const VACIO = () => ({ titulo: "", cliente: "", cliente_nuevo: "", contacto: "", correo: "", telefono: "", cantidad: null,
  fecha_entrega: "", mensaje: "", usuario: "", fecha: "", compania: companyState.selected || "" });
const form = reactive(VACIO());
const nuevo = ref(true);
const archivos = ref([]);
const candidatos = ref([]);
const ocupado = ref(false);
const error = ref("");
const aviso = ref("");
const ultimo = ref("");

const CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const correoMal = computed(() => !!form.correo.trim() && !CORREO.test(form.correo.trim()));
const listo = computed(() => form.titulo.trim() && (nuevo.value ? form.cliente_nuevo.trim() : form.cliente)
  && CORREO.test(form.correo.trim()) && form.usuario);

function cambiarTipo(v) {
  nuevo.value = v;
  form.cliente = ""; form.cliente_nuevo = "";
}
// Cliente ya dado de alta: su correo y teléfono, si los tiene, para no volver a pedirlos.
async function alElegirCliente(v) {
  if (!v) return;
  try {
    const c = await call("frappe.client.get_value", { doctype: "Customer", filters: { name: v }, fieldname: ["email_id", "mobile_no"] });
    if (c?.email_id && !form.correo) form.correo = c.email_id;
    if (c?.mobile_no && !form.telefono) form.telefono = c.mobile_no;
  } catch { /* sin permiso de leer clientes: se captura a mano */ }
}

function limpiar() {
  const usuario = candidatos.value.length === 1 ? candidatos.value[0].usuario : "";
  Object.assign(form, VACIO(), { usuario });
  nuevo.value = true; archivos.value = []; error.value = "";
}

async function guardar() {
  ocupado.value = true; error.value = ""; aviso.value = "";
  try {
    const r = await crearProyecto({
      ...form, levantamiento: 1, titulo: form.titulo.trim(), correo: form.correo.trim(),
      cliente: nuevo.value ? "" : form.cliente, cliente_nuevo: nuevo.value ? form.cliente_nuevo.trim() : "",
      cantidad: form.cantidad || undefined, fecha_entrega: form.fecha_entrega || undefined,
      fecha: form.fecha || undefined, compania: form.compania || undefined,
    });
    if (archivos.value.length) await subirArchivosAsignacion(r.encargo, archivos.value);
    const quien = candidatos.value.find((c) => c.usuario === form.usuario)?.nombre || form.usuario;
    aviso.value = `${form.titulo.trim()}: asignado a ${quien}. Ya le llegó el aviso.`;
    ultimo.value = r.costeo;
    limpiar();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (e) { error.value = e.message || "No se pudo guardar el levantamiento."; }
  finally { ocupado.value = false; }
}

onMounted(async () => {
  try {
    const op = await getOpciones();
    candidatos.value = (op.pasos || []).find((p) => p.clave === "costear")?.candidatos || [];
    if (candidatos.value.length === 1) form.usuario = candidatos.value[0].usuario;
  } catch { candidatos.value = []; }
});
</script>
