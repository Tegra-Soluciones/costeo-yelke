<!--
  Inicio. Dos vistas, según quién lo abre (el backend lo exige, ver api/tablero.py):

    Finanzas  → Dirección, Supervisor, Analista de costos: ventas, margen, a dónde va
                cada peso, clientes, talleres... por periodo y contra el anterior.
    Operación → todo el equipo: su trabajo, entregas por semana, compras, avance por
                taller, facturas por capturar. Sin cifras financieras de la empresa.

  Quien ve finanzas puede cambiar también a Operación.
-->
<template>
  <div class="flex flex-col min-h-0 bg-surface">
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-[1180px] mx-auto px-5 lg:px-8 py-6 space-y-5">
        <!-- Llegó aquí desde una pantalla que no tiene asignada (router/index.js). -->
        <p v-if="$route.query.sin_acceso" class="text-[12.5px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          No tienes acceso a <b>{{ $route.query.sin_acceso }}</b>. Pídele a quien administra los accesos que te la asigne.
        </p>
        <div class="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p class="p-eyebrow">Inicio · {{ companyState.selected || "Todas las compañías" }}</p>
            <h1 class="p-h1 mt-1">{{ saludo }}{{ nombre ? `, ${nombre}` : "" }}</h1>
            <p class="p-lede mt-0.5">{{ vista === "finanzas" ? `Lo validado ${textoPeriodo}. Montos netos, sin IVA.` : "Cómo va la operación hoy y lo que te toca." }}</p>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <div v-if="permisos.ve_finanzas" class="p-seg">
              <button type="button" :class="vista === 'finanzas' ? 'on' : ''" @click="vista = 'finanzas'">Finanzas</button>
              <button type="button" :class="vista === 'operacion' ? 'on' : ''" @click="vista = 'operacion'">Operación</button>
            </div>
            <div v-if="vista === 'finanzas'" class="p-seg">
              <button v-for="(etq, k) in PERIODOS" :key="k" type="button" :class="periodo === k ? 'on' : ''" @click="periodo = k">{{ etq }}</button>
            </div>
            <button type="button" class="p-btn-ghost h-8 px-2" :disabled="cargando" title="Actualizar" @click="cargar"><Icono nombre="actualizar" class="w-4 h-4" :class="cargando ? 'animate-spin' : ''" /></button>
          </div>
        </div>

        <RegresadosAMi />
        <RouterLink
          v-if="cuentaBandeja && (permisos.puede_aprobar || permisos.puede_revisar)" to="/direccion"
          class="p-panel px-4 py-3 flex items-center gap-3 hover:bg-zinc-50"
        >
          <span class="p-dot p-dot-now"></span>
          <span class="text-[13px] flex-1"><b class="font-semibold">{{ cuentaBandeja }}</b> {{ cuentaBandeja === 1 ? "documento espera" : "documentos esperan" }} tu {{ permisos.puede_aprobar ? "aprobación" : "revisión" }}</span>
          <span class="text-[12.5px] text-brand-600 font-medium">Abrir ›</span>
        </RouterLink>

        <p v-if="error" class="text-[13px] text-red-700">{{ error }}</p>
        <div class="transition-opacity" :class="cargando ? 'opacity-50' : ''">
          <TableroFinanzas v-if="vista === 'finanzas' && fin" :t="fin" :texto-periodo="textoPeriodo" :previo-texto="previoTexto" />
          <TableroOperativo v-else-if="vista === 'operacion' && ope" :o="ope" />
          <div v-else-if="cargando" class="py-20 text-center p-meta">Cargando…</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import Icono from "@/components/Icono.vue";
import RegresadosAMi from "@/components/aprobacion/RegresadosAMi.vue";
import TableroFinanzas from "@/components/tablero/TableroFinanzas.vue";
import TableroOperativo from "@/components/tablero/TableroOperativo.vue";
import { cargarPermisosAprobacion, cuentaBandeja, usePermisosAprobacion } from "@/composables/useAprobacion.js";
import { useCompany } from "@/composables/useCompany.js";
import { call } from "@/utils/frappe.js";
import { fecha } from "@/utils/formato.js";

const PERIODOS = { mes: "Mes", trimestre: "Trimestre", anio: "Año", "12m": "12 meses", todo: "Todo" };
const CLAVE_PERIODO = "costeo_yelke.periodo_inicio";
const CLAVE_VISTA = "costeo_yelke.vista_inicio";

const { state: companyState } = useCompany();
const permisos = usePermisosAprobacion();

const fin = ref(null);
const ope = ref(null);
const cargando = ref(false);
const error = ref("");
const periodo = ref(leer(CLAVE_PERIODO, Object.keys(PERIODOS), "anio"));
const vista = ref("operacion");

function leer(clave, validos, def) {
  try { const v = localStorage.getItem(clave); return validos.includes(v) ? v : def; } catch { return def; }
}
function guardar(clave, v) { try { localStorage.setItem(clave, v); } catch { /* opcional */ } }

const nombre = computed(() => ((vista.value === "finanzas" ? fin.value : ope.value)?.usuario || "").split(" ")[0]);
const saludo = computed(() => { const hr = new Date().getHours(); return hr < 12 ? "Buenos días" : hr < 19 ? "Buenas tardes" : "Buenas noches"; });
const textoPeriodo = computed(() => {
  if (!fin.value) return "";
  return fin.value.desde ? `del ${fecha(fin.value.desde)} al ${fecha(fin.value.hasta)}` : "de todo el historial";
});
const previoTexto = computed(() => (fin.value?.previo ? `vs ${fecha(fin.value.previo.desde)} – ${fecha(fin.value.previo.hasta)}` : ""));

async function cargar() {
  cargando.value = true;
  error.value = "";
  const company = companyState.selected || undefined;
  try {
    if (vista.value === "finanzas") fin.value = await call("costeo_yelke.api.tablero.get_tablero", { company, periodo: periodo.value });
    else ope.value = await call("costeo_yelke.api.tablero.get_tablero_operativo", { company });
  } catch (e) {
    error.value = e.message || "No se pudo cargar el tablero.";
  } finally {
    cargando.value = false;
  }
}

watch(periodo, (p) => { guardar(CLAVE_PERIODO, p); cargar(); });
watch(vista, (v) => { guardar(CLAVE_VISTA, v); cargar(); });
watch(() => companyState.selected, cargar);
onMounted(async () => {
  await cargarPermisosAprobacion();
  // Quien ve finanzas arranca donde la dejó (Finanzas por omisión); el resto, Operación.
  const inicial = permisos.ve_finanzas ? leer(CLAVE_VISTA, ["finanzas", "operacion"], "finanzas") : "operacion";
  if (vista.value === inicial) cargar(); else vista.value = inicial;
});
</script>
