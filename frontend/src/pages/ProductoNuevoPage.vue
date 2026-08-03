<template>
  <div class="flex flex-col h-full">

    <!-- ═══════════════════════════════════════════════════════════════
         STEP 1 — Type Selector
    ════════════════════════════════════════════════════════════════ -->
    <template v-if="step === 1">
      <PageHeader title="Nuevo Producto" subtitle="¿Qué tipo de artículo vas a crear?" back />

      <div class="flex-1 overflow-y-auto flex flex-col items-center justify-center p-8 gap-8">
        <div class="grid grid-cols-2 gap-5 w-full max-w-2xl">
          <button
            v-for="tipo in TIPOS"
            :key="tipo.group"
            class="group flex flex-col items-start gap-3 p-6 bg-white border-2 rounded-xl transition-all hover:shadow-md text-left"
            :class="`hover:border-${tipo.color}-400`"
            :style="`--hover-color: ${tipo.hex}`"
            @click="selectTipo(tipo)"
          >
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
              :style="`background-color: ${tipo.bg}`"
            >
              {{ tipo.icon }}
            </div>
            <div>
              <p class="font-semibold text-gray-900 text-sm mb-1">{{ tipo.label }}</p>
              <p class="text-xs text-gray-500 leading-relaxed">{{ tipo.hint }}</p>
            </div>
            <div class="flex flex-wrap gap-1 mt-1">
              <span
                v-for="tag in tipo.tags"
                :key="tag"
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :style="`background-color: ${tipo.bg}; color: ${tipo.textColor}`"
              >{{ tag }}</span>
            </div>
            <div
              class="absolute inset-0 rounded-xl ring-2 ring-inset opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
              :style="`ring-color: ${tipo.hex}`"
            />
          </button>
        </div>

        <p class="text-xs text-gray-400">
          Podrás ajustar el tipo desde la configuración del artículo una vez creado.
        </p>
      </div>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════
         STEP 2 — Form
    ════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <PageHeader :title="selectedTipo?.label || 'Nuevo Producto'" :subtitle="form.item_code || 'Nuevo artículo'" back @back="step = 1">
        <button
          :disabled="saving"
          class="px-4 py-1.5 bg-brand-500 text-white text-sm font-medium rounded-md hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
          @click="saveItem"
        >
          <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          {{ saving ? "Guardando…" : "Crear Artículo" }}
        </button>
      </PageHeader>

      <!-- Loading -->
      <div v-if="loading" class="flex-1 flex items-center justify-center text-gray-400">
        <svg class="w-7 h-7 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </div>

      <div v-else class="flex-1 overflow-y-auto p-5 flex gap-5">

        <!-- ─── Left: tabs ─────────────────────────────────── -->
        <div class="flex-1 min-w-0 space-y-1">

          <!-- Tab nav -->
          <div class="bg-white rounded-t-lg border border-gray-200 border-b-0 px-4 pt-3 flex gap-1 overflow-x-auto">
            <button
              v-for="tab in visibleTabs"
              :key="tab.key"
              class="px-3 py-2 text-xs font-medium border-b-2 transition-colors -mb-px whitespace-nowrap"
              :class="activeTab === tab.key
                ? 'border-brand-500 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="bg-white rounded-b-lg rounded-tr-lg border border-gray-200 p-6 space-y-6">

            <!-- ── General ── -->
            <div v-if="activeTab === 'general'">
              <SectionTitle>Identificación</SectionTitle>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <FieldLabel>Código de Artículo <Req /></FieldLabel>
                  <input v-model="form.item_code" class="field-input" :class="err('item_code')" placeholder="Ej: YLK-CHA-TIM" />
                  <ErrMsg :v="errors.item_code" />
                </div>
                <div>
                  <FieldLabel>Nombre del Artículo</FieldLabel>
                  <input v-model="form.item_name" class="field-input" placeholder="Nombre descriptivo" />
                </div>
                <div>
                  <FieldLabel>Grupo de Artículo <Req /></FieldLabel>
                  <select v-model="form.item_group" class="field-input" :class="err('item_group')">
                    <option value="">— Seleccionar —</option>
                    <option v-for="g in defaults.item_groups" :key="g.name" :value="g.name">{{ g.name }}</option>
                  </select>
                  <ErrMsg :v="errors.item_group" />
                </div>
                <div>
                  <FieldLabel>Unidad de Medida Predeterminada <Req /></FieldLabel>
                  <select v-model="form.stock_uom" class="field-input" :class="err('stock_uom')">
                    <option value="">— Seleccionar —</option>
                    <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                  </select>
                  <ErrMsg :v="errors.stock_uom" />
                </div>
                <div>
                  <FieldLabel>Marca</FieldLabel>
                  <select v-model="form.brand" class="field-input">
                    <option value="">— Sin marca —</option>
                    <option v-for="b in defaults.brands" :key="b.name" :value="b.name">{{ b.name }}</option>
                  </select>
                </div>
                <div class="flex items-center gap-6 pt-5">
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.disabled" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Deshabilitado</span>
                  </label>
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.is_stock_item" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Mantener inventario</span>
                  </label>
                </div>
              </div>

              <div class="mt-5">
                <FieldLabel>Descripción</FieldLabel>
                <textarea v-model="form.description" rows="4" class="field-input resize-none" placeholder="Descripción detallada del artículo…" />
              </div>

              <SectionTitle class="mt-6">Precio y Peso</SectionTitle>
              <div class="grid grid-cols-3 gap-4">
                <div>
                  <FieldLabel>Precio de Venta Estándar</FieldLabel>
                  <div class="relative">
                    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                    <input v-model.number="form.standard_rate" type="number" min="0" step="0.01" class="field-input pl-6" />
                  </div>
                </div>
                <div>
                  <FieldLabel>Peso por Unidad</FieldLabel>
                  <input v-model.number="form.weight_per_unit" type="number" min="0" step="0.001" class="field-input" />
                </div>
                <div>
                  <FieldLabel>UOM de Peso</FieldLabel>
                  <select v-model="form.weight_uom" class="field-input">
                    <option value="">—</option>
                    <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- ── Unidades de Medida ── -->
            <div v-if="activeTab === 'uom'">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <SectionTitle class="mb-0">Equivalencias de Unidades</SectionTitle>
                  <p class="text-xs text-gray-400 mt-1">
                    UOM base:
                    <span class="font-semibold text-gray-600">{{ form.stock_uom || '(selecciona UOM en General)' }}</span>
                    = 1
                  </p>
                </div>
                <button
                  class="text-xs text-brand-600 font-medium flex items-center gap-1 hover:text-brand-700"
                  :disabled="!form.stock_uom"
                  @click="addUomConversion"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                  </svg>
                  Agregar UOM
                </button>
              </div>

              <p v-if="!form.stock_uom" class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
                ⚠ Primero selecciona la UOM base en la pestaña General
              </p>

              <!-- Stock UOM reference row -->
              <div v-if="form.stock_uom" class="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-lg border border-gray-200 text-sm mb-3">
                <div class="flex-1">
                  <span class="font-semibold text-gray-700">{{ form.stock_uom }}</span>
                  <span class="ml-2 text-xs text-gray-400">(UOM base)</span>
                </div>
                <div class="w-32 text-right text-xs text-gray-400">Factor: <span class="font-semibold text-gray-700">1.000</span></div>
              </div>

              <div v-if="!form.uom_conversions.length && form.stock_uom" class="py-8 text-center text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-lg space-y-1">
                <p class="font-medium">Sin equivalencias adicionales</p>
                <p class="text-xs">Ej: 1 Caja = 12 Piezas</p>
              </div>

              <div v-else class="space-y-2">
                <div
                  v-for="(row, idx) in form.uom_conversions"
                  :key="idx"
                  class="flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg group"
                >
                  <!-- UOM select -->
                  <div class="flex-1">
                    <FieldLabel>Unidad de Medida</FieldLabel>
                    <select v-model="row.uom" class="field-input">
                      <option value="">— Seleccionar —</option>
                      <option
                        v-for="u in defaults.uoms"
                        :key="u.name"
                        :value="u.name"
                        :disabled="u.name === form.stock_uom"
                      >{{ u.name }}{{ u.name === form.stock_uom ? ' (base)' : '' }}</option>
                    </select>
                  </div>
                  <!-- Factor -->
                  <div class="w-44">
                    <FieldLabel>
                      Factor
                      <span class="text-gray-300 font-normal">(1 {{ row.uom || '?' }} = ? {{ form.stock_uom }})</span>
                    </FieldLabel>
                    <input
                      v-model.number="row.conversion_factor"
                      type="number" min="0.0001" step="0.001"
                      class="field-input"
                    />
                  </div>
                  <!-- Delete -->
                  <button
                    class="mt-4 w-7 h-7 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-400 text-gray-300 transition-all flex-shrink-0"
                    @click="form.uom_conversions.splice(idx, 1)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- ── Ventas ── -->
            <div v-if="activeTab === 'ventas'">
              <SectionTitle>Configuración de Ventas</SectionTitle>
              <div class="grid grid-cols-2 gap-4">
                <div class="flex items-center pt-1">
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.is_sales_item" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600 font-medium">Permitir Ventas</span>
                  </label>
                </div>
                <div>
                  <FieldLabel>UOM de Venta Predeterminada</FieldLabel>
                  <select v-model="form.sales_uom" class="field-input" :disabled="!form.is_sales_item">
                    <option value="">— Igual a UOM stock —</option>
                    <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                  </select>
                </div>
                <div>
                  <FieldLabel>Descuento Máximo (%)</FieldLabel>
                  <div class="relative">
                    <input v-model.number="form.max_discount" type="number" min="0" max="100" class="field-input pr-7" :disabled="!form.is_sales_item" />
                    <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">%</span>
                  </div>
                </div>
                <div>
                  <label class="flex items-center gap-2 text-sm cursor-pointer mt-1">
                    <input type="checkbox" v-model="form.enable_deferred_revenue" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Habilitar ingreso diferido</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- ── Compras ── -->
            <div v-if="activeTab === 'compras'">
              <SectionTitle>Configuración de Compras</SectionTitle>
              <div class="grid grid-cols-2 gap-4">
                <div class="flex items-center pt-1">
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.is_purchase_item" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600 font-medium">Permitir Compras</span>
                  </label>
                </div>
                <div>
                  <FieldLabel>UOM de Compra Predeterminada</FieldLabel>
                  <select v-model="form.purchase_uom" class="field-input" :disabled="!form.is_purchase_item">
                    <option value="">— Igual a UOM stock —</option>
                    <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                  </select>
                </div>
                <div>
                  <FieldLabel>Cantidad Mínima de Pedido</FieldLabel>
                  <input v-model.number="form.min_order_qty" type="number" min="0" class="field-input" :disabled="!form.is_purchase_item" />
                </div>
                <div>
                  <FieldLabel>Tiempo de Entrega (días)</FieldLabel>
                  <input v-model.number="form.lead_time_days" type="number" min="0" class="field-input" :disabled="!form.is_purchase_item" />
                </div>
                <div class="col-span-2">
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.is_customer_provided_item" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Artículo proporcionado por cliente</span>
                  </label>
                </div>
                <div v-if="form.is_customer_provided_item" class="col-span-2">
                  <FieldLabel>Cliente</FieldLabel>
                  <LinkInput v-model="form.customer" doctype="Customer" placeholder="Cliente proveedor…" />
                </div>
                <div class="col-span-2">
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.enable_deferred_expense" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Habilitar gasto diferido</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- ── Manufactura ── -->
            <div v-if="activeTab === 'manufactura'">
              <SectionTitle>Manufactura</SectionTitle>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <FieldLabel>BOM Predeterminada</FieldLabel>
                  <LinkInput v-model="form.default_bom" doctype="BOM" placeholder="Lista de materiales…" />
                </div>
                <div class="space-y-3 pt-1">
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.is_sub_contracted_item" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Proporcionar materiales (subcontratado)</span>
                  </label>
                  <label class="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" v-model="form.include_item_in_manufacturing" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600">Incluir en manufactura</span>
                  </label>
                </div>
              </div>

              <SectionTitle class="mt-6">Control de Lotes y Series</SectionTitle>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="flex items-center gap-2 text-sm cursor-pointer mb-3">
                    <input type="checkbox" v-model="form.has_batch_no" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600 font-medium">Tiene Número de Lote</span>
                  </label>
                  <div v-if="form.has_batch_no">
                    <FieldLabel>Serie de Lote</FieldLabel>
                    <input v-model="form.batch_number_series" class="field-input" placeholder="BAT-.YYYY.-" />
                  </div>
                </div>
                <div>
                  <label class="flex items-center gap-2 text-sm cursor-pointer mb-3">
                    <input type="checkbox" v-model="form.has_serial_no" class="rounded border-gray-300 text-brand-500" />
                    <span class="text-gray-600 font-medium">Tiene Número de Serie</span>
                  </label>
                  <div v-if="form.has_serial_no">
                    <FieldLabel>Serie de Número</FieldLabel>
                    <input v-model="form.serial_no_series" class="field-input" placeholder="SN-.YYYY.-" />
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Precios + Reglas ── -->
            <div v-if="activeTab === 'precios'">
              <p class="text-xs text-gray-400 mb-5">Se guardarán al crear el artículo</p>
              <ItemPricesForm
                :prices="form.item_prices"
                :rules="form.pricing_rules"
                :price-lists="defaults.price_lists"
                :currencies="defaults.currencies"
                :uoms="defaults.uoms"
                :item-uoms="form.uom_conversions.filter(r => r.uom)"
                :default-currency="defaults.price_lists[0]?.currency || 'MXN'"
                @addPrice="p => form.item_prices.push(p)"
                @removePrice="idx => form.item_prices.splice(idx, 1)"
                @addRule="r => form.pricing_rules.push(r)"
                @removeRule="idx => form.pricing_rules.splice(idx, 1)"
              />
            </div>

            <!-- ── Proveedores ── -->
            <div v-if="activeTab === 'proveedores'">
              <div class="flex items-center justify-between mb-4">
                <SectionTitle class="mb-0">Proveedores del Artículo</SectionTitle>
                <button class="text-xs text-brand-600 font-medium flex items-center gap-1 hover:text-brand-700" @click="addSupplier">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                  Agregar proveedor
                </button>
              </div>

              <div v-if="!form.supplier_items.length" class="py-10 text-center text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-lg space-y-1">
                <p class="font-medium">Sin proveedores configurados</p>
                <p class="text-xs">Vincula proveedores y sus referencias de pieza para facilitar órdenes de compra.</p>
              </div>

              <div v-else class="space-y-3">
                <div
                  v-for="(row, idx) in form.supplier_items"
                  :key="idx"
                  class="border border-gray-200 rounded-lg p-4 relative group"
                >
                  <button
                    class="absolute top-3 right-3 opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-400 text-gray-300 transition-all"
                    @click="form.supplier_items.splice(idx, 1)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                  </button>
                  <div class="grid grid-cols-2 gap-3">
                    <div class="col-span-2">
                      <FieldLabel>Proveedor <Req /></FieldLabel>
                      <LinkInput v-model="row.supplier" doctype="Supplier" placeholder="Buscar proveedor…" />
                    </div>
                    <div>
                      <FieldLabel>Número de Pieza (Proveedor)</FieldLabel>
                      <input v-model="row.supplier_part_no" class="field-input" placeholder="PN del proveedor" />
                    </div>
                    <div>
                      <FieldLabel>Nombre de Pieza (Proveedor)</FieldLabel>
                      <input v-model="row.supplier_part_name" class="field-input" placeholder="Nombre en catálogo del proveedor" />
                    </div>
                    <div>
                      <FieldLabel>UOM del Proveedor</FieldLabel>
                      <select v-model="row.uom" class="field-input">
                        <option value="">— Stock UOM —</option>
                        <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Configuración por Empresa ── -->
            <div v-if="activeTab === 'empresa'">
              <div class="flex items-center justify-between mb-4">
                <SectionTitle class="mb-0">Configuración por Empresa</SectionTitle>
                <button class="text-xs text-brand-600 font-medium flex items-center gap-1 hover:text-brand-700" @click="addDefault">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                  Agregar empresa
                </button>
              </div>

              <div v-if="!form.item_defaults.length" class="py-8 text-center text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-lg">
                Configura el almacén, lista de precios y centros de costo por empresa
              </div>

              <div v-else class="space-y-4">
                <div
                  v-for="(row, idx) in form.item_defaults"
                  :key="idx"
                  class="border border-gray-200 rounded-lg p-4 relative group"
                >
                  <button
                    class="absolute top-3 right-3 opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-400 text-gray-300 transition-all"
                    @click="form.item_defaults.splice(idx, 1)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                  </button>
                  <div class="grid grid-cols-2 gap-3">
                    <div class="col-span-2">
                      <FieldLabel>Empresa</FieldLabel>
                      <select v-model="row.company" class="field-input">
                        <option value="">— Seleccionar empresa —</option>
                        <option v-for="c in defaults.companies" :key="c.name" :value="c.name">{{ c.name }}</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel>Almacén Predeterminado</FieldLabel>
                      <select v-model="row.default_warehouse" class="field-input">
                        <option value="">— Sin almacén —</option>
                        <option v-for="w in warehousesForCompany(row.company)" :key="w.name" :value="w.name">{{ w.name }}</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel>Lista de Precios</FieldLabel>
                      <select v-model="row.default_price_list" class="field-input">
                        <option value="">— Sin lista —</option>
                        <option v-for="p in defaults.price_lists" :key="p.name" :value="p.name">{{ p.name }}</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel>C. de Costo Compra</FieldLabel>
                      <select v-model="row.buying_cost_center" class="field-input">
                        <option value="">—</option>
                        <option v-for="c in costCentersForCompany(row.company)" :key="c.name" :value="c.name">{{ c.name }}</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel>C. de Costo Venta</FieldLabel>
                      <select v-model="row.selling_cost_center" class="field-input">
                        <option value="">—</option>
                        <option v-for="c in costCentersForCompany(row.company)" :key="c.name" :value="c.name">{{ c.name }}</option>
                      </select>
                    </div>
                    <div class="col-span-2">
                      <FieldLabel>Proveedor Predeterminado</FieldLabel>
                      <LinkInput v-model="row.default_supplier" doctype="Supplier" placeholder="Proveedor…" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Comercio Exterior ── -->
            <div v-if="activeTab === 'exterior'">
              <SectionTitle>Comercio Exterior</SectionTitle>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <FieldLabel>País de Origen</FieldLabel>
                  <LinkInput v-model="form.country_of_origin" doctype="Country" placeholder="País…" />
                </div>
                <div>
                  <FieldLabel>Número de Arancel Aduanero</FieldLabel>
                  <LinkInput v-model="form.customs_tariff_number" doctype="Customs Tariff Number" placeholder="Fracción arancelaria…" />
                </div>
              </div>
            </div>

            <!-- ── CFDI (Mexico Compliance) ── -->
            <div v-if="activeTab === 'cfdi'">
              <SectionTitle>Información CFDI — SAT</SectionTitle>
              <p class="text-xs text-gray-400 mb-4">
                Campos requeridos por el SAT para la emisión de Comprobantes Fiscales Digitales por Internet (CFDI).
              </p>
              <div class="space-y-4">
                <div>
                  <FieldLabel>Clave de Producto o Servicio SAT <Req /></FieldLabel>
                  <LinkInput
                    v-model="form.mx_product_service_key"
                    doctype="SAT Product or Service Key"
                    placeholder="Buscar clave SAT…"
                    :error="!!errors.mx_product_service_key"
                  />
                  <p class="mt-1.5 text-xs text-gray-400">
                    Ejemplo: <code class="bg-gray-100 px-1 rounded">43211500</code> — Tejidos /
                    <code class="bg-gray-100 px-1 rounded">84111500</code> — Manufactura
                  </p>
                  <ErrMsg :v="errors.mx_product_service_key" />
                </div>
              </div>
              <div class="mt-5 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 leading-relaxed">
                <strong class="font-semibold">Clave SAT de UOM:</strong> Se configura en el catálogo de UOM del sistema.
                Desk → Unidades de Medida → edita y asigna <code>mx_uom_key</code>.
              </div>
            </div>

          </div>
        </div>

        <!-- ─── Right sidebar ──────────────────────────────── -->
        <div class="w-56 flex-shrink-0 space-y-4">

          <!-- Type badge -->
          <div
            class="rounded-lg border-2 p-4"
            :style="`background-color: ${selectedTipo?.bg}; border-color: ${selectedTipo?.hex}30`"
          >
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xl leading-none">{{ selectedTipo?.icon }}</span>
              <p class="text-xs font-bold" :style="`color: ${selectedTipo?.textColor}`">{{ selectedTipo?.label }}</p>
            </div>
            <button
              class="mt-2 text-xs font-medium underline underline-offset-2 opacity-60 hover:opacity-100"
              :style="`color: ${selectedTipo?.textColor}`"
              @click="step = 1"
            >
              Cambiar tipo
            </button>
          </div>

          <!-- Summary -->
          <div class="bg-white rounded-lg border border-gray-200 p-4">
            <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Resumen</h3>
            <div class="space-y-2.5 text-sm">
              <div>
                <p class="text-xs text-gray-400">Código</p>
                <p class="font-medium text-gray-900 truncate">{{ form.item_code || '—' }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-400">UOM</p>
                <p class="font-medium text-gray-700">{{ form.stock_uom || '—' }}</p>
              </div>
              <div v-if="form.standard_rate">
                <p class="text-xs text-gray-400">Precio estándar</p>
                <p class="font-semibold text-brand-600">{{ fmtC(form.standard_rate) }}</p>
              </div>
              <div v-if="form.item_prices.length">
                <p class="text-xs text-gray-400">Precios en lista</p>
                <p class="font-medium text-gray-700">{{ form.item_prices.length }}</p>
              </div>
              <div v-if="form.supplier_items.length">
                <p class="text-xs text-gray-400">Proveedores</p>
                <p class="font-medium text-gray-700">{{ form.supplier_items.length }}</p>
              </div>
            </div>
          </div>

          <!-- CFDI status -->
          <div v-if="defaults.has_mexico_compliance" class="bg-white rounded-lg border border-gray-200 p-4">
            <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">CFDI</h3>
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full flex-shrink-0" :class="form.mx_product_service_key ? 'bg-green-400' : 'bg-yellow-400'" />
              <span class="text-xs text-gray-600">
                {{ form.mx_product_service_key ? 'Clave SAT asignada' : 'Pendiente clave SAT' }}
              </span>
            </div>
            <button v-if="!form.mx_product_service_key" class="mt-2 text-xs text-brand-600 hover:text-brand-700 font-medium" @click="activeTab = 'cfdi'">
              Asignar clave →
            </button>
          </div>

          <!-- Quick tab shortcuts -->
          <div class="bg-white rounded-lg border border-gray-200 p-4">
            <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Secciones</h3>
            <div class="space-y-1">
              <button
                v-for="tab in visibleTabs"
                :key="tab.key"
                class="w-full text-left text-xs px-2 py-1.5 rounded transition-colors"
                :class="activeTab === tab.key ? 'bg-brand-50 text-brand-700 font-medium' : 'text-gray-500 hover:bg-gray-50'"
                @click="activeTab = tab.key"
              >
                {{ tab.label }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </template>

    <!-- ── Success modal ──────────────────────────────────── -->
    <div v-if="created" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl shadow-xl p-8 max-w-sm w-full mx-4 text-center">
        <div class="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
          <svg class="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <h2 class="text-lg font-bold text-gray-900 mb-1">¡Artículo creado!</h2>
        <p class="text-sm text-gray-500 mb-6">
          <span class="font-medium text-gray-800">{{ created.item_code }}</span> fue guardado exitosamente.
        </p>
        <div class="flex flex-col gap-2">
          <button class="w-full px-4 py-2 bg-brand-500 text-white text-sm font-medium rounded-md hover:bg-brand-600" @click="openInDesk">
            Ver en Desk
          </button>
          <button class="w-full px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-md hover:bg-gray-50" @click="resetForm">
            Crear otro artículo
          </button>
          <RouterLink to="/productos" class="text-xs text-gray-400 hover:text-gray-600 mt-1">
            Volver al catálogo
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- ── Toast ──────────────────────────────────────────── -->
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
import { RouterLink } from "vue-router";
import PageHeader     from "@/components/PageHeader.vue";
import LinkInput      from "@/components/LinkInput.vue";
import ItemPricesForm from "@/components/ItemPricesForm.vue";
import { call }       from "@/utils/frappe.js";

// ── Micro-components ─────────────────────────────────────────────────────────
const FieldLabel   = defineComponent({ setup(_, { slots }) { return () => h("label", { class: "text-xs font-medium text-gray-500 block mb-1" }, slots.default?.()); } });
const Req          = defineComponent({ setup() { return () => h("span", { class: "text-red-400 ml-0.5" }, "*"); } });
const ErrMsg       = defineComponent({ props: { v: String }, setup(p) { return () => p.v ? h("p", { class: "mt-1 text-xs text-red-500" }, p.v) : null; } });
const SectionTitle = defineComponent({ setup(_, { slots }) { return () => h("h3", { class: "text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4" }, slots.default?.()); } });
// ─────────────────────────────────────────────────────────────────────────────

const TIPOS = [
  {
    label: "Producto Terminado",
    group: "Productos Terminados",
    icon: "📦",
    hint: "Artículos terminados listos para venta. Tienen BOM e inventario.",
    tags: ["Ventas", "Manufactura", "Inventario"],
    isStock: true, isSales: true, isPurchase: false, includeManuf: true,
    isSubContracted: true,
    bg: "#fff4ef", hex: "#f97316", textColor: "#c2410c",
  },
  {
    label: "Materia Prima",
    group: "Materia prima",
    icon: "🧵",
    hint: "Insumos y materiales usados en producción o servicios.",
    tags: ["Compras", "Inventario"],
    isStock: true, isSales: false, isPurchase: true, includeManuf: true,
    bg: "#fffbeb", hex: "#f59e0b", textColor: "#92400e",
  },
  {
    label: "Sub-ensamblaje",
    group: "Sub-Ensamblajes",
    icon: "🔧",
    hint: "Componentes manufacturados internamente que se usan en productos finales.",
    tags: ["Manufactura", "Inventario"],
    isStock: true, isSales: false, isPurchase: false, includeManuf: true,
    isSubContracted: true,
    bg: "#f0fdf4", hex: "#22c55e", textColor: "#166534",
  },
  {
    label: "Servicio",
    group: "Servicios",
    icon: "⚙️",
    hint: "Servicios que se compran o venden. Sin inventario físico.",
    tags: ["Compras", "Sin inventario"],
    isStock: false, isSales: false, isPurchase: true, includeManuf: true,
    bg: "#eff6ff", hex: "#3b82f6", textColor: "#1e40af",
  },
];

const TABS_BASE = [
  { key: "general",     label: "General"       },
  { key: "uom",        label: "Unidades"      },
  { key: "ventas",      label: "Ventas"        },
  { key: "compras",     label: "Compras"       },
  { key: "manufactura", label: "Manufactura"   },
  { key: "precios",     label: "Precios"       },
  { key: "proveedores", label: "Proveedores"   },
  { key: "empresa",     label: "Por Empresa"   },
  { key: "exterior",    label: "Com. Exterior" },
];

// ── State ─────────────────────────────────────────────────────────────────────
const step         = ref(1);
const selectedTipo = ref(null);
const loading      = ref(true);
const saving       = ref(false);
const activeTab    = ref("general");
const defaults     = reactive({
  companies: [], item_groups: [], uoms: [], brands: [],
  warehouses: [], cost_centers: [], price_lists: [], currencies: [],
  default_company: "", has_mexico_compliance: false,
});
const errors = reactive({});
const toast  = reactive({ show: false, msg: "", type: "success" });
const created = ref(null);

function blankForm() {
  return {
    item_code: "", item_name: "", item_group: "", stock_uom: "",
    disabled: false, is_stock_item: true, brand: "", description: "",
    standard_rate: 0, weight_per_unit: 0, weight_uom: "",
    is_sales_item: false, sales_uom: "", max_discount: 0, enable_deferred_revenue: false,
    is_purchase_item: true, purchase_uom: "", min_order_qty: 0, lead_time_days: 0,
    is_customer_provided_item: false, customer: "", enable_deferred_expense: false,
    default_bom: "", is_sub_contracted_item: false, include_item_in_manufacturing: false,
    has_batch_no: false, batch_number_series: "", has_serial_no: false, serial_no_series: "",
    country_of_origin: "", customs_tariff_number: "",
    mx_product_service_key: "",
    item_defaults: [],
    uom_conversions: [],
    item_prices: [],
    pricing_rules: [],
    supplier_items: [],
  };
}

const form = reactive(blankForm());

const visibleTabs = computed(() => {
  if (defaults.has_mexico_compliance) return [...TABS_BASE, { key: "cfdi", label: "CFDI" }];
  return TABS_BASE;
});


// ── Type selection ────────────────────────────────────────────────────────────
function selectTipo(tipo) {
  selectedTipo.value = tipo;
  form.item_group               = tipo.group;
  form.is_stock_item            = tipo.isStock;
  form.is_sales_item            = tipo.isSales;
  form.is_purchase_item         = tipo.isPurchase;
  form.include_item_in_manufacturing = tipo.includeManuf;
  form.is_sub_contracted_item   = tipo.isSubContracted ?? false;
  step.value = 2;
  activeTab.value = "general";
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function err(field) { return errors[field] ? "border-red-400 focus:ring-red-400" : ""; }

function fmtC(v) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0);
}

function warehousesForCompany(company) {
  if (!company) return defaults.warehouses;
  return defaults.warehouses.filter(w => !w.company || w.company === company);
}
function costCentersForCompany(company) {
  if (!company) return defaults.cost_centers;
  return defaults.cost_centers.filter(c => !c.company || c.company === company);
}

// ── Child table helpers ───────────────────────────────────────────────────────
function addDefault() {
  form.item_defaults.push({
    company: defaults.default_company,
    default_warehouse: "", default_price_list: "",
    buying_cost_center: "", selling_cost_center: "", default_supplier: "",
  });
}

function addSupplier() {
  form.supplier_items.push({
    supplier: "", supplier_part_no: "", supplier_part_name: "", uom: "",
  });
}

function addUomConversion() {
  form.uom_conversions.push({ uom: "", conversion_factor: 1 });
}

// ── Validate ──────────────────────────────────────────────────────────────────
function validate() {
  Object.keys(errors).forEach(k => delete errors[k]);
  let ok = true;
  if (!form.item_code.trim()) { errors.item_code  = "Requerido"; ok = false; }
  if (!form.item_group)       { errors.item_group = "Requerido"; ok = false; }
  if (!form.stock_uom)        { errors.stock_uom  = "Requerido"; ok = false; }
  if (defaults.has_mexico_compliance && !form.mx_product_service_key) {
    errors.mx_product_service_key = "Requerido para facturación CFDI";
    ok = false;
  }
  return ok;
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveItem() {
  if (!validate()) {
    showToast("Revisa los campos requeridos marcados en rojo", "error");
    return;
  }
  saving.value = true;
  try {
    const result = await call("costeo_yelke.api.item_api.create_item", { data: JSON.stringify(form) });
    created.value = result;
  } catch (e) {
    showToast(e.message || "Error al crear artículo", "error");
  } finally {
    saving.value = false;
  }
}

function openInDesk() {
  if (created.value) window.open(`/app/item/${encodeURIComponent(created.value.item_code)}`, "_blank");
}

function resetForm() {
  const blank = blankForm();
  Object.keys(blank).forEach(k => { form[k] = blank[k]; });
  created.value = null;
  step.value = 1;
  selectedTipo.value = null;
  activeTab.value = "general";
}

function showToast(msg, type = "success") {
  toast.msg = msg; toast.type = type; toast.show = true;
  setTimeout(() => (toast.show = false), 4000);
}

// ── Load ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const data = await call("costeo_yelke.api.item_api.get_item_form_defaults");
    Object.assign(defaults, data);
  } catch (e) {
    showToast("No se pudieron cargar los datos del formulario", "error");
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.field-input {
  @apply w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white transition-colors;
  @apply disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
