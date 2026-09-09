<template>
  <DocumentListPage
    title="Recordatorios de Precio"
    subtitle="Avisos de vigencia de precios acordados con clientes"
    :stats="stats"
    :loading="loading"
    :rows="filtered"
    v-model:search="search"
    search-placeholder="Buscar cliente o artículo…"
    :show-clear="!!(filterEstado || search)"
    empty-label="No hay recordatorios"
    empty-icon="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
    @clear="filterEstado = ''; search = ''"
  >
    <template #filters>
      <select v-model="filterEstado" class="h-8 px-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500">
        <option value="">Todos los estados</option>
        <option value="Pendiente">Pendiente</option>
        <option value="Enviado">Enviado</option>
        <option value="Descartado">Descartado</option>
      </select>
    </template>

    <template #head>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Cliente</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Artículo</th>
      <th class="text-right py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Precio acordado</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Vigente hasta</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Aviso</th>
      <th class="text-left py-3 pr-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
      <th class="text-right py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Acciones</th>
    </template>

    <template #row="{ row: r }">
      <td class="py-3 pr-3">
        <p class="font-semibold text-gray-800 text-xs">{{ r.customer_name || r.customer }}</p>
        <p v-if="r.costeo" class="text-xs text-gray-400">{{ r.costeo }}</p>
      </td>
      <td class="py-3 pr-3 text-xs text-gray-600 truncate max-w-[200px]">{{ r.item_name || r.item_code }}</td>
      <td class="py-3 pr-3 text-xs text-gray-700 text-right tabular-nums">{{ fmtMoney(r.price_list_rate) }}</td>
      <td class="py-3 pr-3 text-xs" :class="venceClass(r)">{{ fmtDate(r.valid_upto) }}</td>
      <td class="py-3 pr-3 text-xs text-gray-500">{{ r.tipo_aviso }}</td>
      <td class="py-3 pr-3">
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold" :class="estadoClass(r.estado)">
          {{ r.estado }}
        </span>
        <p v-if="r.enviado_email_el || r.enviado_whatsapp_el" class="text-[10px] text-gray-400 mt-0.5">
          {{ r.enviado_email_el ? 'correo' : '' }}{{ r.enviado_email_el && r.enviado_whatsapp_el ? ' · ' : '' }}{{ r.enviado_whatsapp_el ? 'WhatsApp' : '' }}
        </p>
      </td>
      <td class="py-3 text-right whitespace-nowrap">
        <button
          v-if="r.estado !== 'Enviado'"
          class="text-[11px] font-semibold text-green-700 hover:text-green-800 px-2 py-1 rounded hover:bg-green-50 disabled:opacity-40"
          :disabled="busy === r.name"
          @click.stop="setEstado(r, 'Enviado')"
        >Marcar enviado</button>
        <button
          v-if="r.estado !== 'Descartado'"
          class="text-[11px] font-semibold text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100 disabled:opacity-40"
          :disabled="busy === r.name"
          @click.stop="setEstado(r, 'Descartado')"
        >Descartar</button>
        <button
          v-if="r.estado !== 'Pendiente'"
          class="text-[11px] font-semibold text-brand-600 hover:text-brand-700 px-2 py-1 rounded hover:bg-brand-50 disabled:opacity-40"
          :disabled="busy === r.name"
          @click.stop="setEstado(r, 'Pendiente')"
        >Reabrir</button>
      </td>
    </template>
  </DocumentListPage>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import DocumentListPage from "@/components/DocumentListPage.vue";
import { call } from "@/utils/frappe.js";

const loading = ref(true);
const rows = ref([]);
const search = ref("");
const filterEstado = ref("");
const busy = ref("");

const filtered = computed(() => {
  let list = rows.value;
  if (filterEstado.value) list = list.filter((r) => r.estado === filterEstado.value);
  if (search.value) {
    const q = search.value.toLowerCase();
    list = list.filter((r) =>
      (r.customer_name || r.customer || "").toLowerCase().includes(q) ||
      (r.item_name || r.item_code || "").toLowerCase().includes(q));
  }
  return list;
});

const stats = computed(() => {
  const all = rows.value;
  const hoy = new Date().toISOString().slice(0, 10);
  return [
    { label: "Total", value: all.length, color: "#1e293b" },
    { label: "Pendientes", value: all.filter((r) => r.estado === "Pendiente").length, color: "#f59e0b" },
    { label: "Vencidos sin atender", value: all.filter((r) => r.estado === "Pendiente" && r.valid_upto && r.valid_upto < hoy).length, color: "#ef4444" },
  ];
});

function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtMoney(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function venceClass(r) {
  if (!r.valid_upto || r.estado !== "Pendiente") return "text-gray-600";
  const hoy = new Date().toISOString().slice(0, 10);
  return r.valid_upto < hoy ? "text-red-600 font-semibold" : "text-gray-600";
}
function estadoClass(estado) {
  return {
    Pendiente: "bg-amber-100 text-amber-700",
    Enviado: "bg-green-100 text-green-700",
    Descartado: "bg-gray-100 text-gray-400",
  }[estado] || "bg-gray-100 text-gray-500";
}

async function setEstado(r, estado) {
  busy.value = r.name;
  try {
    await call("costeo_yelke.api.item_api.marcar_recordatorio", { recordatorio: r.name, estado });
    r.estado = estado;
  } catch (e) {
    console.error(e);
    alert(e.message || "No se pudo actualizar el recordatorio");
  } finally {
    busy.value = "";
  }
}

async function load() {
  loading.value = true;
  try { rows.value = await call("costeo_yelke.api.item_api.get_recordatorios", { limit: 300 }) || []; }
  catch (e) { console.error(e); }
  finally { loading.value = false; }
}

onMounted(load);
</script>
