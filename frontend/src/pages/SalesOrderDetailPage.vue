<template>
  <div class="flex flex-col min-h-0">

    <!-- Header -->
    <PageHeader
      :title="isNew ? 'Nueva Orden de Venta' : (so.name || 'Cargando…')"
      :subtitle="isNew ? 'Nueva orden de venta' : (so.customer_name || so.customer || '')"
      back
    >
      <template v-if="!isNew">
        <!-- Print -->
        <button class="btn-icon" title="Imprimir" @click="openPrint">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
          </svg>
        </button>

        <!-- Actions for confirmed SO (docstatus=1) -->
        <template v-if="so.docstatus === 1">
          <!-- Crear OC -->
          <button
            :disabled="!!(acting === 'makeOC')"
            class="px-3 py-1.5 bg-amber-500 text-white text-sm font-semibold rounded-md hover:bg-amber-600 flex items-center gap-1.5 transition-colors disabled:opacity-50"
            @click="showOCModal = true"
          >
            <svg v-if="acting === 'makeOC'" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            {{ acting === 'makeOC' ? 'Creando…' : 'Crear OC' }}
          </button>
          <!-- Crear Factura -->
          <button
            :disabled="!!(acting === 'makeFactura')"
            class="px-3 py-1.5 bg-purple-600 text-white text-sm font-semibold rounded-md hover:bg-purple-700 flex items-center gap-1.5 transition-colors disabled:opacity-50"
            @click="makeInvoice"
          >
            <svg v-if="acting === 'makeFactura'" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            {{ acting === 'makeFactura' ? 'Creando…' : 'Crear Factura' }}
          </button>
          <!-- Enviar -->
          <button
            class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
            @click="showSendModal = true"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
            Enviar
          </button>
          <div class="w-px h-5 bg-gray-200" />
        </template>

        <div class="w-px h-5 bg-gray-200" />
        <a
          :href="`/app/sales-order/${encodeURIComponent(so.name)}`"
          target="_blank"
          class="px-3 py-1.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 flex items-center gap-1.5"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
          Desk
        </a>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <!-- Main -->
    <div v-else class="p-5 pb-40 flex gap-5 items-start">

      <!-- Left: Form -->
      <div class="flex-1 min-w-0 space-y-4">

        <!-- Status bar -->
        <div v-if="!isNew" class="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-2.5">
          <StatusBadge :docstatus="so.docstatus" :status="so.status" />
          <span class="text-xs text-gray-300">·</span>
          <span class="text-xs font-mono text-gray-400">{{ so.name }}</span>
          <div class="flex-1" />
          <span v-if="form.delivery_date" class="text-xs" :class="isOverdue(form.delivery_date, so.docstatus) ? 'text-red-500 font-medium' : 'text-gray-400'">
            Entrega: {{ fmtDate(form.delivery_date) }}
          </span>
        </div>

        <!-- Dirty bar -->
        <div v-if="isDirty && canEdit" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5">
          <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
            Cambios sin guardar
          </p>
          <div class="flex items-center gap-2">
            <button v-if="!isNew" class="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs font-medium rounded-lg hover:bg-gray-50" @click="discardChanges">Descartar</button>
            <button :disabled="saving" class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="save">
              <svg v-if="saving" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {{ saving ? 'Guardando…' : 'Guardar' }}
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div class="bg-white rounded-t-xl border border-gray-200 border-b-0 px-4 pt-3 flex gap-1">
          <button
            v-for="tab in TABS" :key="tab.key"
            class="px-3 py-2 text-xs font-medium border-b-2 transition-colors -mb-px whitespace-nowrap"
            :class="activeTab === tab.key ? 'border-brand-500 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700'"
            @click="activeTab = tab.key"
          >{{ tab.label }}
            <span v-if="tab.key === 'items'" class="ml-1 px-1.5 py-0.5 rounded-full text-xs" :class="activeTab==='items' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-500'">{{ form.items.length }}</span>
          </button>
        </div>

        <div class="bg-white rounded-b-xl rounded-tr-xl border border-gray-200 p-6">

          <!-- General tab -->
          <div v-if="activeTab === 'general'" class="space-y-5">
            <div class="grid grid-cols-2 gap-x-6 gap-y-4">

              <div>
                <label class="field-label">Cliente <span class="text-red-400">*</span></label>
                <select v-model="form.customer" :disabled="!canEdit" class="field-input">
                  <option value="">— Seleccionar cliente —</option>
                  <option v-for="c in defaults.customers" :key="c.name" :value="c.name">{{ c.nombre_comercial || c.customer_name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Empresa <span class="text-red-400">*</span></label>
                <input v-model="form.company" type="text" :disabled="!canEdit" class="field-input" placeholder="Empresa" />
              </div>

              <div>
                <label class="field-label">Tipo de Orden</label>
                <select v-model="form.order_type" :disabled="!canEdit" class="field-input">
                  <option value="Sales">Ventas</option>
                  <option value="Maintenance">Mantenimiento</option>
                  <option value="Shopping Cart">Carrito</option>
                </select>
              </div>

              <div>
                <label class="field-label">Fecha <span class="text-red-400">*</span></label>
                <input v-model="form.transaction_date" type="date" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Fecha de Entrega <span class="text-red-400">*</span></label>
                <input v-model="form.delivery_date" type="date" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">OC del Cliente</label>
                <input v-model="form.po_no" type="text" :disabled="!canEdit" class="field-input" placeholder="Número de orden de compra" />
              </div>

              <div>
                <label class="field-label">Moneda</label>
                <select v-model="form.currency" :disabled="!canEdit" class="field-input">
                  <option v-for="c in defaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Lista de Precios</label>
                <select v-model="form.selling_price_list" :disabled="!canEdit" class="field-input">
                  <option value="">— Sin lista —</option>
                  <option v-for="pl in defaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Impuestos y Cargos</label>
                <select v-model="form.taxes_and_charges" :disabled="!canEdit" class="field-input">
                  <option value="">— Sin plantilla —</option>
                  <option v-for="t in defaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Email de contacto</label>
                <input v-model="form.contact_email" type="email" :disabled="!canEdit" class="field-input" placeholder="correo@cliente.com" />
              </div>

              <div>
                <label class="field-label">WhatsApp / Móvil</label>
                <input v-model="form.contact_mobile" type="tel" :disabled="!canEdit" class="field-input" placeholder="+52 55 1234 5678" />
              </div>

            </div>

            <div v-if="!isNew" class="pt-4 border-t border-gray-100">
              <AttachmentsPanel doctype="Sales Order" :docname="so.name" />
            </div>
          </div>

          <!-- Items tab -->
          <div v-if="activeTab === 'items'" class="space-y-4">
            <div class="overflow-x-auto">
              <table class="w-full text-sm min-w-[760px]">
                <thead>
                  <tr class="border-b border-gray-100">
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-10">#</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3">Artículo</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-24">Cant.</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-24">UOM</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-32">Precio</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-20">Desc %</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-32">Importe</th>
                    <th v-if="canEdit" class="w-8 pb-3"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="(row, idx) in form.items" :key="idx" class="group" :class="row._dirty ? 'bg-amber-50/20' : ''">
                    <td class="py-3 pr-3 text-xs text-gray-400">{{ idx + 1 }}</td>
                    <td class="py-3 pr-3">
                      <div class="flex items-start gap-2.5">
                        <div class="w-10 h-10 rounded-lg flex-shrink-0 overflow-hidden bg-gray-100 border border-gray-200">
                          <img v-if="row.image" :src="row.image" :alt="row.item_name" class="w-full h-full object-cover" @error="row.image = ''" />
                          <div v-else class="w-full h-full flex items-center justify-center">
                            <svg class="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>
                          </div>
                        </div>
                        <div class="flex-1 space-y-1 min-w-0">
                          <input v-if="canEdit" v-model="row.item_code" type="text" list="item-datalist" class="field-input text-xs" placeholder="Código de artículo" @change="fillItemDefaults(row)" />
                          <span v-else class="font-medium text-gray-800 text-xs block">{{ row.item_code }}</span>
                          <p v-if="row.item_name && row.item_name !== row.item_code" class="text-xs text-gray-400 truncate">{{ row.item_name }}</p>
                        </div>
                      </div>
                    </td>
                    <td class="py-3 pr-3">
                      <input v-if="canEdit" v-model.number="row.qty" type="number" min="0.001" step="any" class="field-input text-xs w-20" @input="recalcRow(row); row._dirty=true" />
                      <span v-else class="text-gray-800 text-xs">{{ row.qty }}</span>
                    </td>
                    <td class="py-3 pr-3">
                      <select v-if="canEdit" v-model="row.uom" class="field-input text-xs w-24" @change="row._dirty=true">
                        <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                      </select>
                      <span v-else class="text-gray-600 text-xs">{{ row.uom }}</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <input v-if="canEdit" v-model.number="row.rate" type="number" min="0" step="any" class="field-input text-xs text-right w-28" @input="recalcRow(row); row._dirty=true" />
                      <span v-else class="font-medium text-gray-800 text-xs">{{ fmtN(row.rate) }}</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <input v-if="canEdit" v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.1" class="field-input text-xs text-right w-16" @input="recalcRow(row); row._dirty=true" />
                      <span v-else class="text-gray-600 text-xs">{{ row.discount_percentage || 0 }}%</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <span class="font-semibold text-gray-800 text-xs">{{ fmtN(row.amount) }}</span>
                    </td>
                    <td v-if="canEdit" class="py-3">
                      <button class="w-6 h-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all" @click="form.items.splice(idx, 1)">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!form.items.length">
                    <td :colspan="canEdit ? 8 : 7" class="py-10 text-center text-gray-400 text-sm">Sin artículos. {{ canEdit ? 'Agrega artículos abajo.' : '' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <datalist id="item-datalist">
              <option v-for="item in itemIndex" :key="item.name" :value="item.name">{{ item.item_name }}</option>
            </datalist>

            <button v-if="canEdit" class="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:border-brand-400 hover:text-brand-600 transition-colors w-full justify-center" @click="addItem">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
              Agregar artículo
            </button>

            <div v-if="canEdit || form.additional_discount_percentage" class="flex items-center gap-4 pt-3 border-t border-gray-100">
              <label class="text-xs text-gray-500">Descuento adicional (%)</label>
              <input v-model.number="form.additional_discount_percentage" type="number" min="0" max="100" step="0.1" :disabled="!canEdit" class="field-input w-24 text-right text-xs" />
            </div>
          </div>

          <!-- Términos tab -->
          <div v-if="activeTab === 'terminos'" class="space-y-4">
            <div>
              <label class="field-label">Plantilla de Términos</label>
              <select v-model="form.tc_name" :disabled="!canEdit" class="field-input" @change="loadTermsText">
                <option value="">— Sin plantilla —</option>
                <option v-for="t in defaults.terms_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="field-label">Términos y Condiciones</label>
              <textarea v-model="form.terms" :disabled="!canEdit" rows="8" class="field-input resize-y" placeholder="Términos y condiciones…" />
            </div>
          </div>

        </div>

        <!-- Bottom action bar (draft only) -->
        <div v-if="canEdit" class="flex items-center justify-between gap-3">
          <div>
            <button
              v-if="!isNew && so.docstatus === 0"
              :disabled="!!(acting || saving)"
              class="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50"
              @click="cancelSO"
            >
              Cancelar OV
            </button>
          </div>
          <div class="flex items-center gap-3">
            <button
              v-if="!isNew"
              :disabled="!!(saving || acting)"
              class="px-5 py-2 border border-gray-200 text-gray-600 text-sm font-medium rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-2"
              @click="save"
            >
              <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {{ saving ? 'Guardando…' : 'Guardar borrador' }}
            </button>
            <button
              :disabled="!!(saving || acting)"
              class="px-5 py-2 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
              @click="doConfirm"
            >
              <svg v-if="saving || acting === 'confirm'" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              {{ saving ? 'Guardando…' : acting === 'confirm' ? 'Confirmando…' : 'Confirmar OV' }}
            </button>
          </div>
        </div>

        <!-- Cancel button for submitted SO -->
        <div v-if="!isNew && so.docstatus === 1" class="flex justify-end">
          <button
            :disabled="acting === 'cancel'"
            class="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50"
            @click="cancelSO"
          >
            Cancelar OV
          </button>
        </div>

      </div>

      <!-- Right sidebar -->
      <div class="w-60 flex-shrink-0 space-y-4 sticky top-5 self-start max-h-[calc(100vh-80px)] overflow-y-auto">

        <!-- Totals -->
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Totales</p>
          <div class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span class="font-medium text-gray-800">{{ fmtC(totals.subtotal) }}</span>
          </div>
          <div v-if="form.additional_discount_percentage" class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Descuento ({{ form.additional_discount_percentage }}%)</span>
            <span class="text-red-600 font-medium">-{{ fmtC(totals.discountAmount) }}</span>
          </div>
          <div v-if="so.total_taxes_and_charges" class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Impuestos</span>
            <span class="font-medium text-gray-800">{{ fmtC(so.total_taxes_and_charges) }}</span>
          </div>
          <div class="flex justify-between items-center text-base font-bold border-t border-gray-100 pt-2.5 mt-1">
            <span class="text-gray-800">Total</span>
            <span class="text-brand-600">{{ fmtC(totals.grand) }} <span class="text-xs font-normal text-gray-400">{{ form.currency }}</span></span>
          </div>
        </div>

        <!-- Contact -->
        <div v-if="form.customer" class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Contacto</p>
          <p class="text-sm font-semibold text-gray-800">{{ customerDisplayName }}</p>
          <div v-if="form.contact_email" class="flex items-center gap-2">
            <svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
            <span class="text-xs text-gray-600 truncate">{{ form.contact_email }}</span>
          </div>
          <div v-if="form.contact_mobile" class="flex items-center gap-2">
            <svg class="w-3.5 h-3.5 text-green-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
            <button v-if="!isNew" class="text-xs text-green-600 hover:text-green-700 font-medium truncate" @click="openWhatsApp">{{ form.contact_mobile }}</button>
            <span v-else class="text-xs text-gray-600 truncate">{{ form.contact_mobile }}</span>
          </div>
        </div>

        <!-- Status & dates -->
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5 text-sm">
          <div v-if="!isNew">
            <p class="text-xs text-gray-400">Estado</p>
            <StatusBadge :docstatus="so.docstatus" :status="so.status" class="mt-0.5" />
          </div>
          <div v-if="form.transaction_date">
            <p class="text-xs text-gray-400">Fecha</p>
            <p class="font-medium text-gray-700">{{ fmtDate(form.transaction_date) }}</p>
          </div>
          <div v-if="form.delivery_date">
            <p class="text-xs text-gray-400">Fecha de Entrega</p>
            <p class="font-medium" :class="isOverdue(form.delivery_date, so.docstatus) ? 'text-red-500' : 'text-gray-700'">{{ fmtDate(form.delivery_date) }}</p>
          </div>
          <div v-if="form.selling_price_list">
            <p class="text-xs text-gray-400">Lista de Precios</p>
            <p class="font-medium text-gray-700 text-xs">{{ form.selling_price_list }}</p>
          </div>
        </div>

        <!-- Items summary -->
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Artículos ({{ form.items.length }})</p>
          <div class="space-y-2 max-h-52 overflow-y-auto">
            <div v-for="(row, i) in form.items" :key="i" class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-md flex-shrink-0 bg-gray-100 overflow-hidden border border-gray-200">
                <img v-if="row.image" :src="row.image" :alt="row.item_name" class="w-full h-full object-cover" @error="row.image=''" />
                <div v-else class="w-full h-full flex items-center justify-center"><span class="text-xs text-gray-300">·</span></div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-700 truncate font-medium">{{ row.item_name || row.item_code }}</p>
                <p class="text-xs text-gray-400">{{ row.qty }} {{ row.uom }}</p>
              </div>
            </div>
            <p v-if="!form.items.length" class="text-xs text-gray-400">Sin artículos</p>
          </div>
          <button v-if="canEdit" class="mt-2 w-full text-xs text-brand-600 hover:text-brand-700 font-medium text-center py-1" @click="activeTab = 'items'">
            {{ form.items.length ? 'Editar artículos' : '+ Agregar artículos' }}
          </button>
        </div>

        <!-- Timestamps -->
        <div v-if="!isNew" class="bg-white rounded-xl border border-gray-200 p-4 space-y-2 text-xs text-gray-400">
          <div v-if="so.creation"><p class="font-medium text-gray-500">Creada</p><p>{{ fmtDatetime(so.creation) }}</p></div>
          <div v-if="so.modified"><p class="font-medium text-gray-500">Modificada</p><p>{{ fmtDatetime(so.modified) }}</p></div>
        </div>

      </div>
    </div>

    <!-- ── Email Modal ─────────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showEmailModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="showEmailModal = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 class="text-base font-semibold text-gray-800">Enviar por correo</h3>
              <button class="w-7 h-7 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-400" @click="showEmailModal = false">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="px-6 py-4 space-y-4">
              <div><label class="field-label">Para <span class="text-red-400">*</span></label><input v-model="emailForm.to" type="email" class="field-input" placeholder="correo@cliente.com" /></div>
              <div><label class="field-label">CC</label><input v-model="emailForm.cc" type="text" class="field-input" /></div>
              <div><label class="field-label">Asunto</label><input v-model="emailForm.subject" type="text" class="field-input" /></div>
              <div><label class="field-label">Mensaje</label><textarea v-model="emailForm.message" rows="5" class="field-input resize-y" /></div>
              <label class="flex items-center gap-2 cursor-pointer">
                <input v-model="emailForm.attach_pdf" type="checkbox" class="w-4 h-4 rounded text-brand-600" />
                <span class="text-sm text-gray-700">Adjuntar PDF</span>
              </label>
            </div>
            <div class="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button class="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50" @click="showEmailModal = false">Cancelar</button>
              <button :disabled="sendingEmail || !emailForm.to" class="px-5 py-2 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 disabled:opacity-50 flex items-center gap-2" @click="sendEmail">
                <svg v-if="sendingEmail" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                {{ sendingEmail ? 'Enviando…' : 'Enviar correo' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── WhatsApp Modal ────────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showWAModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="showWAModal = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div class="flex items-center gap-2.5">
                <svg class="w-5 h-5 text-green-500" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                <h3 class="text-base font-semibold text-gray-800">Enviar por WhatsApp</h3>
              </div>
              <button class="w-7 h-7 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-400" @click="showWAModal = false">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="px-6 py-4 space-y-4">
              <div><label class="field-label">Número <span class="text-red-400">*</span></label><input v-model="waPhone" type="tel" class="field-input" placeholder="+52 55 1234 5678" /></div>
              <div><label class="field-label">Mensaje</label><textarea v-model="waMessage" rows="4" class="field-input resize-y text-sm" /></div>
              <div class="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-700">
                <p class="font-semibold mb-1">📎 Adjuntar PDF:</p>
                <ol class="list-decimal ml-4 space-y-0.5"><li>Clic en <strong>Enviar</strong> — se descarga el PDF y abre WhatsApp Web</li><li>Usa el botón adjuntar (📎) y selecciona el PDF</li></ol>
              </div>
            </div>
            <div class="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button class="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50" @click="showWAModal = false">Cancelar</button>
              <button :disabled="!waPhone.trim()" class="px-5 py-2 bg-green-500 text-white text-sm font-semibold rounded-xl hover:bg-green-600 disabled:opacity-50" @click="sendWhatsApp">Enviar</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── Send Picker Modal ──────────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showSendModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="showSendModal = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 class="text-base font-semibold text-gray-800">Enviar orden de venta</h3>
              <button class="w-7 h-7 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-400" @click="showSendModal = false">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="px-6 py-5 space-y-3">
              <button class="w-full flex items-center gap-4 px-4 py-3.5 border border-gray-200 rounded-xl hover:border-brand-400 hover:bg-brand-50 transition-colors text-left group" @click="showSendModal = false; showEmailModal = true">
                <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-200 transition-colors">
                  <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                </div>
                <div><p class="text-sm font-semibold text-gray-800">Correo electrónico</p><p class="text-xs text-gray-400 mt-0.5">Enviar PDF adjunto por email</p></div>
              </button>
              <button class="w-full flex items-center gap-4 px-4 py-3.5 border border-gray-200 rounded-xl hover:border-green-400 hover:bg-green-50 transition-colors text-left group" @click="showSendModal = false; openWhatsApp()">
                <div class="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0 group-hover:bg-green-200 transition-colors">
                  <svg class="w-5 h-5 text-green-600" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                </div>
                <div><p class="text-sm font-semibold text-gray-800">WhatsApp</p><p class="text-xs text-gray-400 mt-0.5">Abrir WhatsApp Web con mensaje</p></div>
              </button>
              <button class="w-full flex items-center gap-4 px-4 py-3.5 border border-gray-200 rounded-xl hover:border-gray-400 hover:bg-gray-50 transition-colors text-left group" @click="showSendModal = false; openPrint()">
                <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 group-hover:bg-gray-200 transition-colors">
                  <svg class="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
                </div>
                <div><p class="text-sm font-semibold text-gray-800">Imprimir / PDF</p><p class="text-xs text-gray-400 mt-0.5">Ver vista previa de impresión</p></div>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── Crear OC Modal (supplier picker) ─────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showOCModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="showOCModal = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 class="text-base font-semibold text-gray-800">Crear Orden de Compra</h3>
              <button class="w-7 h-7 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-400" @click="showOCModal = false">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="px-6 py-5 space-y-4">
              <p class="text-sm text-gray-500">Se creará una OC con los artículos de esta orden de venta (<strong>{{ so.name }}</strong>).</p>
              <div>
                <label class="text-xs font-medium text-gray-500 block mb-1">Proveedor <span class="text-red-400">*</span></label>
                <select v-model="ocSupplier" class="w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500">
                  <option value="">— Seleccionar proveedor —</option>
                  <option v-for="s in ocSuppliers" :key="s.name" :value="s.name">{{ s.supplier_name }}</option>
                </select>
              </div>
            </div>
            <div class="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button class="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50" @click="showOCModal = false">Cancelar</button>
              <button
                :disabled="!ocSupplier || acting === 'makeOC'"
                class="px-5 py-2 bg-amber-500 text-white text-sm font-semibold rounded-xl hover:bg-amber-600 disabled:opacity-50 flex items-center gap-2"
                @click="makePO"
              >
                <svg v-if="acting === 'makeOC'" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                {{ acting === 'makeOC' ? 'Creando…' : 'Crear OC' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="toast.show" class="fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg" :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'">
        {{ toast.msg }}
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, defineComponent, h } from "vue";
import { useRouter, useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import AttachmentsPanel from "@/components/AttachmentsPanel.vue";
import { call, defaultPrintFormat } from "@/utils/frappe.js";

const props  = defineProps({ name: { type: String, default: "" } });
const router = useRouter();
const route  = useRoute();

// ── StatusBadge ──────────────────────────────────────────────────────────────
const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = {
      "Draft": "Borrador", "To Deliver and Bill": "Por Entregar/Facturar",
      "To Bill": "Por Facturar", "To Deliver": "Por Entregar",
      "Completed": "Completada", "Cancelled": "Cancelada",
    };
    const STATUS_COLOR = {
      "To Deliver and Bill": "bg-blue-100 text-blue-700",
      "To Bill": "bg-purple-100 text-purple-700",
      "To Deliver": "bg-amber-100 text-amber-700",
      "Completed": "bg-green-100 text-green-700",
    };
    return () => {
      const ds  = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Confirmada");
      const cls   = ds === 0 ? "bg-gray-100 text-gray-600" : ds === 2 ? "bg-gray-100 text-gray-400" : (STATUS_COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

const TABS = [
  { key: "general",  label: "General" },
  { key: "items",    label: "Artículos" },
  { key: "terminos", label: "Términos" },
];

const loading      = ref(true);
const saving       = ref(false);
const acting       = ref("");
const sendingEmail = ref(false);
const activeTab    = ref("general");
const toast        = reactive({ show: false, msg: "", type: "success" });

const showEmailModal = ref(false);
const showWAModal    = ref(false);
const showSendModal  = ref(false);
const showOCModal    = ref(false);
const ocSupplier     = ref("");
const ocSuppliers    = ref([]);

const waPhone   = ref("");
const waMessage = ref("");

const emailForm = reactive({ to: "", cc: "", subject: "", message: "", attach_pdf: true });

const isNew = computed(() => !props.name || props.name === "nueva");

const so = reactive({
  name: "", docstatus: 0, status: "", creation: "", modified: "",
  total_taxes_and_charges: 0, customer_name: "",
});

const form = reactive({
  name: "", customer: "", company: "",
  transaction_date: "", delivery_date: "", order_type: "Sales",
  currency: "MXN", selling_price_list: "", conversion_rate: 1,
  taxes_and_charges: "", additional_discount_percentage: 0,
  discount_amount: 0, apply_discount_on: "Grand Total",
  tc_name: "", terms: "", customer_address: "", shipping_address_name: "",
  contact_person: "", contact_email: "", contact_mobile: "", po_no: "",
  items: [],
});
const formOriginal = ref({});

const defaults = reactive({
  customers: [], price_lists: [], currencies: [], tax_templates: [],
  terms_templates: [], warehouses: [], uoms: [],
  default_currency: "MXN", default_price_list: "",
});

const itemIndex = ref([]);

// ── Computed ─────────────────────────────────────────────────────────────────
const canEdit = computed(() => isNew.value || so.docstatus === 0);

const isDirty = computed(() => {
  const orig = formOriginal.value;
  if (!orig || !Object.keys(orig).length) return isNew.value;
  const keys = ["customer","company","transaction_date","delivery_date","order_type",
    "currency","selling_price_list","taxes_and_charges","additional_discount_percentage",
    "tc_name","terms","contact_email","contact_mobile","po_no"];
  if (!keys.every(k => (form[k] ?? "") === (orig[k] ?? ""))) return true;
  if (form.items.length !== (orig.items || []).length) return true;
  return form.items.some(r => r._dirty);
});

const customerDisplayName = computed(() => {
  const c = defaults.customers.find(c => c.name === form.customer);
  return c?.nombre_comercial || c?.customer_name || form.customer;
});

const totals = computed(() => {
  const subtotal = form.items.reduce((s, r) => s + (r.amount || 0), 0);
  const discountAmount = subtotal * (form.additional_discount_percentage || 0) / 100;
  const taxes = isNew.value ? 0 : (so.total_taxes_and_charges || 0);
  return { subtotal, discountAmount, grand: subtotal - discountAmount + taxes };
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function fmtN(v) { return new Intl.NumberFormat("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0); }
function fmtDate(s) {
  if (!s) return "—";
  const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtDatetime(s) { if (!s) return ""; return new Date(s).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
function isOverdue(dateStr, docstatus) { if (!dateStr || docstatus !== 1) return false; return new Date(dateStr + "T23:59:59") < new Date(); }
function today() { return new Date().toISOString().split("T")[0]; }
function addDays(n) { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split("T")[0]; }
function showToast(msg, type = "success") { toast.msg = msg; toast.type = type; toast.show = true; setTimeout(() => (toast.show = false), 3500); }

// ── Items ─────────────────────────────────────────────────────────────────────
function addItem() {
  form.items.push({
    item_code: "", item_name: "", description: "", image: "",
    qty: 1, uom: "", stock_uom: "", conversion_factor: 1,
    rate: 0, price_list_rate: 0, discount_percentage: 0,
    discount_amount: 0, amount: 0, net_amount: 0,
    delivery_date: form.delivery_date || addDays(7),
    warehouse: "", item_tax_template: "", _dirty: true,
  });
  activeTab.value = "items";
}

function recalcRow(row) {
  const base = (row.rate || 0) * (row.qty || 1);
  row.amount = base - base * (row.discount_percentage || 0) / 100;
}

async function fillItemDefaults(row) {
  if (!row.item_code) return;
  row._dirty = true;
  try {
    const res = await call("costeo_yelke.api.sales_order_api.get_item_details_for_so", {
      item_code: row.item_code, price_list: form.selling_price_list || "",
    });
    if (res) {
      row.item_name       = res.item_name       || row.item_code;
      row.description     = res.description     || "";
      row.stock_uom       = res.stock_uom       || "";
      row.uom             = res.uom             || res.stock_uom || "";
      row.rate            = res.rate            || 0;
      row.price_list_rate = res.price_list_rate || 0;
      row.image           = res.image           || "";
      recalcRow(row);
    }
  } catch { /* ignore */ }
}

async function loadItemIndex() {
  try {
    const items = await call("frappe.client.get_list", {
      doctype: "Item", fields: ["name", "item_name"],
      filters: [["disabled", "=", 0]], limit_page_length: 500, order_by: "item_name asc",
    });
    itemIndex.value = items || [];
  } catch { /* non-critical */ }
}

// ── Sync ──────────────────────────────────────────────────────────────────────
function syncFromSO(data) {
  Object.assign(so, {
    name: data.name, docstatus: data.docstatus, status: data.status,
    creation: data.creation, modified: data.modified,
    total_taxes_and_charges: data.total_taxes_and_charges || 0,
    customer_name: data.customer_name || "",
  });
  const scalars = ["customer","company","transaction_date","delivery_date","order_type",
    "currency","selling_price_list","conversion_rate","taxes_and_charges",
    "additional_discount_percentage","discount_amount","apply_discount_on",
    "tc_name","terms","customer_address","shipping_address_name",
    "contact_person","contact_email","contact_mobile","po_no"];
  scalars.forEach(k => {
    const v = data[k];
    form[k] = v !== null && v !== undefined ? v : (typeof form[k] === "number" ? 0 : "");
  });
  form.items = (data.items || []).map(r => ({ ...r, image: r.image || "", _dirty: false }));
  form.name  = data.name;
  formOriginal.value = JSON.parse(JSON.stringify({ ...form }));
}

function discardChanges() {
  if (formOriginal.value && Object.keys(formOriginal.value).length) {
    const saved = formOriginal.value;
    Object.keys(form).forEach(k => { if (k !== "items") form[k] = saved[k] ?? form[k]; });
    form.items = (saved.items || []).map(r => ({ ...r, _dirty: false }));
  }
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function save() {
  saving.value = true;
  let ok = false;
  try {
    const deliveryDate = form.delivery_date || addDays(7);
    const payload = {
      name: isNew.value ? "" : form.name,
      customer: form.customer, company: form.company,
      transaction_date: form.transaction_date, delivery_date: deliveryDate,
      order_type: form.order_type, currency: form.currency,
      selling_price_list: form.selling_price_list, conversion_rate: form.conversion_rate || 1,
      taxes_and_charges: form.taxes_and_charges,
      additional_discount_percentage: form.additional_discount_percentage || 0,
      apply_discount_on: form.apply_discount_on || "Grand Total",
      tc_name: form.tc_name, terms: form.terms,
      customer_address: form.customer_address, contact_email: form.contact_email,
      contact_mobile: form.contact_mobile, po_no: form.po_no,
      items: form.items.map(r => ({
        item_code: r.item_code, item_name: r.item_name, description: r.description,
        qty: r.qty, uom: r.uom, conversion_factor: r.conversion_factor || 1,
        rate: r.rate, discount_percentage: r.discount_percentage || 0,
        warehouse: r.warehouse, delivery_date: r.delivery_date || deliveryDate,
      })),
    };
    const saved = await call("costeo_yelke.api.sales_order_api.save_sales_order", {
      data: JSON.stringify(payload),
    });
    syncFromSO(saved);
    showToast(isNew.value ? "Orden creada" : "Orden guardada");
    if (isNew.value) router.replace(`/ordenes-venta/${encodeURIComponent(saved.name)}`);
    ok = true;
  } catch (e) {
    showToast(e.message || "Error al guardar", "error");
  } finally {
    saving.value = false;
  }
  return ok;
}

async function doConfirm() {
  if (isDirty.value || isNew.value) {
    const saved = await save();
    if (!saved) return;
  }
  if (so.docstatus !== 0) return;
  acting.value = "confirm";
  try {
    const res = await call("costeo_yelke.api.sales_order_api.submit_sales_order", { name: so.name });
    Object.assign(so, { docstatus: res.docstatus, status: res.status });
    showToast("Orden de venta confirmada");
  } catch (e) {
    showToast(e.message || "Error al confirmar", "error");
  } finally {
    acting.value = "";
  }
}

async function cancelSO() {
  if (!confirm("¿Cancelar esta orden de venta?")) return;
  acting.value = "cancel";
  try {
    const res = await call("costeo_yelke.api.sales_order_api.cancel_sales_order", { name: so.name });
    Object.assign(so, { docstatus: res.docstatus, status: res.status });
    showToast("Orden cancelada");
  } catch (e) {
    showToast(e.message || "Error al cancelar", "error");
  } finally {
    acting.value = "";
  }
}

// ── Print ─────────────────────────────────────────────────────────────────────
async function openPrint() {
  const fmt = await defaultPrintFormat("Sales Order");
  window.open(`/printview?doctype=Sales+Order&name=${encodeURIComponent(so.name)}&format=${encodeURIComponent(fmt)}&no_letterhead=0`, "_blank");
}

// ── Email ─────────────────────────────────────────────────────────────────────
function prepareEmailForm() {
  emailForm.to      = form.contact_email || "";
  emailForm.cc      = "";
  emailForm.subject = `Orden de Venta ${so.name} - ${customerDisplayName.value}`;
  emailForm.message = `Estimado cliente,\n\nAdjunto encontrará la orden de venta ${so.name} por un total de ${fmtC(totals.value?.grand || 0)} ${form.currency}.\n\nQuedo a sus órdenes.\n\nSaludos`;
  emailForm.attach_pdf = true;
}

async function sendEmail() {
  if (!emailForm.to) return;
  sendingEmail.value = true;
  try {
    const recipients = emailForm.cc
      ? [emailForm.to, ...emailForm.cc.split(",").map(e => e.trim()).filter(Boolean)]
      : [emailForm.to];
    await call("costeo_yelke.api.quotation_api.send_quotation_email", {
      name: so.name, recipients: JSON.stringify(recipients),
      subject: emailForm.subject,
      message: emailForm.message.replace(/\n/g, "<br>"),
      print_format: "Standard", attach_pdf: emailForm.attach_pdf ? 1 : 0,
    });
    showToast("Correo enviado");
    showEmailModal.value = false;
  } catch (e) {
    showToast(e.message || "Error al enviar", "error");
  } finally {
    sendingEmail.value = false;
  }
}

// ── WhatsApp ──────────────────────────────────────────────────────────────────
function openWhatsApp() {
  waPhone.value   = form.contact_mobile || "";
  waMessage.value = `Hola, le comparto la orden de venta *${so.name}* por un total de *${fmtC(totals.value?.grand || 0)} ${form.currency}*.\n\nAdjunto el PDF con el detalle.`;
  showWAModal.value = true;
}

function sendWhatsApp() {
  const phone = waPhone.value.replace(/[^0-9]/g, "");
  if (!phone) return;
  const pdfUrl = `/api/method/frappe.utils.print_format.download_pdf?doctype=Sales+Order&name=${encodeURIComponent(so.name)}&format=Standard&no_letterhead=0`;
  const a = document.createElement("a"); a.href = pdfUrl; a.download = `${so.name}.pdf`; a.click();
  setTimeout(() => window.open(`https://wa.me/${phone}?text=${encodeURIComponent(waMessage.value)}`, "_blank"), 500);
  showWAModal.value = false;
  showToast("PDF descargado — adjúntalo en WhatsApp");
}

// ── Crear OC ──────────────────────────────────────────────────────────────────
async function loadSuppliers() {
  if (ocSuppliers.value.length) return;
  try {
    const rows = await call("frappe.client.get_list", {
      doctype: "Supplier", fields: ["name","supplier_name"],
      filters: [["disabled","=",0]], limit_page_length: 200, order_by: "supplier_name asc",
    });
    ocSuppliers.value = rows || [];
  } catch { /* ignore */ }
}

watch(showOCModal, async (v) => { if (v) { ocSupplier.value = ""; await loadSuppliers(); } });

async function makePO() {
  if (!ocSupplier.value) return;
  showOCModal.value = false;
  acting.value = "makeOC";
  try {
    const res = await call("costeo_yelke.api.purchase_order_api.make_purchase_order_from_sales_order", {
      sales_order_name: so.name, supplier: ocSupplier.value,
    });
    showToast("Orden de compra creada");
    setTimeout(() => router.push(`/ordenes-compra/${encodeURIComponent(res.name)}`), 800);
  } catch (e) {
    showToast(e.message || "Error al crear OC", "error");
  } finally {
    acting.value = "";
  }
}

// ── Crear Factura ─────────────────────────────────────────────────────────────
async function makeInvoice() {
  acting.value = "makeFactura";
  try {
    const res = await call("costeo_yelke.api.sales_invoice_api.make_sales_invoice_from_so", {
      sales_order_name: so.name,
    });
    showToast("Factura creada");
    setTimeout(() => router.push(`/facturas/${encodeURIComponent(res.name)}`), 800);
  } catch (e) {
    showToast(e.message || "Error al crear factura", "error");
  } finally {
    acting.value = "";
  }
}

// ── Terms ─────────────────────────────────────────────────────────────────────
async function loadTermsText() {
  if (!form.tc_name) return;
  try {
    const doc = await call("frappe.client.get_value", { doctype: "Terms and Conditions", filters: { name: form.tc_name }, fieldname: "terms" });
    if (doc?.terms) form.terms = doc.terms;
  } catch { /* ignore */ }
}

// ── Mount ─────────────────────────────────────────────────────────────────────
onMounted(async () => {
  loading.value = true;
  try {
    const defs = await call("costeo_yelke.api.sales_order_api.get_sales_order_form_defaults");
    await loadItemIndex();

    defaults.customers       = defs.customers       || [];
    defaults.price_lists     = defs.price_lists     || [];
    defaults.currencies      = defs.currencies      || [];
    defaults.tax_templates   = defs.tax_templates   || [];
    defaults.terms_templates = defs.terms_templates || [];
    defaults.warehouses      = defs.warehouses      || [];
    defaults.uoms            = defs.uoms            || [];

    form.company            = defs.company           || "";
    form.currency           = defs.default_currency  || "MXN";
    form.selling_price_list = defs.default_price_list || "";
    form.transaction_date   = today();
    form.delivery_date      = addDays(7);

    if (!isNew.value) {
      const data = await call("costeo_yelke.api.sales_order_api.get_sales_order", { name: props.name });
      syncFromSO(data);
    }

    prepareEmailForm();
  } catch (e) {
    showToast(e.message || "Error al cargar", "error");
  } finally {
    loading.value = false;
  }
});

watch(showEmailModal, (v) => { if (v) prepareEmailForm(); });
watch(() => form.items, (items) => { items.forEach(r => recalcRow(r)); }, { deep: true });
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-gray-500 block mb-1; }
.field-input  { @apply w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white transition-colors disabled:bg-gray-50 disabled:text-gray-500; }
.btn-icon     { @apply w-8 h-8 border border-gray-200 rounded-md flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors; }
.fade-enter-active, .fade-leave-active   { transition: opacity 0.2s; }
.fade-enter-from,   .fade-leave-to       { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from,   .modal-leave-to     { opacity: 0; transform: scale(0.95); }
</style>
