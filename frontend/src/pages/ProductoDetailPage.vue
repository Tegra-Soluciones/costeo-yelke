<template>
  <div class="flex flex-col h-full">
    <PageHeader
      :title="item?.item_name || 'Cargando…'"
      :subtitle="item?.name || ''"
      back
    >
      <a
        v-if="item"
        :href="`/app/item/${encodeURIComponent(item.item_code)}`"
        target="_blank"
        class="px-3 py-1.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors flex items-center gap-1.5"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
        </svg>
        Editar en Desk
      </a>
    </PageHeader>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex-1 flex flex-col items-center justify-center text-gray-400 gap-3">
      <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <p class="text-sm">{{ error }}</p>
      <button class="text-brand-600 text-sm font-medium hover:text-brand-700" @click="$router.back()">Volver</button>
    </div>

    <!-- Content -->
    <div v-else-if="item" class="flex-1 overflow-y-auto p-5 flex gap-5">

      <!-- ─── Left: tabs ─────────────────────────────────── -->
      <div class="flex-1 min-w-0 space-y-1">

        <!-- Tab nav -->
        <div class="bg-white rounded-t-lg border border-gray-200 border-b-0 px-4 pt-3 flex gap-1 overflow-x-auto">
          <button
            v-for="tab in visibleTabs"
            :key="tab.key"
            class="px-3 py-2 text-xs font-medium border-b-2 transition-colors -mb-px whitespace-nowrap flex items-center gap-1.5"
            :class="activeTab === tab.key
              ? 'border-brand-500 text-brand-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
            <span
              v-if="(tab.key === 'general' || tab.key === 'manufactura' || tab.key === 'cfdi') && generalDirty"
              class="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0"
              title="Cambios sin guardar"
            />
            <span
              v-if="tab.key === 'uom' && itemUomRows.length"
              class="px-1.5 py-0.5 rounded-full text-xs leading-none"
              :class="activeTab === 'uom' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-500'"
            >{{ itemUomRows.length }}</span>
            <span
              v-if="tab.key === 'uom' && uomDirty"
              class="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0"
              title="Cambios sin guardar"
            />
            <span
              v-if="tab.key === 'precios' && itemPrices.length"
              class="px-1.5 py-0.5 rounded-full text-xs leading-none"
              :class="activeTab === 'precios' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-500'"
            >{{ itemPrices.length }}</span>
            <span
              v-if="tab.key === 'precios' && pricesDirty"
              class="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0"
              title="Cambios sin guardar"
            />
          </button>
        </div>

        <div class="bg-white rounded-b-lg rounded-tr-lg border border-gray-200 p-6">

          <!-- ── General ── -->
          <div v-if="activeTab === 'general'" class="space-y-5">

            <!-- Save toolbar -->
            <div v-if="generalDirty" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
              <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                Hay cambios sin guardar
              </p>
              <div class="flex items-center gap-2">
                <button
                  class="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs font-medium rounded-lg hover:bg-gray-50"
                  @click="syncFormFromItem(item)"
                >Descartar</button>
                <button
                  :disabled="savingGeneral"
                  class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                  @click="saveGeneral"
                >
                  <svg v-if="savingGeneral" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ savingGeneral ? 'Guardando…' : 'Guardar cambios' }}
                </button>
              </div>
            </div>

            <!-- Read-only code -->
            <div>
              <p class="text-xs text-gray-400 mb-0.5">Código de Artículo</p>
              <p class="text-sm font-mono font-medium text-gray-800">{{ item.item_code }}</p>
            </div>

            <div class="grid grid-cols-2 gap-x-6 gap-y-4">
              <!-- Nombre -->
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">Nombre</label>
                <input v-model="itemForm.item_name" type="text" class="field-input" />
              </div>

              <!-- Grupo -->
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">Grupo</label>
                <select v-model="itemForm.item_group" class="field-input">
                  <option value="">— Seleccionar —</option>
                  <option v-for="g in defaults.item_groups" :key="g.name" :value="g.name">{{ g.name }}</option>
                </select>
              </div>

              <!-- UOM Stock -->
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">UOM Stock</label>
                <select v-model="itemForm.stock_uom" class="field-input">
                  <option value="">— Seleccionar —</option>
                  <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                </select>
              </div>

              <!-- Marca -->
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">Marca</label>
                <select v-model="itemForm.brand" class="field-input">
                  <option value="">— Sin marca —</option>
                  <option v-for="b in defaults.brands" :key="b.name" :value="b.name">{{ b.name }}</option>
                </select>
              </div>

              <!-- Precio estándar -->
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">Precio Estándar</label>
                <input v-model.number="itemForm.standard_rate" type="number" min="0" step="0.01" class="field-input" />
              </div>

              <!-- Peso por unidad -->
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">Peso por Unidad</label>
                <div class="flex gap-2">
                  <input v-model.number="itemForm.weight_per_unit" type="number" min="0" step="0.001" class="field-input flex-1" />
                  <select v-model="itemForm.weight_uom" class="field-input w-28">
                    <option value="">UOM</option>
                    <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Flags -->
            <div class="pt-2 border-t border-gray-100 space-y-2">
              <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Opciones</p>
              <div class="grid grid-cols-2 gap-x-6 gap-y-2.5">
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.is_stock_item" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">Artículo de inventario</span>
                </label>
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.is_sales_item" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">Artículo de ventas</span>
                </label>
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.is_purchase_item" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">Artículo de compras</span>
                </label>
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.include_item_in_manufacturing" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">Incluir en manufactura</span>
                </label>
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.disabled" class="rounded border-gray-300 text-red-500 focus:ring-red-500" />
                  <span class="text-sm text-gray-700">Deshabilitado</span>
                </label>
              </div>
            </div>

            <!-- Descripción -->
            <div class="pt-2 border-t border-gray-100">
              <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 block">Descripción</label>
              <textarea
                v-model="itemForm.description"
                rows="4"
                class="field-input resize-y"
                placeholder="Descripción del artículo…"
              />
            </div>

            <!-- Footer save -->
            <div v-if="generalDirty" class="flex justify-end pt-2">
              <button
                :disabled="savingGeneral"
                class="px-5 py-2.5 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
                @click="saveGeneral"
              >
                <svg v-if="savingGeneral" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ savingGeneral ? 'Guardando…' : 'Guardar artículo' }}
              </button>
            </div>
          </div>

          <!-- ── Unidades de Medida ───────────────────────────────── -->
          <div v-if="activeTab === 'uom'" class="space-y-4">

            <!-- Save toolbar (UOM dirty) -->
            <div v-if="uomDirty" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
              <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                Hay cambios sin guardar
              </p>
              <button
                :disabled="savingUoms"
                class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                @click="saveUoms"
              >
                <svg v-if="savingUoms" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ savingUoms ? 'Guardando…' : 'Guardar unidades' }}
              </button>
            </div>

            <!-- Header row -->
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-sm font-semibold text-gray-800">Tabla de Equivalencias (UOM)</h3>
                <p class="text-xs text-gray-400 mt-0.5">
                  UOM base: <span class="font-semibold text-gray-600">{{ item.stock_uom }}</span> = 1
                </p>
              </div>
              <button
                class="px-3 py-1.5 border border-brand-200 text-brand-600 text-xs font-semibold rounded-lg hover:bg-brand-50 transition-colors flex items-center gap-1"
                @click="addUomRow"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                </svg>
                Agregar UOM
              </button>
            </div>

            <!-- Stock UOM row (read-only reference) -->
            <div class="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-xl border border-gray-200 text-sm">
              <div class="flex-1">
                <span class="font-semibold text-gray-700">{{ item.stock_uom }}</span>
                <span class="ml-2 text-xs text-gray-400">(UOM base / stock)</span>
              </div>
              <div class="w-32 text-right">
                <span class="text-xs text-gray-400">Factor: </span>
                <span class="font-semibold text-gray-700">1.000</span>
              </div>
            </div>

            <!-- Conversion rows -->
            <div v-if="!itemUomRows.length" class="py-10 flex flex-col items-center gap-2.5 border-2 border-dashed border-gray-200 rounded-xl text-gray-400">
              <svg class="w-9 h-9 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
              <div class="text-center">
                <p class="text-sm font-medium text-gray-500">Sin equivalencias adicionales</p>
                <p class="text-xs">El artículo sólo usa <strong>{{ item.stock_uom }}</strong> como unidad</p>
              </div>
              <button class="mt-1 px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600" @click="addUomRow">
                + Agregar UOM
              </button>
            </div>

            <div v-else class="space-y-2">
              <div
                v-for="(row, idx) in itemUomRows"
                :key="idx"
                class="flex items-center gap-3 px-4 py-3 border rounded-xl group transition-colors"
                :class="row._dirty ? 'border-amber-300 bg-amber-50/40' : 'border-gray-200 bg-white hover:border-gray-300'"
              >
                <!-- UOM select -->
                <div class="flex-1">
                  <label class="text-xs text-gray-400 block mb-1">Unidad de Medida</label>
                  <select
                    v-model="row.uom"
                    class="field-input"
                    @change="row._dirty = true"
                  >
                    <option value="">— Seleccionar —</option>
                    <option
                      v-for="u in defaults.uoms"
                      :key="u.name"
                      :value="u.name"
                      :disabled="u.name === item.stock_uom"
                    >{{ u.name }}{{ u.name === item.stock_uom ? ' (base)' : '' }}</option>
                  </select>
                </div>

                <!-- Factor input -->
                <div class="w-44">
                  <label class="text-xs text-gray-400 block mb-1">
                    Factor de conversión
                    <span class="text-gray-300 font-normal">
                      (1 {{ row.uom || '?' }} = ? {{ item.stock_uom }})
                    </span>
                  </label>
                  <input
                    v-model.number="row.conversion_factor"
                    type="number" min="0.0001" step="0.001"
                    class="field-input"
                    @input="row._dirty = true"
                  />
                </div>

                <!-- Delete -->
                <button
                  class="mt-4 w-7 h-7 flex items-center justify-center rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all flex-shrink-0"
                  @click="removeUomRow(idx)"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Footer save -->
            <div v-if="uomDirty" class="flex justify-end pt-4 border-t border-gray-100">
              <button
                :disabled="savingUoms"
                class="px-5 py-2.5 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
                @click="saveUoms"
              >
                <svg v-if="savingUoms" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ savingUoms ? 'Guardando…' : 'Guardar equivalencias' }}
              </button>
            </div>
          </div>

          <!-- ── Precios + Reglas ──────────────────────────────────── -->
          <div v-if="activeTab === 'precios'">
            <!-- Save toolbar (appears when dirty) -->
            <div v-if="anyDirty" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-5">
              <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                Hay cambios sin guardar
              </p>
              <button
                :disabled="savingPrices"
                class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                @click="saveAll"
              >
                <svg v-if="savingPrices" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                <svg v-else class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                </svg>
                {{ savingPrices ? 'Guardando…' : 'Guardar todo' }}
              </button>
            </div>

            <ItemPricesForm
              :prices="itemPrices"
              :rules="itemRules"
              :price-lists="defaults.price_lists"
              :currencies="defaults.currencies"
              :uoms="defaults.uoms"
              :item-uoms="itemUomRows"
              :default-currency="defaultCurrency"
              @addPrice="p => itemPrices.push(p)"
              @removePrice="idx => itemPrices.splice(idx, 1)"
              @addRule="r => itemRules.push(r)"
              @removeRule="idx => itemRules.splice(idx, 1)"
            />

            <!-- Footer save -->
            <div v-if="anyDirty" class="flex justify-end mt-6 pt-5 border-t border-gray-100">
              <button
                :disabled="savingPrices"
                class="px-5 py-2.5 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
                @click="saveAll"
              >
                <svg v-if="savingPrices" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ savingPrices ? 'Guardando…' : 'Guardar precios y reglas' }}
              </button>
            </div>
          </div>

          <!-- ── Manufactura ── -->
          <div v-if="activeTab === 'manufactura'" class="space-y-5">

            <!-- Save toolbar -->
            <div v-if="generalDirty" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
              <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                Hay cambios sin guardar
              </p>
              <div class="flex items-center gap-2">
                <button
                  class="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs font-medium rounded-lg hover:bg-gray-50"
                  @click="syncFormFromItem(item)"
                >Descartar</button>
                <button
                  :disabled="savingGeneral"
                  class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                  @click="saveGeneral"
                >
                  <svg v-if="savingGeneral" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  {{ savingGeneral ? 'Guardando…' : 'Guardar cambios' }}
                </button>
              </div>
            </div>

            <div class="space-y-3">
              <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Opciones de Manufactura</p>
              <div class="grid grid-cols-2 gap-x-6 gap-y-2.5">
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.include_item_in_manufacturing" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">Incluir en manufactura</span>
                </label>
                <label class="flex items-center gap-2.5 cursor-pointer select-none">
                  <input type="checkbox" v-model="itemForm.is_sub_contracted_item" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                  <span class="text-sm text-gray-700">Es artículo subcontratado</span>
                </label>
              </div>
            </div>

            <div v-if="item.default_bom" class="pt-2 border-t border-gray-100">
              <p class="text-xs text-gray-400 mb-0.5">BOM Predeterminada</p>
              <p class="text-sm font-mono font-medium text-gray-800">{{ item.default_bom }}</p>
            </div>

            <div class="pt-2 border-t border-gray-100 space-y-4">
              <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Seguimiento</p>
              <div class="grid grid-cols-2 gap-x-6 gap-y-4">
                <div class="space-y-2">
                  <label class="flex items-center gap-2.5 cursor-pointer select-none">
                    <input type="checkbox" v-model="itemForm.has_batch_no" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                    <span class="text-sm text-gray-700">Tiene número de lote</span>
                  </label>
                  <div v-if="itemForm.has_batch_no">
                    <label class="text-xs font-medium text-gray-500 block mb-1">Serie de lote</label>
                    <input v-model="itemForm.batch_number_series" type="text" class="field-input" placeholder="ej. LOTE-.####" />
                  </div>
                </div>
                <div class="space-y-2">
                  <label class="flex items-center gap-2.5 cursor-pointer select-none">
                    <input type="checkbox" v-model="itemForm.has_serial_no" class="rounded border-gray-300 text-brand-500 focus:ring-brand-500" />
                    <span class="text-sm text-gray-700">Tiene número de serie</span>
                  </label>
                  <div v-if="itemForm.has_serial_no">
                    <label class="text-xs font-medium text-gray-500 block mb-1">Serie</label>
                    <input v-model="itemForm.serial_no_series" type="text" class="field-input" placeholder="ej. SN-.####" />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="generalDirty" class="flex justify-end pt-2">
              <button
                :disabled="savingGeneral"
                class="px-5 py-2.5 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
                @click="saveGeneral"
              >
                {{ savingGeneral ? 'Guardando…' : 'Guardar manufactura' }}
              </button>
            </div>
          </div>

          <!-- ── Proveedores ── -->
          <div v-if="activeTab === 'proveedores'">
            <div v-if="!item.supplier_items?.length" class="py-12 text-center text-gray-400">
              <p class="text-sm">Sin proveedores configurados</p>
              <a :href="`/app/item/${encodeURIComponent(item.item_code)}`" target="_blank" class="mt-2 inline-block text-xs text-brand-600 hover:text-brand-700">
                Configurar en Desk →
              </a>
            </div>
            <table v-else class="w-full text-sm">
              <thead>
                <tr class="border-b border-gray-100">
                  <Th>Proveedor</Th><Th>N° Pieza Prov.</Th><Th>Nombre Pieza Prov.</Th><Th>UOM</Th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="(s, i) in item.supplier_items" :key="i" class="hover:bg-gray-50">
                  <Td class="font-medium">{{ s.supplier }}</Td>
                  <Td class="font-mono text-xs">{{ s.supplier_part_no || '—' }}</Td>
                  <Td>{{ s.supplier_part_name || '—' }}</Td>
                  <Td>{{ s.uom || '—' }}</Td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── Por Empresa ── -->
          <div v-if="activeTab === 'empresa'">
            <div v-if="!item.item_defaults?.length" class="py-12 text-center text-gray-400">
              <p class="text-sm">Sin configuración por empresa</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="(d, i) in item.item_defaults"
                :key="i"
                class="border border-gray-100 rounded-xl p-4 bg-gray-50"
              >
                <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">{{ d.company }}</p>
                <div class="grid grid-cols-2 gap-x-8 gap-y-2">
                  <InfoRow label="Almacén"        :value="d.default_warehouse || '—'" />
                  <InfoRow label="Lista de Precios" :value="d.default_price_list || '—'" />
                  <InfoRow label="C.C. Compra"    :value="d.buying_cost_center || '—'" />
                  <InfoRow label="C.C. Venta"     :value="d.selling_cost_center || '—'" />
                  <InfoRow label="Proveedor Pred." :value="d.default_supplier || '—'" />
                </div>
              </div>
            </div>
          </div>

          <!-- ── CFDI ── -->
          <div v-if="activeTab === 'cfdi'" class="space-y-5">

            <!-- Save toolbar -->
            <div v-if="generalDirty" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
              <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                Hay cambios sin guardar
              </p>
              <button
                :disabled="savingGeneral"
                class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-50"
                @click="saveGeneral"
              >{{ savingGeneral ? 'Guardando…' : 'Guardar cambios' }}</button>
            </div>

            <div>
              <label class="text-xs font-medium text-gray-500 block mb-1">Clave SAT (mx_product_service_key)</label>
              <input v-model="itemForm.mx_product_service_key" type="text" class="field-input" placeholder="ej. 43211508" />
            </div>
            <InfoRow v-if="item.country_of_origin"     label="País de Origen"  :value="item.country_of_origin" />
            <InfoRow v-if="item.customs_tariff_number" label="Arancel Aduanero" :value="item.customs_tariff_number" />
          </div>

        </div>
      </div>

      <!-- ─── Right sidebar ──────────────────────────────── -->
      <div class="w-56 flex-shrink-0 space-y-4">

        <!-- Image -->
        <div
          class="rounded-xl border border-gray-200 overflow-hidden"
          :style="item.image ? '' : `background-color: ${tipoFor(item.item_group)?.bg}`"
        >
          <img v-if="item.image" :src="item.image" :alt="item.item_name" class="w-full h-44 object-cover" />
          <div v-else class="h-44 flex items-center justify-center">
            <span class="text-6xl opacity-30 select-none">{{ tipoFor(item.item_group)?.icon }}</span>
          </div>
        </div>

        <!-- Key info -->
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
            :style="`background-color: ${tipoFor(item.item_group)?.bg}; color: ${tipoFor(item.item_group)?.textColor}`"
          >
            <span>{{ tipoFor(item.item_group)?.icon }}</span>
            <span>{{ item.item_group }}</span>
          </div>

          <div class="space-y-2.5 text-sm pt-1">
            <div>
              <p class="text-xs text-gray-400">UOM</p>
              <p class="font-medium text-gray-700">{{ item.stock_uom }}</p>
            </div>
            <div v-if="item.brand">
              <p class="text-xs text-gray-400">Marca</p>
              <p class="font-medium text-gray-700">{{ item.brand }}</p>
            </div>
            <div v-if="item.standard_rate">
              <p class="text-xs text-gray-400">Precio estándar</p>
              <p class="font-bold text-brand-600">{{ fmtC(item.standard_rate) }}</p>
            </div>
          </div>
        </div>

        <!-- Prices summary (click to open tab) -->
        <div
          class="bg-white rounded-xl border cursor-pointer transition-colors p-4"
          :class="activeTab === 'precios' ? 'border-brand-300 ring-1 ring-brand-200' : 'border-gray-200 hover:border-brand-200'"
          @click="activeTab = 'precios'"
        >
          <div class="flex items-center justify-between mb-2">
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Precios</p>
            <span
              class="text-xs px-2 py-0.5 rounded-full font-semibold"
              :class="(itemPrices.length || itemRules.length) ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-400'"
            >{{ itemPrices.length + itemRules.length }}</span>
          </div>
          <div v-if="itemPrices.length" class="space-y-1.5">
            <div
              v-for="p in itemPrices.slice(0,3)"
              :key="p.name || p._id"
              class="flex items-center justify-between text-xs"
            >
              <span class="text-gray-500 truncate mr-2">{{ p.price_list }}</span>
              <span class="font-semibold text-gray-800 flex-shrink-0">{{ fmtN(p.price_list_rate) }} {{ p.currency }}</span>
            </div>
            <p v-if="itemPrices.length > 3" class="text-xs text-gray-400 text-center pt-1">+ {{ itemPrices.length - 3 }} más</p>
          </div>
          <p v-else class="text-xs text-gray-400">Sin precios configurados</p>
          <p class="text-xs text-brand-600 font-medium mt-2">{{ activeTab === 'precios' ? 'Editando ↑' : 'Ver y editar →' }}</p>
        </div>

        <!-- CFDI status -->
        <div v-if="item.mx_product_service_key !== undefined" class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">CFDI</p>
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full flex-shrink-0" :class="item.mx_product_service_key ? 'bg-green-400' : 'bg-yellow-400'" />
            <span class="text-xs text-gray-600">
              {{ item.mx_product_service_key ? `Clave: ${item.mx_product_service_key}` : 'Sin clave SAT' }}
            </span>
          </div>
        </div>

        <!-- Timestamps -->
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2 text-xs text-gray-400">
          <div v-if="item.creation">
            <p class="font-medium text-gray-500">Creado</p>
            <p>{{ fmtDate(item.creation) }}</p>
          </div>
          <div v-if="item.modified">
            <p class="font-medium text-gray-500">Modificado</p>
            <p>{{ fmtDate(item.modified) }}</p>
          </div>
        </div>

      </div>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div
        v-if="toast.show"
        class="fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg"
        :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'"
      >
        {{ toast.msg }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, defineComponent, h } from "vue";
import PageHeader     from "@/components/PageHeader.vue";
import ItemPricesForm from "@/components/ItemPricesForm.vue";
import { call }       from "@/utils/frappe.js";

const props = defineProps({ name: { type: String, required: true } });

// ── Micro-components ─────────────────────────────────────────────────────────
const InfoRow = defineComponent({
  props: { label: String, value: String, mono: Boolean },
  setup(p, { slots }) {
    return () => h("div", {}, [
      h("p", { class: "text-xs text-gray-400 mb-0.5" }, p.label),
      slots.default
        ? slots.default()
        : h("p", { class: `text-sm font-medium text-gray-800 ${p.mono ? 'font-mono' : ''}` }, p.value ?? "—"),
    ]);
  },
});
const Th = defineComponent({ setup(_, { slots }) { return () => h("th", { class: "text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-4" }, slots.default?.()); } });
const Td = defineComponent({ props: { class: String }, setup(p, { slots }) { return () => h("td", { class: `py-2.5 pr-4 text-sm text-gray-700 ${p.class || ''}` }, slots.default?.()); } });
// ─────────────────────────────────────────────────────────────────────────────

const TIPOS = [
  { group: "Productos Terminados", icon: "📦", bg: "#fff4ef", textColor: "#c2410c" },
  { group: "Sub-Ensamblajes",      icon: "🔧", bg: "#f0fdf4", textColor: "#166534" },
  { group: "Materia prima",        icon: "🧵", bg: "#fffbeb", textColor: "#92400e" },
  { group: "Servicios",            icon: "⚙️", bg: "#eff6ff", textColor: "#1e40af" },
];

const loading        = ref(true);
const error          = ref(null);
const item           = ref(null);
const activeTab      = ref("general");
const savingPrices   = ref(false);
const savingUoms     = ref(false);
const savingGeneral  = ref(false);
const toast          = reactive({ show: false, msg: "", type: "success" });

const defaults = reactive({
  price_lists: [], currencies: [], uoms: [], item_groups: [], brands: [],
});

// Editable form for General + Manufactura fields
const itemForm = reactive({
  item_name: "", item_group: "", stock_uom: "", brand: "",
  standard_rate: 0, weight_per_unit: 0, weight_uom: "",
  description: "",
  is_stock_item: false, is_sales_item: false, is_purchase_item: false,
  include_item_in_manufacturing: false, is_sub_contracted_item: false, disabled: false,
  has_batch_no: false, batch_number_series: "", has_serial_no: false, serial_no_series: "",
  mx_product_service_key: "",
});
const itemFormOriginal = ref({});

const itemPrices   = ref([]);
const itemRules    = ref([]);
const itemUomRows  = ref([]); // {uom, conversion_factor, _dirty}

const defaultCurrency = computed(() =>
  defaults.price_lists[0]?.currency || "MXN"
);

const TABS_BASE = [
  { key: "general",     label: "General"     },
  { key: "uom",        label: "Unidades"    },
  { key: "precios",     label: "Precios"     },
  { key: "manufactura", label: "Manufactura" },
  { key: "proveedores", label: "Proveedores" },
  { key: "empresa",     label: "Por Empresa" },
];

const visibleTabs = computed(() => {
  const tabs = [...TABS_BASE];
  if (item.value?.mx_product_service_key !== undefined) {
    tabs.push({ key: "cfdi", label: "CFDI" });
  }
  return tabs;
});

const pricesDirty = computed(() =>
  itemPrices.value.some(r => r._dirty) || itemRules.value.some(r => r._dirty)
);
const uomDirty = computed(() => itemUomRows.value.some(r => r._dirty));
const generalDirty = computed(() => {
  const orig = itemFormOriginal.value;
  return Object.keys(itemForm).some(k => itemForm[k] !== orig[k]);
});
const anyDirty = computed(() => pricesDirty.value || uomDirty.value);

// ── Helpers ───────────────────────────────────────────────────────────────────
function tipoFor(group) { return TIPOS.find(t => t.group === group); }

function fmtC(v) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0);
}
function fmtN(v) {
  return new Intl.NumberFormat("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0);
}
function fmtDate(s) {
  if (!s) return "";
  return new Date(s).toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

// ── UOM conversion table ──────────────────────────────────────────────────────
function addUomRow() {
  itemUomRows.value.push({ uom: "", conversion_factor: 1, _dirty: true });
}
function removeUomRow(idx) {
  itemUomRows.value.splice(idx, 1);
}

async function saveUoms() {
  savingUoms.value = true;
  try {
    const payload = itemUomRows.value
      .filter(r => r.uom)
      .map(r => ({ uom: r.uom, conversion_factor: r.conversion_factor || 1 }));
    await call("costeo_yelke.api.item_api.save_item_uoms", {
      item_code: props.name,
      uoms: JSON.stringify(payload),
    });
    // Refresh from server
    const fresh = await call("costeo_yelke.api.item_api.get_item", { item_code: props.name });
    itemUomRows.value = (fresh.uom_conversions || []).map(r => ({ ...r, _dirty: false }));
    showToast(`Guardado: ${payload.length} equivalencia${payload.length !== 1 ? 's' : ''}`, "success");
  } catch (e) {
    showToast(e.message || "Error al guardar equivalencias", "error");
  } finally {
    savingUoms.value = false;
  }
}

// ── Save general item fields ──────────────────────────────────────────────────
async function saveGeneral() {
  savingGeneral.value = true;
  try {
    const payload = { ...itemForm };
    await call("costeo_yelke.api.item_api.update_item", {
      item_code: props.name,
      data: JSON.stringify(payload),
    });
    // Refresh item from server
    const fresh = await call("costeo_yelke.api.item_api.get_item", { item_code: props.name });
    Object.assign(item.value, fresh);   // update in-place to preserve Vue reactive tracking
    syncFormFromItem(fresh);
    showToast("Artículo actualizado", "success");
  } catch (e) {
    showToast(e.message || "Error al guardar", "error");
  } finally {
    savingGeneral.value = false;
  }
}

function syncFormFromItem(src) {
  Object.keys(itemForm).forEach(k => {
    if (!(k in src)) return;          // key absent from server response → keep current
    const v = src[k];
    if (v === null || v === undefined) {
      // null from Frappe → clear to type-appropriate empty
      itemForm[k] = typeof itemForm[k] === "number" ? 0 : typeof itemForm[k] === "boolean" ? false : "";
    } else if (typeof itemForm[k] === "boolean") {
      // Frappe returns 0/1 for checkboxes; coerce to real JS boolean for v-model
      itemForm[k] = !!v;
    } else {
      itemForm[k] = v;
    }
  });
  itemFormOriginal.value = { ...itemForm };
}

// ── Save prices + rules ────────────────────────────────────────────────────────
async function saveAll() {
  savingPrices.value = true;
  try {
    const pricePayload = itemPrices.value.map(r => ({
      name: r.name, price_list: r.price_list, price_list_rate: r.price_list_rate,
      currency: r.currency, uom: r.uom, valid_from: r.valid_from, valid_upto: r.valid_upto,
      customer: r.customer, supplier: r.supplier, note: r.note,
    }));
    const rulesPayload = itemRules.value.map(r => ({
      name: r.name, selling: r.selling ? 1 : 0, buying: r.buying ? 1 : 0,
      disable: r.disable ? 1 : 0, min_qty: r.min_qty, max_qty: r.max_qty,
      rate_or_discount: r.rate_or_discount, rate: r.rate,
      discount_percentage: r.discount_percentage, discount_amount: r.discount_amount,
      currency: r.currency, for_price_list: r.for_price_list,
      customer: r.customer, valid_from: r.valid_from, valid_upto: r.valid_upto,
    }));

    const [pRes, rRes] = await Promise.all([
      call("costeo_yelke.api.item_api.save_item_prices",  { item_code: props.name, prices: JSON.stringify(pricePayload) }),
      call("costeo_yelke.api.item_api.save_pricing_rules", { item_code: props.name, rules: JSON.stringify(rulesPayload) }),
    ]);

    // Refresh from server
    const fresh = await call("costeo_yelke.api.item_api.get_item", { item_code: props.name });
    itemPrices.value = (fresh.item_prices   || []).map(p => ({ ...p, _dirty: false }));
    itemRules.value  = (fresh.pricing_rules || []).map(r => ({ ...r, _dirty: false }));

    const total = (pRes.saved || 0) + (rRes.saved || 0);
    showToast(`Guardado: ${pRes.saved} precio${pRes.saved !== 1 ? 's' : ''} · ${rRes.saved} regla${rRes.saved !== 1 ? 's' : ''}`, "success");
  } catch (e) {
    showToast(e.message || "Error al guardar", "error");
  } finally {
    savingPrices.value = false;
  }
}

function showToast(msg, type = "success") {
  toast.msg = msg; toast.type = type; toast.show = true;
  setTimeout(() => (toast.show = false), 3500);
}

// ── Load ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [itemData, formDefaults] = await Promise.all([
      call("costeo_yelke.api.item_api.get_item", { item_code: props.name }),
      call("costeo_yelke.api.item_api.get_item_form_defaults"),
    ]);
    item.value = itemData;
    defaults.price_lists  = formDefaults.price_lists  || [];
    defaults.currencies   = formDefaults.currencies   || [];
    defaults.uoms         = formDefaults.uoms         || [];
    defaults.item_groups  = formDefaults.item_groups  || [];
    defaults.brands       = formDefaults.brands       || [];
    itemPrices.value   = (itemData.item_prices    || []).map(p => ({ ...p, _dirty: false }));
    itemRules.value    = (itemData.pricing_rules  || []).map(r => ({ ...r, _dirty: false }));
    itemUomRows.value  = (itemData.uom_conversions || []).map(r => ({ ...r, _dirty: false }));
    syncFormFromItem(itemData);
  } catch (e) {
    error.value = e.message || "No se pudo cargar el artículo";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.field-input {
  @apply w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white transition-colors;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
