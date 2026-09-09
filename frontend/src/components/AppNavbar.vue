<template>
  <header class="h-16 bg-white border-b border-surface-border flex items-center px-4 gap-3 flex-shrink-0 z-30">

    <!-- ── Left: breadcrumb ─────────────────────────────────── -->
    <div class="flex-1 flex items-center gap-1.5 min-w-0 text-xs">
      <span class="text-gray-400 font-medium hidden sm:block">{{ section.group }}</span>
      <template v-if="section.page">
        <svg class="w-3 h-3 text-gray-300 flex-shrink-0 hidden sm:block" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
        </svg>
        <span class="font-semibold text-gray-700 truncate">{{ section.page }}</span>
      </template>
    </div>

    <!-- ── Right: actions + user ───────────────────────────── -->
    <div class="flex items-center gap-1">

      <!-- Selector de compañía: filtra toda la app a una sola compañía a la vez -->
      <div
        v-if="companyState.companies.length > 0"
        class="flex items-center gap-1.5 px-2 h-7 bg-gray-50 border border-gray-200 rounded-lg"
        title="Compañía activa -- filtra lo que se muestra en toda la app"
      >
        <svg class="w-3 h-3 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
        <select
          :value="companyState.selected"
          @change="setCompany($event.target.value)"
          class="bg-transparent text-gray-600 text-xs font-medium border-0 focus:outline-none focus:ring-0 py-0 pr-5 cursor-pointer"
        >
          <option v-for="c in companyState.companies" :key="c.name" :value="c.name">{{ c.name }}</option>
        </select>
      </div>

      <!-- Divider -->
      <div class="w-px h-5 bg-gray-200 mx-1 hidden md:block" />

      <!-- ── App launcher ───────────────────────────────────── -->
      <div class="relative" ref="appsRef">
        <button
          title="Apps"
          class="w-8 h-8 flex items-center justify-center rounded-lg transition-colors"
          :class="appsOpen ? 'text-gray-700 bg-gray-100' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
          @click.stop="toggleApps"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
          </svg>
        </button>

        <Transition name="panel">
          <div
            v-if="appsOpen"
            class="absolute right-0 top-full mt-2 w-72 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden z-50"
          >
            <div class="px-4 py-3 border-b border-gray-100">
              <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Apps instaladas</p>
            </div>
            <div class="p-3 grid grid-cols-3 gap-1">
              <a
                v-for="app in apps"
                :key="app.name"
                :href="app.home"
                class="flex flex-col items-center gap-1.5 p-3 rounded-lg hover:bg-gray-50 transition-colors group"
              >
                <!-- Logo or fallback icon -->
                <div class="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center bg-gray-100 group-hover:bg-gray-200 transition-colors flex-shrink-0">
                  <img v-if="app.logo" :src="app.logo" class="w-full h-full object-contain p-1" :alt="app.title" />
                  <svg v-else class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/>
                  </svg>
                </div>
                <span class="text-[11px] font-medium text-gray-600 group-hover:text-gray-900 text-center leading-tight line-clamp-2">{{ app.title }}</span>
              </a>
            </div>
            <!-- Loading state -->
            <div v-if="appsLoading" class="flex items-center justify-center py-8">
              <svg class="w-5 h-5 text-gray-300 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
            </div>
          </div>
        </Transition>
      </div>

      <!-- ── Notifications ──────────────────────────────────── -->
      <div class="relative" ref="notifRef">
        <button
          title="Notificaciones"
          class="relative w-8 h-8 flex items-center justify-center rounded-lg transition-colors"
          :class="notifOpen ? 'text-gray-700 bg-gray-100' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'"
          @click.stop="toggleNotif"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
          <!-- Unread badge -->
          <span
            v-if="data.unread_notifications > 0"
            class="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none"
          >
            {{ data.unread_notifications > 99 ? '99+' : data.unread_notifications }}
          </span>
        </button>

        <Transition name="panel">
          <div
            v-if="notifOpen"
            class="absolute right-0 top-full mt-2 w-96 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden z-50"
          >
            <!-- Header -->
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-gray-800">Notificaciones</p>
                <span v-if="data.unread_notifications > 0" class="px-1.5 py-0.5 text-[10px] font-bold bg-red-100 text-red-600 rounded-full leading-none">
                  {{ data.unread_notifications }}
                </span>
              </div>
              <button
                v-if="data.unread_notifications > 0"
                class="text-xs text-brand-600 hover:text-brand-700 font-medium transition-colors"
                @click="markAllRead"
              >
                Marcar todo leído
              </button>
            </div>

            <!-- Notification list -->
            <div class="overflow-y-auto max-h-[420px] divide-y divide-gray-50">
              <!-- Loading -->
              <div v-if="notifLoading" class="flex items-center justify-center py-10">
                <svg class="w-5 h-5 text-gray-300 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              </div>

              <!-- Empty -->
              <div v-else-if="!notifications.length" class="flex flex-col items-center gap-2 py-12 text-gray-400">
                <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                </svg>
                <p class="text-xs">Sin notificaciones</p>
              </div>

              <!-- Items -->
              <template v-else>
                <a
                  v-for="n in notifications"
                  :key="n.name"
                  :href="n.document_type && n.document_name ? `/app/${slugify(n.document_type)}/${encodeURIComponent(n.document_name)}` : '/app/notification-log'"
                  class="flex gap-3 px-4 py-3 hover:bg-gray-50 transition-colors"
                  :class="n.read ? 'opacity-60' : ''"
                  @click="onNotifClick(n)"
                >
                  <!-- Type indicator dot -->
                  <div class="mt-1 flex-shrink-0">
                    <span class="block w-2 h-2 rounded-full" :class="n.read ? 'bg-gray-300' : typeColor(n.type)"></span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-800 leading-snug line-clamp-2" v-html="n.subject"></p>
                    <p class="text-xs text-gray-400 mt-0.5">{{ timeAgo(n.creation) }}</p>
                  </div>
                </a>
              </template>
            </div>

            <!-- Footer -->
            <div class="border-t border-gray-100 px-4 py-2.5">
              <a href="/app/notification-log" class="text-xs text-brand-600 hover:text-brand-700 font-medium">
                Ver todas las notificaciones →
              </a>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Divider -->
      <div class="w-px h-5 bg-gray-200 mx-1" />

      <!-- ── User menu ───────────────────────────────────────── -->
      <div class="relative" ref="menuRef">
        <button
          class="flex items-center gap-2 px-1.5 h-8 rounded-lg hover:bg-gray-100 transition-colors"
          @click.stop="menuOpen = !menuOpen"
        >
          <!-- Avatar -->
          <div class="w-6 h-6 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center" :style="`background: ${avatarBg}`">
            <img v-if="data.user?.user_image" :src="data.user.user_image" class="w-full h-full object-cover" />
            <span v-else class="text-[10px] font-bold text-white leading-none">{{ initials }}</span>
          </div>
          <!-- Name (hidden on small screens) -->
          <span class="text-sm font-medium text-gray-700 hidden sm:block max-w-[130px] truncate leading-none">
            {{ data.user?.full_name || data.user?.email || '…' }}
          </span>
          <!-- Caret -->
          <svg
            class="w-3 h-3 text-gray-400 transition-transform flex-shrink-0"
            :class="menuOpen ? 'rotate-180' : ''"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <!-- Dropdown panel -->
        <Transition name="panel">
          <div
            v-if="menuOpen"
            class="absolute right-0 top-full mt-2 w-60 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden z-50"
          >
            <!-- User info header -->
            <div class="flex items-center gap-3 px-4 py-3.5 bg-gray-50 border-b border-gray-100">
              <div class="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center" :style="`background: ${avatarBg}`">
                <img v-if="data.user?.user_image" :src="data.user.user_image" class="w-full h-full object-cover" />
                <span v-else class="text-sm font-bold text-white">{{ initials }}</span>
              </div>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-gray-900 truncate">{{ data.user?.full_name }}</p>
                <p class="text-xs text-gray-400 truncate">{{ data.user?.email }}</p>
              </div>
            </div>

            <!-- Menu items -->
            <div class="py-1.5">
              <DropItem :href="`/app/user/${encodeURIComponent(data.user?.name || '')}`">
                <template #icon>
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                </template>
                Mi Perfil
              </DropItem>
              <DropItem href="/app/user-settings">
                <template #icon>
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                </template>
                Configuración
              </DropItem>
            </div>

            <div class="border-t border-gray-100 py-1.5">
              <DropItem @click.prevent="logout" href="#" danger>
                <template #icon>
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                </template>
                Cerrar sesión
              </DropItem>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, defineComponent, h } from "vue";
import { useRoute } from "vue-router";
import { call } from "@/utils/frappe.js";
import { useCompany } from "@/composables/useCompany.js";

const { state: companyState, setCompany } = useCompany();

const route    = useRoute();
const menuRef  = ref(null);
const notifRef = ref(null);
const appsRef  = ref(null);

const menuOpen  = ref(false);
const notifOpen = ref(false);
const appsOpen  = ref(false);

const notifLoading = ref(false);
const appsLoading  = ref(false);

const notifications = ref([]);
const apps          = ref([]);

const data = reactive({
  user: null,
  company: "",
  company_currency: "",
  unread_notifications: 0,
});

// ── Breadcrumb mapping ────────────────────────────────────────────────────────
const ROUTE_MAP = {
  Dashboard:      { group: "Inicio",    page: "Panel de control" },
  CosteoList:     { group: "Costeo",    page: "Pipeline" },
  CosteoNuevo:    { group: "Costeo",    page: "Nuevo Costeo" },
  CosteoDetail:   { group: "Costeo",    page: "Detalle" },
  ProductoList:   { group: "Catálogo",  page: "Productos" },
  ProductoNuevo:  { group: "Catálogo",  page: "Nuevo Producto" },
  ProductoDetail: { group: "Catálogo",  page: "Detalle" },
  Precios:        { group: "Catálogo",  page: "Reglas de Precio" },
  RecordatoriosList: { group: "Ventas", page: "Recordatorios de Precio" },
};

const section = computed(() => ROUTE_MAP[route.name] || { group: "Costeo Yelke", page: "" });

// ── Avatar ────────────────────────────────────────────────────────────────────
const AVATAR_COLORS = ["#f97316", "#3b82f6", "#10b981", "#8b5cf6", "#ec4899", "#0ea5e9"];

const initials = computed(() => {
  const name = data.user?.full_name || data.user?.email || "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
});

const avatarBg = computed(() => {
  const str = data.user?.name || "x";
  const idx = str.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
});

// ── Notification helpers ──────────────────────────────────────────────────────
function typeColor(type) {
  const map = {
    Alert:   "bg-red-400",
    Mention: "bg-blue-400",
    Energy:  "bg-yellow-400",
    Assignment: "bg-purple-400",
    Share:   "bg-green-400",
  };
  return map[type] || "bg-brand-400";
}

function timeAgo(creation) {
  if (!creation) return "";
  const diff = Math.floor((Date.now() - new Date(creation).getTime()) / 1000);
  if (diff < 60)  return "hace un momento";
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
  return `hace ${Math.floor(diff / 86400)} d`;
}

function slugify(doctype) {
  return doctype.toLowerCase().replace(/\s+/g, "-");
}

// ── Panel toggles ─────────────────────────────────────────────────────────────
async function toggleNotif() {
  const next = !notifOpen.value;
  closeAll();
  notifOpen.value = next;
  if (next && !notifications.value.length) {
    notifLoading.value = true;
    try {
      notifications.value = await call("costeo_yelke.api.item_api.get_notifications", { limit: 20 });
    } catch (_) {}
    notifLoading.value = false;
  }
}

async function toggleApps() {
  const next = !appsOpen.value;
  closeAll();
  appsOpen.value = next;
  if (next && !apps.value.length) {
    appsLoading.value = true;
    try {
      apps.value = await call("costeo_yelke.api.item_api.get_frappe_apps");
    } catch (_) {}
    appsLoading.value = false;
  }
}

function closeAll() {
  menuOpen.value  = false;
  notifOpen.value = false;
  appsOpen.value  = false;
}

// ── Mark all read ─────────────────────────────────────────────────────────────
async function markAllRead() {
  try {
    await call("costeo_yelke.api.item_api.mark_notifications_read");
    notifications.value.forEach(n => { n.read = 1; });
    data.unread_notifications = 0;
  } catch (_) {}
}

// ── Notification click ────────────────────────────────────────────────────────
function onNotifClick(n) {
  n.read = 1;
  if (data.unread_notifications > 0) data.unread_notifications--;
  notifOpen.value = false;
}

// ── Dropdown item component ───────────────────────────────────────────────────
const DropItem = defineComponent({
  props: { href: String, danger: Boolean },
  emits: ["click"],
  setup(props, { slots, emit }) {
    return () => {
      const tag = props.href ? "a" : "button";
      const cls = [
        "flex items-center gap-2.5 w-full px-4 py-2 text-sm transition-colors text-left",
        props.danger
          ? "text-red-500 hover:bg-red-50 hover:text-red-600"
          : "text-gray-700 hover:bg-gray-50",
      ].join(" ");
      return h(
        tag,
        {
          class: cls,
          ...(props.href ? { href: props.href } : {}),
          onClick: (e) => emit("click", e),
        },
        [
          slots.icon ? h("span", { class: "text-gray-400 flex-shrink-0" }, slots.icon()) : null,
          h("span", { class: "flex-1" }, slots.default?.()),
        ]
      );
    };
  },
});

// ── Actions ───────────────────────────────────────────────────────────────────
async function logout() {
  closeAll();
  try { await call("logout"); } catch (_) {}
  window.location.href = "/login";
}

// ── Click outside to close all panels ────────────────────────────────────────
function onDocClick(e) {
  const refs = [menuRef.value, notifRef.value, appsRef.value];
  if (refs.every(r => !r || !r.contains(e.target))) {
    closeAll();
  }
}

// ── Load ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  document.addEventListener("click", onDocClick, true);
  try {
    const res = await call("costeo_yelke.api.item_api.get_navbar_data");
    Object.assign(data, res);
  } catch (_) {}
});

onUnmounted(() => {
  document.removeEventListener("click", onDocClick, true);
});
</script>

<style scoped>
.panel-enter-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.panel-leave-active { transition: opacity 0.08s ease, transform 0.08s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }
</style>
