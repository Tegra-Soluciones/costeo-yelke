<!--
  Accesos (docs/plan-accesos-ejecucion.md, fase 8): qué vistas tiene cada puesto
  (perfil) y cada usuario, en "Editar" o "Ver". Las vistas van en renglones agrupados
  y los puestos en columnas: son pocos puestos y muchas vistas.

  "Ver como…" pinta la app con los accesos de un puesto o usuario para revisar lo que
  verá antes de dárselo (solo cambia la pantalla; ver useAccesos.simular).
-->
<template>
  <div class="flex flex-col min-h-0 bg-surface">
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-[1180px] mx-auto px-5 lg:px-8 py-6 space-y-5">
        <div class="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p class="p-eyebrow">Administración</p>
            <h1 class="p-h1 mt-1">Accesos</h1>
            <p class="p-lede mt-0.5">Cada puesto con sus vistas: <b>Editar</b> ve y captura, <b>Ver</b> solo consulta. Los usuarios toman los accesos de su puesto.</p>
          </div>
          <div class="flex items-center gap-2">
            <input v-model="nuevoPerfil" v-mayus class="p-field h-9 w-56" placeholder="Nuevo puesto (ej. COMPRAS)" @keyup.enter="crearPerfil" />
            <button type="button" class="p-btn-secondary" :disabled="!nuevoPerfil.trim() || ocupado" @click="crearPerfil">Agregar puesto</button>
          </div>
        </div>

        <p v-if="error" class="text-[12.5px] text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{{ error }}</p>
        <div v-if="cargando" class="p-panel p-10 text-center p-meta">Cargando accesos…</div>

        <template v-else-if="m">
          <!-- Matriz: vistas × puestos -->
          <section class="p-panel overflow-x-auto">
            <table class="p-tbl min-w-[720px]">
              <thead>
                <tr>
                  <th class="sticky left-0 bg-white">Vista</th>
                  <th v-for="p in m.perfiles" :key="p.nombre" class="text-center min-w-[9.5rem]">
                    <span class="block text-ink text-[12px] font-semibold normal-case">{{ p.nombre }}</span>
                    <span class="block font-normal">{{ p.usuarios }} usuario(s){{ p.pase_libre ? " · todo" : "" }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <template v-for="g in grupos" :key="g.grupo">
                  <tr><td :colspan="m.perfiles.length + 1" class="!py-1.5 bg-surface-raised/60"><span class="p-eyebrow">{{ g.grupo }}</span></td></tr>
                  <tr v-for="v in g.vistas" :key="v.clave">
                    <td class="sticky left-0 bg-white" :title="v.descripcion">{{ v.etiqueta }}</td>
                    <td v-for="p in m.perfiles" :key="p.nombre" class="text-center">
                      <span v-if="p.pase_libre" class="text-[12px] text-ink-light">Todo</span>
                      <select v-else v-model="borrador[p.nombre][v.clave]" class="p-field h-8 py-0 text-[12.5px] w-28"
                              :class="borrador[p.nombre][v.clave] === 'editar' ? 'font-semibold text-ink' : borrador[p.nombre][v.clave] === 'ver' ? 'text-ink' : 'text-ink-light'">
                        <option value="">—</option><option value="ver">Ver</option><option value="editar">Editar</option>
                      </select>
                    </td>
                  </tr>
                </template>
              </tbody>
              <tfoot>
                <tr>
                  <td class="sticky left-0 bg-white"></td>
                  <td v-for="p in m.perfiles" :key="p.nombre" class="text-center">
                    <button v-if="!p.pase_libre" type="button" class="text-[12px] text-brand-600 hover:text-brand-700" @click="verComo(p.nombre, borrador[p.nombre])">Ver como…</button>
                  </td>
                </tr>
              </tfoot>
            </table>
          </section>
          <div class="flex items-center justify-end gap-3 sticky bottom-0 bg-surface/95 py-3">
            <p v-if="cambiados.length" class="p-meta">Cambios en {{ cambiados.join(", ") }}: se aplican a sus usuarios al guardar.</p>
            <button type="button" class="p-btn-primary" :disabled="!cambiados.length || ocupado" @click="guardar">{{ ocupado ? "Guardando…" : "Guardar cambios" }}</button>
          </div>

          <!-- Usuarios -->
          <section class="p-panel">
            <div class="px-4 pt-4 pb-2">
              <p class="text-[14px] font-semibold text-ink">Usuarios</p>
              <p class="p-meta">El puesto decide sus accesos. Al cambiar de puesto, sus roles pasan a ser los del puesto (los préstamos vigentes se conservan).</p>
            </div>
            <table class="p-tbl">
              <thead><tr><th>Usuario</th><th>Puesto</th><th>Vistas</th><th>Préstamos</th><th></th></tr></thead>
              <tbody>
                <tr v-for="u in m.usuarios" :key="u.usuario">
                  <td>{{ u.nombre }}<span class="block text-[11.5px] text-ink-light">{{ u.usuario }}</span></td>
                  <td>
                    <select :value="u.perfil" class="p-field h-8 py-0 text-[12.5px] w-48" :disabled="ocupado" @change="asignar(u, $event.target.value)">
                      <option value="">— Sin puesto —</option>
                      <option v-for="p in m.perfiles" :key="p.nombre" :value="p.nombre">{{ p.nombre }}</option>
                    </select>
                  </td>
                  <td class="p-meta">{{ u.pase_libre ? "Todo" : resumen(u.niveles) }}</td>
                  <td class="p-meta">{{ u.prestamos.length ? u.prestamos.map((x) => `de ${x.de} hasta ${x.hasta}`).join(", ") : "—" }}</td>
                  <td class="text-right"><button v-if="!u.pase_libre" type="button" class="text-[12px] text-brand-600 hover:text-brand-700" @click="verComo(u.nombre, u.niveles)">Ver como…</button></td>
                </tr>
              </tbody>
            </table>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/utils/frappe.js";
import { simular } from "@/composables/useAccesos.js";

const router = useRouter();
const m = ref(null);
const borrador = reactive({});
const cargando = ref(true);
const ocupado = ref(false);
const error = ref("");
const nuevoPerfil = ref("");

const grupos = computed(() => {
  const out = [];
  for (const v of m.value?.vistas || []) {
    let g = out.find((x) => x.grupo === v.grupo);
    if (!g) out.push((g = { grupo: v.grupo, vistas: [] }));
    g.vistas.push(v);
  }
  return out;
});
const limpio = (n) => Object.fromEntries(Object.entries(n || {}).filter(([, v]) => v));
const igual = (a, b) => JSON.stringify(limpio(a)) === JSON.stringify(limpio(b));
const cambiados = computed(() => (m.value?.perfiles || []).filter((p) => !p.pase_libre && !igual(
  Object.fromEntries(Object.keys(borrador[p.nombre] || {}).sort().map((k) => [k, borrador[p.nombre][k]])),
  Object.fromEntries(Object.keys(p.niveles).sort().map((k) => [k, p.niveles[k]])),
)).map((p) => p.nombre));

const resumen = (n) => {
  const ed = Object.values(n).filter((x) => x === "editar").length;
  const ve = Object.values(n).filter((x) => x === "ver").length;
  return ed + ve ? `${ed} editar · ${ve} ver` : "Ninguna";
};

async function cargar() {
  cargando.value = true; error.value = "";
  try {
    m.value = await call("costeo_yelke.api.accesos.get_matriz");
    for (const p of m.value.perfiles) {
      borrador[p.nombre] = Object.fromEntries(m.value.vistas.map((v) => [v.clave, p.niveles[v.clave] || ""]));
    }
  } catch (e) { error.value = e.message || "No se pudieron cargar los accesos."; }
  finally { cargando.value = false; }
}

async function guardar() {
  ocupado.value = true; error.value = "";
  try {
    for (const nombre of cambiados.value) {
      await call("costeo_yelke.api.accesos.guardar_perfil", { perfil: nombre, niveles: JSON.stringify(limpio(borrador[nombre])) });
    }
    await cargar();
  } catch (e) { error.value = e.message || "No se pudieron guardar los cambios."; }
  finally { ocupado.value = false; }
}

async function crearPerfil() {
  if (!nuevoPerfil.value.trim()) return;
  ocupado.value = true; error.value = "";
  try {
    await call("costeo_yelke.api.accesos.crear_perfil", { nombre: nuevoPerfil.value.trim() });
    nuevoPerfil.value = "";
    await cargar();
  } catch (e) { error.value = e.message || "No se pudo crear el puesto."; }
  finally { ocupado.value = false; }
}

async function asignar(u, perfil) {
  ocupado.value = true; error.value = "";
  try {
    await call("costeo_yelke.api.accesos.asignar_perfil", { usuario: u.usuario, perfil: perfil || null });
    await cargar();
  } catch (e) { error.value = e.message || "No se pudo cambiar el puesto."; }
  finally { ocupado.value = false; }
}

/** Vista previa: la app con esos accesos hasta salir del modo (barra de arriba). */
function verComo(etiqueta, niveles) {
  simular(etiqueta, limpio(niveles));
  router.push("/inicio");
}

onMounted(cargar);
</script>
