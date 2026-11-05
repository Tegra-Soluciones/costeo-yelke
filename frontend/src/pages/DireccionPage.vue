<!--
  Panel de Dirección (docs/plan-panel-direccion.md §4, mockup docs/mockups/direccion.html).

    Director            → Por aprobar · Proyectos · Resumen (+ delegar)
    Aprobador/delegado  → Por aprobar
    Revisor             → Por revisar

  Celular (< 1024 px): pantalla propia, sin el menú de la app, con pestañas abajo
  y el detalle a pantalla completa. Escritorio: lista + detalle en dos columnas.
  El documento abierto vive en la URL (?doc=Doctype/Nombre) para que los enlaces de
  la campana y del correo abran justo ese.
-->
<template>
  <div class="bg-surface" :class="esMovil ? 'min-h-full' : 'flex flex-col min-h-0'">
    <div v-if="permisos.cargado && !accede" class="p-10">
      <VacioEstado icono="candado" titulo="No tienes acceso a este panel" detalle="Es para Dirección y para quien revisa o aprueba documentos." />
    </div>

    <!-- ═════════════ CELULAR ═════════════ -->
    <template v-else-if="esMovil">
      <div class="bg-white px-5 pb-4 border-b border-surface-border" style="padding-top: max(10px, env(safe-area-inset-top))">
        <div class="flex items-center justify-between">
          <p class="p-eyebrow">{{ soloRevisa ? "Revisión de documentos" : "Dirección" }}</p>
          <div class="flex items-center -mr-2">
          <!-- Levantamiento ya no es pestaña: es su propia pantalla (también para el celular). -->
          <RouterLink v-if="permisos.ve_panel" to="/levantamiento" class="h-10 px-2 flex items-center text-[12px] text-brand-600 font-semibold">+ Levantar</RouterLink>
          <RouterLink to="/inicio" class="h-10 px-2 flex items-center text-[12px] text-ink-light font-medium">App ›</RouterLink>
          <button type="button" class="relative w-10 h-10 flex items-center justify-center text-ink-muted" @click="abrirNotificaciones">
            <svg class="w-[21px] h-[21px]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M6 8a6 6 0 1112 0c0 7 3 8 3 8H3s3-1 3-8M10 20a2 2 0 004 0"/></svg>
            <span v-if="noLeidas" class="absolute top-1.5 right-1.5 min-w-[17px] h-[17px] px-1 rounded-full bg-brand-500 text-white text-[10px] font-bold flex items-center justify-center">{{ noLeidas }}</span>
          </button>
          </div>
        </div>
        <h1 class="text-[24px] font-semibold tracking-tight leading-tight">{{ tituloMovil }}</h1>
        <p v-if="subtitulo" class="p-lede mt-0.5">{{ subtitulo }}</p>
      </div>
      <BannerDelegacion :propia="dlg?.activa" :recibida="permisos.delegacion" @terminar="terminarDelegacion" />

      <div :style="permisos.ve_panel ? 'padding-bottom: calc(76px + env(safe-area-inset-bottom))' : 'padding-bottom: 24px'">
        <template v-if="tab === 'aprobar'">
          <div v-if="!soloRevisa" class="px-4 pt-3 flex gap-2 overflow-x-auto" style="scrollbar-width: none">
            <button v-for="[k, l] in FILTROS" :key="k" type="button" class="chip" :class="filtro === k ? 'on' : ''" @click="filtro = k">
              {{ l }}<template v-if="cuentaFiltro(k)"> · {{ cuentaFiltro(k) }}</template>
            </button>
          </div>
          <ListaBandeja />
        </template>
        <ProyectosDireccion v-else-if="tab === 'proyectos'" ref="proyectosRef" :grupo-inicial="grupoProyectos" />
        <div v-else-if="tab === 'encargos'" class="px-4 pt-3"><VistaAsignaciones modo="equipo" movil /></div>
        <PorAsignar v-else-if="tab === 'porasignar'" @cuenta="porAsignar = $event" />
        <ResumenDireccion
          v-else ref="resumenRef" :pendientes="bandeja.items.length" :bloqueadas="bloqueadas" :dlg="dlg"
          @ir="irDesdeResumen" @delegar="hojaDelegar = true" @delegacion="alCambiarDelegacion"
        />
      </div>

      <nav v-if="permisos.ve_panel" class="fixed bottom-0 inset-x-0 z-30 grid grid-cols-5 bg-white/95 backdrop-blur border-t border-surface-border" style="padding-bottom: env(safe-area-inset-bottom)">
        <button
          v-for="t in TABS" :key="t.k" type="button" class="relative h-[56px] flex flex-col items-center justify-center gap-0.5 text-[10.5px] font-medium"
          :class="tab === t.k ? 'text-brand-600' : 'text-ink-light'" @click="irTab(t.k)"
        >
          <span v-html="t.icono"></span>{{ t.c || t.l }}
          <span v-if="t.k === 'aprobar' && bandeja.items.length" class="absolute top-1.5 left-[calc(50%+6px)] min-w-[16px] h-4 px-1 rounded-full bg-brand-500 text-white text-[9.5px] font-bold flex items-center justify-center">{{ bandeja.items.length }}</span>
        </button>
      </nav>

      <!-- Detalle a pantalla completa -->
      <div v-if="abierta" class="fixed inset-0 z-40 bg-surface flex flex-col" style="padding-top: env(safe-area-inset-top)">
        <div class="bg-white h-12 flex items-center px-2 border-b border-surface-border flex-shrink-0">
          <button type="button" class="h-10 px-2 flex items-center gap-0.5 text-brand-600 text-[14px] font-medium" @click="cerrarDetalle">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg>
            {{ soloRevisa ? "Por revisar" : "Por aprobar" }}
          </button>
        </div>
        <div class="flex-1 min-h-0"><DetalleAprobacion :key="clave(abierta)" :fila="abierta" movil @resuelto="alResolver" /></div>
      </div>
    </template>

    <!-- ═════════════ ESCRITORIO ═════════════ -->
    <template v-else>
      <div class="h-14 bg-white border-b border-surface-border flex items-center px-6 gap-4 flex-shrink-0">
        <div>
          <p class="p-eyebrow">{{ soloRevisa ? "Revisión de documentos" : "Dirección" }}</p>
          <p class="text-[16px] font-semibold leading-tight">{{ { aprobar: soloRevisa ? "Por revisar" : "Por aprobar", proyectos: "Proyectos", porasignar: "Por asignar", encargos: "Asignaciones", resumen: "Resumen" }[tab] }}</p>
        </div>
        <div v-if="permisos.ve_panel" class="p-seg ml-6">
          <button v-for="t in TABS" :key="t.k" type="button" :class="tab === t.k ? 'on' : ''" @click="irTab(t.k)">
            {{ t.l }}<template v-if="t.k === 'aprobar'"> · {{ bandeja.items.length }}</template><template v-if="t.k === 'porasignar' && porAsignar"> · {{ porAsignar }}</template>
          </button>
        </div>
        <button v-if="permisos.ve_panel && dlg && !dlg.activa && !dlg.programadas?.length" type="button" class="p-btn-secondary ml-auto h-8 text-[12.5px]" @click="hojaDelegar = true">Delegar…</button>
      </div>
      <BannerDelegacion :propia="dlg?.activa" :recibida="permisos.delegacion" escritorio @terminar="terminarDelegacion" />

      <div v-if="tab === 'aprobar'" class="flex-1 flex min-h-0" style="height: calc(100vh - 64px - 56px)">
        <div class="w-[400px] border-r border-surface-border flex flex-col bg-white flex-shrink-0">
          <div v-if="!soloRevisa" class="px-4 py-2.5 flex gap-2 border-b border-surface-border flex-wrap">
            <button v-for="[k, l] in FILTROS" :key="k" type="button" class="chip h-7 text-[12px]" :class="filtro === k ? 'on' : ''" @click="filtro = k">
              {{ l }}<template v-if="cuentaFiltro(k)"> · {{ cuentaFiltro(k) }}</template>
            </button>
          </div>
          <div class="overflow-y-auto flex-1"><ListaBandeja renglon /></div>
        </div>
        <div class="flex-1 min-w-0">
          <DetalleAprobacion v-if="abierta" :key="clave(abierta)" :fila="abierta" @resuelto="alResolver" />
          <div v-else class="h-full flex items-center justify-center text-center">
            <div><Icono nombre="check-circulo" class="w-10 h-10 mx-auto text-emerald-600" /><p class="font-semibold mt-2">{{ bandeja.items.length ? "Elige un documento" : "Todo al día" }}</p></div>
          </div>
        </div>
      </div>
      <div v-else class="flex-1 overflow-y-auto"><div class="max-w-[1100px] mx-auto px-6 py-5">
        <ProyectosDireccion v-if="tab === 'proyectos'" ref="proyectosRef" :grupo-inicial="grupoProyectos" />
        <VistaAsignaciones v-else-if="tab === 'encargos'" modo="equipo" />
        <PorAsignar v-else-if="tab === 'porasignar'" @cuenta="porAsignar = $event" />
        <ResumenDireccion
          v-else ref="resumenRef" :pendientes="bandeja.items.length" :bloqueadas="bloqueadas" :dlg="dlg"
          @ir="irDesdeResumen" @delegar="hojaDelegar = true" @delegacion="alCambiarDelegacion"
        />
      </div></div>
    </template>

    <HojaDelegar :abierto="hojaDelegar" :candidatos="dlg?.candidatos || []" :hoy="dlg?.hoy" @cerrar="hojaDelegar = false" @hecho="alDelegar" />

    <!-- Notificaciones (celular: no hay barra de la app) -->
    <Teleport to="body">
      <div v-if="hojaNotif" class="fixed inset-0 z-[70] bg-black/30 flex items-end" @click.self="hojaNotif = false">
        <div class="w-full bg-white rounded-t-[22px] max-h-[80vh] flex flex-col" style="padding-bottom: max(16px, env(safe-area-inset-bottom))">
          <div class="w-9 h-1 rounded-full bg-zinc-300 mx-auto mt-2 mb-1"></div>
          <div class="px-5 pt-2 pb-2 flex items-center justify-between">
            <p class="text-[17px] font-semibold">Notificaciones</p>
            <button type="button" class="text-[12.5px] text-brand-600 font-medium" @click="marcarLeidas">Marcar leídas</button>
          </div>
          <div class="overflow-y-auto">
            <button
              v-for="n in notificaciones" :key="n.name" type="button"
              class="w-full text-left px-5 py-3 flex gap-3 border-b border-surface-border" :class="n.read ? '' : 'bg-brand-50/40'"
              @click="abrirNotificacion(n)"
            >
              <span class="w-7 h-7 rounded-full flex items-center justify-center text-[10.5px] font-semibold flex-shrink-0" :class="colorAvatar(n.from_user)">{{ iniciales(n.from_user) }}</span>
              <div class="flex-1 min-w-0"><p class="text-[13px] leading-snug" v-html="n.subject"></p><p class="text-[11px] text-ink-light mt-0.5">{{ haceCuanto(n.creation) }}</p></div>
              <span v-if="!n.read" class="p-dot p-dot-now mt-2"></span>
            </button>
            <p v-if="!notificaciones.length" class="px-5 py-10 text-center p-meta">Sin notificaciones</p>
          </div>
        </div>
      </div>
    </Teleport>

    <Transition name="fade">
      <div v-if="toast" class="fixed left-4 right-4 lg:left-auto lg:right-6 lg:w-[420px] z-[60] bg-ink text-white text-[13px] rounded-xl px-4 py-3 flex items-center gap-3 shadow-lg"
           :style="esMovil ? 'bottom: calc(90px + env(safe-area-inset-bottom))' : 'bottom: 24px'">
        <Icono nombre="check-circulo" class="w-4 h-4 flex-shrink-0" /><span class="flex-1">{{ toast }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import VacioEstado from "@/components/produccion/VacioEstado.vue";
import Icono from "@/components/Icono.vue";
import TarjetaAprobacion from "@/components/direccion/TarjetaAprobacion.vue";
import DetalleAprobacion from "@/components/direccion/DetalleAprobacion.vue";
import ProyectosDireccion from "@/components/direccion/ProyectosDireccion.vue";
import ResumenDireccion from "@/components/direccion/ResumenDireccion.vue";
import VistaAsignaciones from "@/components/asignaciones/VistaAsignaciones.vue";
import PorAsignar from "@/components/direccion/PorAsignar.vue";
import HojaDelegar from "@/components/direccion/HojaDelegar.vue";
import { cargarPermisosAprobacion, refrescarCuentaBandeja, usePermisosAprobacion } from "@/composables/useAprobacion.js";
import { call } from "@/utils/frappe.js";
import { colorAvatar, dinero, fecha, haceCuanto, iniciales } from "@/utils/formato.js";

const route = useRoute();
const router = useRouter();
const permisos = usePermisosAprobacion();

const ICONOS = {
  aprobar: '<svg class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4"/><rect x="4" y="4" width="16" height="16" rx="4"/></svg>',
  proyectos: '<svg class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 5h7v7H4zM13 5h7v4h-7zM13 11h7v8h-7zM4 14h7v5H4z"/></svg>',
  encargos: '<svg class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M16 8a4 4 0 11-8 0 4 4 0 018 0zM4 20a8 8 0 0116 0"/></svg>',
  porasignar: '<svg class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M15 8a3 3 0 11-6 0 3 3 0 016 0zM4 20a8 8 0 0111-7.4M19 15v6M16 18h6"/></svg>',
  resumen: '<svg class="w-[22px] h-[22px]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></svg>',
};
const TABS = [
  { k: "aprobar", l: "Por aprobar", icono: ICONOS.aprobar },
  { k: "proyectos", l: "Proyectos", icono: ICONOS.proyectos },
  { k: "porasignar", l: "Por asignar", icono: ICONOS.porasignar },
  { k: "encargos", l: "Asignaciones", icono: ICONOS.encargos },
  { k: "resumen", l: "Resumen", icono: ICONOS.resumen },
];
const FILTROS = [["todos", "Todos"], ["compras", "Compras"], ["ventas", "Ventas"], ["costeo", "Costeos y precios"]];
const GRUPO = { "oc-mp": "compras", "oc-maq": "compras", fc: "compras", cot: "ventas", ov: "ventas", costeo: "costeo", precio: "costeo" };

// ── Celular o escritorio ──────────────────────────────────────────────────────
const mq = window.matchMedia("(max-width: 1023px)");
const esMovil = ref(mq.matches);
const alCambiarAncho = (e) => { esMovil.value = e.matches; };

// ── Estado ────────────────────────────────────────────────────────────────────
const bandeja = reactive({ items: [], esperando_revision: [], resueltos_hoy: [] });
const cargando = ref(false);
const error = ref("");
const filtro = ref("todos");
const abierta = ref(null);
const dlg = ref(null);
const hojaDelegar = ref(false);
const hojaNotif = ref(false);
const notificaciones = ref([]);
const noLeidas = ref(0);
const toast = ref("");
const grupoProyectos = ref("activos");
const porAsignar = ref(0);
const proyectosRef = ref(null);
const resumenRef = ref(null);

const accede = computed(() => permisos.ve_panel || permisos.puede_aprobar || permisos.puede_revisar || permisos.puede_aprobar_precios);
const soloRevisa = computed(() => permisos.puede_revisar && !permisos.puede_aprobar && !permisos.ve_panel);
const tab = computed(() => (permisos.ve_panel && ["proyectos", "porasignar", "encargos", "resumen"].includes(route.query.tab) ? route.query.tab : "aprobar"));
const lista = computed(() => bandeja.items.filter((f) => filtro.value === "todos" || GRUPO[f.tipo] === filtro.value));
const viejos = computed(() => bandeja.items.filter((f) => f.horas > 48).length);
const bloqueadas = computed(() => bandeja.items.filter((f) => f.bloqueo).length);
const cuentaFiltro = (k) => (k === "todos" ? bandeja.items.length : bandeja.items.filter((f) => GRUPO[f.tipo] === k).length);
const clave = (f) => `${f.tipo === "precio" ? "precio" : f.doctype}/${f.name}`;

const saludo = () => { const hr = new Date().getHours(); return hr < 12 ? "Buenos días" : hr < 19 ? "Buenas tardes" : "Buenas noches"; };
const tituloMovil = computed(() => (tab.value === "proyectos" ? "Proyectos" : tab.value === "porasignar" ? "Por asignar" : tab.value === "encargos" ? "Asignaciones" : tab.value === "resumen" ? "Resumen" : soloRevisa.value ? "Por revisar" : saludo()));
const subtitulo = computed(() => {
  if (tab.value !== "aprobar") return { resumen: "Indicadores y delegación", encargos: "Qué tiene asignado cada persona", porasignar: "Lo que ya puede empezarse y quién lo tiene" }[tab.value] || "Avance y alertas de cada costeo";
  if (soloRevisa.value) return "Revisas antes de que llegue a Dirección.";
  const n = bandeja.items.length;
  if (!n) return "Nada por aprobar";
  return `${n} por aprobar${viejos.value ? ` · ${viejos.value} lleva más de 48 h` : ""}`;
});

// ── Lista (bandeja) -- la misma en celular y escritorio ───────────────────────
const ListaBandeja = defineComponent({
  props: { renglon: Boolean },
  setup(p) {
    return () => {
      const vacio = !lista.value.length;
      const tarjetas = lista.value.map((f) => h(TarjetaAprobacion, {
        key: clave(f), fila: f, renglon: p.renglon, seleccionada: abierta.value && clave(abierta.value) === clave(f),
        onAbrir: abrir,
      }));
      const bloques = [
        h("div", { class: p.renglon ? "" : "px-4 py-3 space-y-2.5" }, [
          cargando.value && !bandeja.items.length ? h("p", { class: "p-meta text-center py-10" }, "Cargando…")
            : error.value ? h("p", { class: "text-[13px] text-red-700 p-4" }, error.value)
            : vacio ? h("div", { class: "text-center py-14" }, [
                h(Icono, { nombre: "check-circulo", class: "w-10 h-10 mx-auto text-emerald-600" }), h("p", { class: "text-[15px] font-semibold mt-2" }, "Todo al día"),
                h("p", { class: "p-meta" }, `No tienes nada pendiente${filtro.value !== "todos" ? " en este filtro" : ""}.`)])
            : tarjetas,
        ]),
      ];
      if (bandeja.esperando_revision.length && !soloRevisa.value) {
        bloques.push(h("details", { class: p.renglon ? "px-4 py-2 border-t border-surface-border" : "mx-4 mb-3" }, [
          h("summary", { class: "list-none cursor-pointer p-meta flex items-center gap-2 h-9" },
            [h("span", { class: "p-dot p-dot-off" }), `Esperando revisión antes de llegarte (${bandeja.esperando_revision.length}) ›`]),
          h("div", { class: "space-y-2 mt-1 opacity-75" }, bandeja.esperando_revision.map((f) =>
            h("div", { class: "p-panel px-4 py-2.5 flex items-center gap-3", key: clave(f) }, [
              h("div", { class: "flex-1 min-w-0" }, [
                h("p", { class: "text-[13px] font-medium truncate" }, `${f.etiqueta} · ${f.titulo}`),
                h("p", { class: "p-meta" }, `${haceCuanto(f.enviado_en)} · envió ${String(f.por_nombre || "").split(" ")[0]}`)]),
              h("span", { class: "tabular-nums text-[13px]" }, f.monto != null ? dinero(f.monto, f.moneda) : "")]))),
        ]));
      }
      if (bandeja.resueltos_hoy.length) {
        const ETQ = { Aprobado: ["p-pill-ok", "Aprobado"], Devuelto: ["p-pill-bad", "Regresado"], Revisado: ["p-pill-fac", "Revisado"] };
        bloques.push(h("details", { class: p.renglon ? "px-4 py-2 border-t border-surface-border" : "mx-4 mb-6" }, [
          h("summary", { class: "list-none cursor-pointer p-meta flex items-center gap-2 h-9" },
            [h("span", { class: "p-dot p-dot-ok" }), `Resueltos hoy (${bandeja.resueltos_hoy.length}) ›`]),
          h("div", { class: "space-y-2 mt-1" }, bandeja.resueltos_hoy.map((r, i) =>
            h("button", { type: "button", class: "w-full text-left p-panel px-4 py-2.5 flex items-center gap-3", key: i,
                          onClick: () => abrir({ doctype: r.doctype, name: r.name, tipo: "" }) }, [
              h("div", { class: "flex-1 min-w-0" }, [
                h("p", { class: "text-[13px] font-medium truncate" }, r.name),
                h("p", { class: "p-meta truncate" }, r.motivo ? `“${r.motivo}”` : haceCuanto(r.en))]),
              h("span", { class: (ETQ[r.resultado] || ETQ.Aprobado)[0] }, (ETQ[r.resultado] || ETQ.Aprobado)[1])]))),
        ]));
      }
      return h("div", bloques);
    };
  },
});

// ── Franja de delegación ──────────────────────────────────────────────────────
const BannerDelegacion = defineComponent({
  props: { propia: Object, recibida: Object, escritorio: Boolean },
  emits: ["terminar"],
  setup(p, { emit }) {
    return () => {
      if (p.recibida) {
        return h("div", { class: p.escritorio ? "mx-6 mt-3 rounded-xl bg-violet-50 border border-violet-200 px-4 py-2.5 text-[13px] text-violet-900"
                                              : "mx-4 mt-3 rounded-xl bg-violet-50 border border-violet-200 px-3.5 py-2.5 text-[12.5px] text-violet-900" },
          [h("b", p.recibida.de_nombre), ` te dejó aprobando en su lugar hasta el ${fecha(p.recibida.hasta)}.`]);
      }
      if (!p.propia) return null;
      return h("div", { class: `${p.escritorio ? "mx-6" : "mx-4"} mt-3 rounded-xl bg-violet-50 border border-violet-200 px-3.5 py-2.5 flex items-center gap-3` }, [
        h("span", { class: `w-7 h-7 rounded-full flex items-center justify-center text-[10.5px] font-semibold flex-shrink-0 ${colorAvatar(p.propia.a_usuario)}` }, iniciales(p.propia.a_nombre)),
        h("p", { class: "text-[12.5px] text-violet-900 flex-1 leading-snug" }, [h("b", p.propia.a_nombre), ` aprueba por ti del ${fecha(p.propia.desde)} al ${fecha(p.propia.hasta)}.`]),
        h("button", { type: "button", class: "text-[12.5px] font-semibold text-violet-700", onClick: () => emit("terminar", p.propia) }, "Terminar"),
      ]);
    };
  },
});

// ── Datos ─────────────────────────────────────────────────────────────────────
async function cargarBandeja() {
  cargando.value = true;
  error.value = "";
  try {
    const r = await call("costeo_yelke.api.aprobaciones.get_bandeja");
    bandeja.items = r.items || [];
    bandeja.esperando_revision = r.esperando_revision || [];
    bandeja.resueltos_hoy = r.resueltos_hoy || [];
  } catch (e) {
    error.value = e.message || "No se pudo cargar la bandeja.";
  } finally {
    cargando.value = false;
  }
  abrirDesdeUrl();
}

async function cargarDelegacion() {
  if (!permisos.ve_panel) return;
  try { dlg.value = await call("costeo_yelke.api.delegacion.get_delegacion"); } catch { dlg.value = null; }
}

async function contarNotificaciones() {
  try { noLeidas.value = (await call("costeo_yelke.api.item_api.get_navbar_data")).unread_notifications || 0; } catch { /* opcional */ }
}

// ── Navegación ────────────────────────────────────────────────────────────────
function abrir(f) {
  abierta.value = f;
  router.replace({ query: { ...route.query, doc: `${f.doctype}/${f.name}`, tipo: f.tipo === "precio" ? "precio" : undefined } });
}
function cerrarDetalle() {
  abierta.value = null;
  router.replace({ query: { ...route.query, doc: undefined, tipo: undefined } });
}
/** Abre el documento de ?doc= (enlace de la campana o del correo). Si ya no está en
 *  la bandeja (ya se resolvió), se abre igual: el detalle muestra su estado. */
function abrirDesdeUrl() {
  const q = String(route.query.doc || "");
  if (!q) {
    if (!esMovil.value && !abierta.value && lista.value.length) abierta.value = lista.value[0];
    return;
  }
  const [doctype, ...resto] = q.split("/");
  const name = resto.join("/");
  const tipo = route.query.tipo === "precio" ? "precio" : "";
  const k = `${tipo || doctype}/${name}`;
  abierta.value = bandeja.items.find((f) => clave(f) === k)
    || (abierta.value && clave(abierta.value) === k ? abierta.value : { doctype, name, tipo, por: "", por_nombre: "" });
}
function irTab(k) {
  abierta.value = null;
  router.replace({ query: { tab: k === "aprobar" ? undefined : k } });
}
function irDesdeResumen(destino) {
  if (destino === "atrasados") { grupoProyectos.value = "atrasados"; irTab("proyectos"); return; }
  irTab("aprobar");
}

let tt;
function avisar(t) { toast.value = t; clearTimeout(tt); tt = setTimeout(() => (toast.value = ""), 3200); }

async function alResolver({ accion, fila }) {
  const quien = fila.por_nombre || "su autor";
  avisar({
    aprobar: `${fila.etiqueta || "Documento"} aprobado. Le avisamos a ${quien}.`,
    regresar: `Regresado a ${quien}. Le llegó el aviso con tu comentario.`,
    marcar_revisado: "Revisado. Ya está en la bandeja de Dirección.",
  }[accion] || "Listo");
  const indice = lista.value.findIndex((f) => clave(f) === clave(fila));
  cerrarDetalle();
  await cargarBandeja();
  refrescarCuentaBandeja();
  if (esMovil.value) return;
  const siguiente = lista.value[Math.min(Math.max(indice, 0), lista.value.length - 1)];
  if (siguiente) abrir(siguiente); else cerrarDetalle();
}

async function alDelegar(r, elegido) {
  hojaDelegar.value = false;
  dlg.value = r;
  avisar(`${elegido?.nombre || "Esa persona"} aprobará por ti. Ya le avisamos.`);
}
function alCambiarDelegacion(r) {
  dlg.value = r;
  avisar("Delegación terminada. Vuelves a recibir todo.");
}
async function terminarDelegacion(f) {
  try { alCambiarDelegacion(await call("costeo_yelke.api.delegacion.terminar_delegacion", { name: f.name })); }
  catch (e) { avisar(e.message || "No se pudo terminar la delegación."); }
}

// ── Notificaciones (celular) ──────────────────────────────────────────────────
async function abrirNotificaciones() {
  hojaNotif.value = true;
  try { notificaciones.value = await call("costeo_yelke.api.item_api.get_notifications", { limit: 20 }); } catch { /* vacío */ }
}
async function marcarLeidas() {
  try { await call("costeo_yelke.api.item_api.mark_notifications_read"); } catch { /* opcional */ }
  notificaciones.value = notificaciones.value.map((n) => ({ ...n, read: 1 }));
  noLeidas.value = 0;
}
function abrirNotificacion(n) {
  hojaNotif.value = false;
  if (n.link && n.link.startsWith("/costeo-yelke")) router.push(n.link.replace(/^\/costeo-yelke/, "") || "/");
  else if (n.document_type && n.document_name) window.open(`/app/${n.document_type.toLowerCase().replace(/\s+/g, "-")}/${encodeURIComponent(n.document_name)}`, "_blank");
}

// ── Ciclo de vida ─────────────────────────────────────────────────────────────
let intervalo;
function alVolver() { if (document.visibilityState === "visible") { cargarBandeja(); contarNotificaciones(); } }

onMounted(async () => {
  mq.addEventListener("change", alCambiarAncho);
  await cargarPermisosAprobacion();
  if (!accede.value) return;
  cargarBandeja();
  cargarDelegacion();
  contarNotificaciones();
  // Para el número de la pestaña "Por asignar" aunque no se abra.
  if (permisos.ve_panel) {
    call("costeo_yelke.api.encargos.get_por_asignar").then((r) => { porAsignar.value = r.sin_asignar || 0; }).catch(() => {});
  }
  intervalo = setInterval(alVolver, 60000);
  document.addEventListener("visibilitychange", alVolver);
});
onBeforeUnmount(() => {
  mq.removeEventListener("change", alCambiarAncho);
  clearInterval(intervalo);
  document.removeEventListener("visibilitychange", alVolver);
});
watch(() => route.query.doc, () => { if (route.query.doc) abrirDesdeUrl(); });
watch(esMovil, (m) => { if (!m && !abierta.value && lista.value.length) abierta.value = lista.value[0]; });
</script>

<style scoped>
.chip { @apply h-8 px-3 rounded-full border border-surface-border bg-white text-[12.5px] text-ink-muted font-medium whitespace-nowrap; }
.chip.on { @apply bg-ink text-white border-ink; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
