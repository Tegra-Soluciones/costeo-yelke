<template>
  <div class="flex flex-col h-full">
    <PageHeader title="Productos" subtitle="Catálogo de artículos">
      <div class="flex items-center gap-2">
        <!-- View toggle -->
        <div class="flex items-center bg-gray-100 rounded-md p-0.5 gap-0.5">
          <button
            class="p-1.5 rounded transition-colors"
            :class="viewMode === 'grid' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-400 hover:text-gray-600'"
            @click="viewMode = 'grid'"
            title="Vista de imágenes"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
            </svg>
          </button>
          <button
            class="p-1.5 rounded transition-colors"
            :class="viewMode === 'list' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-400 hover:text-gray-600'"
            @click="viewMode = 'list'"
            title="Vista de lista"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
            </svg>
          </button>
        </div>

        <button
          class="px-3 py-1.5 bg-brand-500 text-white text-sm font-medium rounded-md hover:bg-brand-600 transition-colors flex items-center gap-1.5"
          @click="$router.push('/productos/nuevo')"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Producto
        </button>
      </div>
    </PageHeader>

    <!-- Search bar -->
    <div class="bg-white border-b border-gray-200 px-6 py-2.5 flex items-center gap-3 flex-shrink-0">
      <div class="relative flex-1 max-w-xs">
        <svg class="absolute left-2.5 top-2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="search"
          type="text"
          placeholder="Buscar por código o nombre…"
          class="pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>
      <span class="text-xs text-gray-400 ml-auto">{{ totalVisible }} artículo{{ totalVisible !== 1 ? 's' : '' }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="w-8 h-8 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <!-- Content -->
    <div v-else class="flex-1 overflow-y-auto p-5 space-y-8">

      <!-- Global empty state -->
      <div v-if="totalVisible === 0" class="py-20 text-center text-gray-400">
        <svg class="w-12 h-12 mx-auto mb-3 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10" />
        </svg>
        <p class="text-sm font-medium">Sin productos encontrados</p>
        <button class="mt-3 text-sm text-brand-600 font-medium hover:text-brand-700" @click="$router.push('/productos/nuevo')">
          Crear nuevo producto →
        </button>
      </div>

      <!-- Sections by type -->
      <template v-for="tipo in TIPOS" :key="tipo.group">
        <section v-if="groupedFiltered[tipo.group]?.length">
          <!-- Section header -->
          <div class="flex items-center gap-3 mb-4">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center text-lg flex-shrink-0" :style="`background-color: ${tipo.bg}`">
              {{ tipo.icon }}
            </div>
            <div class="flex-1 min-w-0">
              <h2 class="text-sm font-bold text-gray-800">{{ tipo.label }}</h2>
              <p class="text-xs text-gray-400">{{ groupedFiltered[tipo.group].length }} artículo{{ groupedFiltered[tipo.group].length !== 1 ? 's' : '' }}</p>
            </div>
            <div class="h-px flex-1 bg-gray-100" />
          </div>

          <!-- ── GRID view ── -->
          <div v-if="viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
            <div
              v-for="item in groupedFiltered[tipo.group]"
              :key="item.name"
              class="bg-white rounded-xl border border-gray-200 overflow-hidden hover:border-brand-300 hover:shadow-md transition-all cursor-pointer group"
              @click="$router.push(`/productos/${encodeURIComponent(item.name)}`)"
            >
              <!-- Image area -->
              <div
                class="h-36 flex items-center justify-center overflow-hidden relative"
                :style="`background-color: ${tipo.bg}`"
              >
                <img
                  v-if="item.image"
                  :src="item.image"
                  :alt="item.item_name"
                  class="w-full h-full object-cover"
                  @error="item.image = null"
                />
                <span v-else class="text-4xl opacity-40 select-none">{{ tipo.icon }}</span>

                <!-- Hover overlay -->
                <div class="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors flex items-center justify-center">
                  <div class="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-full p-1.5 shadow">
                    <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                  </div>
                </div>
              </div>

              <!-- Card body -->
              <div class="p-3">
                <p class="text-sm font-semibold text-gray-900 leading-snug line-clamp-2 mb-1">{{ item.item_name }}</p>
                <p class="text-xs font-mono text-gray-400">{{ item.name }}</p>
                <div class="flex items-center justify-between mt-2">
                  <span class="text-xs text-gray-500">{{ item.stock_uom }}</span>
                  <div class="flex gap-1">
                    <span v-if="item.is_stock_item" class="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Inventario" />
                    <span v-if="item.is_sales_item" class="w-1.5 h-1.5 rounded-full bg-blue-400" title="Ventas" />
                    <span v-if="item.is_purchase_item" class="w-1.5 h-1.5 rounded-full bg-orange-400" title="Compras" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ── LIST view ── -->
          <div v-else class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 overflow-hidden">
            <div
              v-for="item in groupedFiltered[tipo.group]"
              :key="item.name"
              class="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer group transition-colors"
              @click="$router.push(`/productos/${encodeURIComponent(item.name)}`)"
            >
              <!-- Thumbnail -->
              <div
                class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden"
                :style="`background-color: ${tipo.bg}`"
              >
                <img
                  v-if="item.image"
                  :src="item.image"
                  :alt="item.item_name"
                  class="w-full h-full object-cover rounded-lg"
                  @error="item.image = null"
                />
                <span v-else class="text-lg leading-none">{{ tipo.icon }}</span>
              </div>

              <!-- Text -->
              <div class="flex-1 min-w-0">
                <p class="text-sm font-semibold text-gray-900 truncate">{{ item.item_name }}</p>
                <p class="text-xs font-mono text-gray-400">{{ item.name }}</p>
              </div>

              <!-- Meta -->
              <div class="flex items-center gap-3 flex-shrink-0">
                <span class="text-xs text-gray-400 hidden sm:block">{{ item.stock_uom }}</span>
                <div class="flex gap-1">
                  <span v-if="item.is_stock_item" class="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Inventario" />
                  <span v-if="item.is_sales_item" class="w-1.5 h-1.5 rounded-full bg-blue-400" title="Ventas" />
                  <span v-if="item.is_purchase_item" class="w-1.5 h-1.5 rounded-full bg-orange-400" title="Compras" />
                </div>
                <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
                </svg>
              </div>
            </div>
          </div>

        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import { db } from "@/utils/frappe.js";

const router = useRouter();

const TIPOS = [
  { group: "Productos Terminados", label: "Productos Terminados", icon: "📦", bg: "#fff4ef" },
  { group: "Sub-Ensamblajes",      label: "Sub-Ensamblajes",      icon: "🔧", bg: "#f0fdf4" },
  { group: "Materia prima",        label: "Materia Prima",        icon: "🧵", bg: "#fffbeb" },
  { group: "Servicios",            label: "Servicios",            icon: "⚙️", bg: "#eff6ff" },
];

const loading   = ref(true);
const items     = ref([]);
const search    = ref("");
const viewMode  = ref("grid");

const filteredItems = computed(() => {
  const q = search.value.toLowerCase();
  if (!q) return items.value;
  return items.value.filter(
    i => (i.item_name || "").toLowerCase().includes(q) || (i.name || "").toLowerCase().includes(q)
  );
});

const groupedFiltered = computed(() => {
  const map = {};
  for (const tipo of TIPOS) map[tipo.group] = [];
  for (const item of filteredItems.value) {
    if (map[item.item_group]) map[item.item_group].push(item);
  }
  return map;
});

const totalVisible = computed(() => filteredItems.value.length);

onMounted(async () => {
  try {
    items.value = await db.getList("Item", {
      fields: ["name", "item_name", "item_group", "stock_uom", "image",
               "is_stock_item", "is_sales_item", "is_purchase_item", "standard_rate"],
      filters: [
        ["item_group", "in", ["Materia prima", "Servicios", "Sub-Ensamblajes", "Productos Terminados"]],
        ["disabled", "=", 0],
      ],
      orderBy: "item_name asc",
      limit: 500,
    });
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
