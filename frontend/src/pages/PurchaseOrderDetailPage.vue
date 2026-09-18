<template>
  <div class="flex flex-col min-h-0">

    <PageHeader
      :title="isNew ? 'Nueva Orden de Compra' : (po.name || 'Cargando…')"
      :subtitle="isNew ? 'Nueva orden de compra' : (po.supplier_name || po.supplier || '')"
      back
    >
      <template v-if="!isNew">
        <button class="btn-icon" title="Imprimir" @click="openPrint">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
        </button>

        <template v-if="po.docstatus === 1">
          <!-- Crear Factura de Compra -->
          <button
            :disabled="!!(acting === 'makePinv')"
            class="px-3 py-1.5 bg-purple-600 text-white text-sm font-semibold rounded-md hover:bg-purple-700 flex items-center gap-1.5 transition-colors disabled:opacity-50"
            @click="makePurchaseInvoice"
          >
            <svg v-if="acting === 'makePinv'" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            {{ acting === 'makePinv' ? 'Creando…' : 'Crear Factura' }}
          </button>
          <div class="w-px h-5 bg-gray-200" />
        </template>

        <a :href="`/app/purchase-order/${encodeURIComponent(po.name)}`" target="_blank"
          class="px-3 py-1.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
          Desk
        </a>
      </template>
    </PageHeader>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <div v-else class="p-5 pb-40 flex gap-5 items-start">

      <div class="flex-1 min-w-0 space-y-4">

        <!-- Status bar -->
        <div v-if="!isNew" class="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-2.5">
          <StatusBadge :docstatus="po.docstatus" :status="po.status" />
          <span class="text-xs text-gray-300">·</span>
          <span class="text-xs font-mono text-gray-400">{{ po.name }}</span>
          <div class="flex-1" />
          <span v-if="form.schedule_date" class="text-xs" :class="isOverdue(form.schedule_date, po.docstatus) ? 'text-red-500 font-medium' : 'text-gray-400'">
            Entrega: {{ fmtDate(form.schedule_date) }}
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
          <button v-for="tab in TABS" :key="tab.key"
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
                <label class="field-label">Proveedor <span class="text-red-400">*</span></label>
                <select v-model="form.supplier" :disabled="!canEdit" class="field-input">
                  <option value="">— Seleccionar proveedor —</option>
                  <option v-for="s in defaults.suppliers" :key="s.name" :value="s.name">{{ s.supplier_name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Empresa <span class="text-red-400">*</span></label>
                <input v-model="form.company" type="text" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Fecha <span class="text-red-400">*</span></label>
                <input v-model="form.transaction_date" type="date" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Fecha de Entrega Esperada <span class="text-red-400">*</span></label>
                <input v-model="form.schedule_date" type="date" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Moneda</label>
                <select v-model="form.currency" :disabled="!canEdit" class="field-input">
                  <option v-for="c in defaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Lista de Precios</label>
                <select v-model="form.buying_price_list" :disabled="!canEdit" class="field-input">
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
                <input v-model="form.contact_email" type="email" :disabled="!canEdit" class="field-input" />
              </div>

            </div>
          </div>

          <!-- Items tab -->
          <div v-if="activeTab === 'items'" class="space-y-4">
            <div class="overflow-x-auto">
              <table class="w-full text-sm min-w-[720px]">
                <thead>
                  <tr class="border-b border-gray-100">
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-10">#</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3">Artículo</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-24">Cant.</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-24">UOM</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-32">Precio</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-32">Importe</th>
                    <th v-if="canEdit" class="w-8 pb-3"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="(row, idx) in form.items" :key="idx" class="group">
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
                          <input v-if="canEdit" v-model="row.item_code" type="text" list="item-datalist-po" class="field-input text-xs" placeholder="Código de artículo" @change="fillItemDefaults(row)" />
                          <span v-else class="font-medium text-gray-800 text-xs block">{{ row.item_code }}</span>
                          <p v-if="row.item_name && row.item_name !== row.item_code" class="text-xs text-gray-400 truncate">{{ row.item_name }}</p>
                        </div>
                      </div>
                    </td>
                    <td class="py-3 pr-3">
                      <input v-if="canEdit" v-model.number="row.qty" type="number" min="0.001" step="any" class="field-input text-xs w-20" @input="recalcRow(row)" />
                      <span v-else class="text-gray-800 text-xs">{{ row.qty }}</span>
                    </td>
                    <td class="py-3 pr-3">
                      <select v-if="canEdit" v-model="row.uom" class="field-input text-xs w-24">
                        <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                      </select>
                      <span v-else class="text-gray-600 text-xs">{{ row.uom }}</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <input v-if="canEdit" v-model.number="row.rate" type="number" min="0" step="any" class="field-input text-xs text-right w-28" @input="recalcRow(row)" />
                      <span v-else class="font-medium text-gray-800 text-xs">{{ fmtN(row.rate) }}</span>
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
                    <td :colspan="canEdit ? 7 : 6" class="py-10 text-center text-gray-400 text-sm">Sin artículos.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <datalist id="item-datalist-po">
              <option v-for="item in itemIndex" :key="item.name" :value="item.name">{{ item.item_name }}</option>
            </datalist>
            <button v-if="canEdit" class="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:border-brand-400 hover:text-brand-600 transition-colors w-full justify-center" @click="addItem">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
              Agregar artículo
            </button>
          </div>

          <!-- Términos tab -->
          <div v-if="activeTab === 'terminos'" class="space-y-4">
            <div>
              <label class="field-label">Plantilla de Términos</label>
              <select v-model="form.tc_name" :disabled="!canEdit" class="field-input">
                <option value="">— Sin plantilla —</option>
                <option v-for="t in defaults.terms_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="field-label">Términos y Condiciones</label>
              <textarea v-model="form.terms" :disabled="!canEdit" rows="8" class="field-input resize-y" />
            </div>
          </div>

        </div>

        <!-- Bottom action bar (draft) -->
        <div v-if="canEdit" class="flex items-center justify-between gap-3">
          <div>
            <button v-if="!isNew && po.docstatus === 0"
              :disabled="!!(acting || saving)"
              class="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 disabled:opacity-50"
              @click="cancelPO">
              Cancelar OC
            </button>
          </div>
          <div class="flex items-center gap-3">
            <span v-if="!isNew && po.revisado_yelke" class="text-xs font-medium text-brand-700 bg-brand-50 rounded-full px-2.5 py-1 flex items-center gap-1">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              Revisado{{ po.revisado_por_yelke ? ` · ${po.revisado_por_yelke}` : "" }}
            </span>
            <button v-if="!isNew"
              :disabled="!!(saving || acting)"
              class="px-5 py-2 border border-gray-200 text-gray-600 text-sm font-medium rounded-xl hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2"
              @click="save">
              <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {{ saving ? 'Guardando…' : 'Guardar borrador' }}
            </button>
            <button v-if="!isNew && !po.revisado_yelke"
              :disabled="!!(saving || acting) || !permisos.puede_revisar"
              class="px-5 py-2 border border-brand-200 text-brand-700 bg-brand-50 text-sm font-medium rounded-xl hover:bg-brand-100 disabled:opacity-50 flex items-center gap-2"
              :title="permisos.puede_revisar ? 'Marca la revisión intermedia -- requisito antes de Confirmar' : `Necesitas el rol 'Revisor de Documentos Yelke' para revisar`"
              @click="revisarPO">
              <svg v-if="acting === 'review'" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {{ acting === 'review' ? 'Revisando…' : 'Revisar' }}
            </button>
            <button
              :disabled="!!(saving || acting) || !po.revisado_yelke || !permisos.puede_aprobar"
              class="px-5 py-2 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 disabled:opacity-50 flex items-center gap-2"
              :title="!po.revisado_yelke ? 'Guarda y revisa esta orden antes de poder confirmarla' : (permisos.puede_aprobar ? '' : `Necesitas el rol 'Aprobador de Documentos Yelke' para confirmar`)"
              @click="doConfirm">
              <svg v-if="saving || acting === 'confirm'" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              {{ saving ? 'Guardando…' : acting === 'confirm' ? 'Confirmando…' : 'Confirmar OC' }}
            </button>
          </div>
        </div>

        <div v-if="!isNew && po.docstatus === 1" class="flex justify-end">
          <button :disabled="acting === 'cancel'" class="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 disabled:opacity-50" @click="cancelPO">
            Cancelar OC
          </button>
        </div>

      </div>

      <!-- Right sidebar -->
      <div class="w-60 flex-shrink-0 space-y-4 sticky top-5 self-start max-h-[calc(100vh-80px)] overflow-y-auto">
        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Totales</p>
          <div class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span class="font-medium text-gray-800">{{ fmtC(totals.subtotal) }}</span>
          </div>
          <div v-if="po.total_taxes_and_charges" class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Impuestos</span>
            <span class="font-medium text-gray-800">{{ fmtC(po.total_taxes_and_charges) }}</span>
          </div>
          <div class="flex justify-between items-center text-base font-bold border-t border-gray-100 pt-2.5 mt-1">
            <span class="text-gray-800">Total</span>
            <span class="text-brand-600">{{ fmtC(totals.grand) }} <span class="text-xs font-normal text-gray-400">{{ form.currency }}</span></span>
          </div>
        </div>

        <div v-if="form.supplier" class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Proveedor</p>
          <p class="text-sm font-semibold text-gray-800">{{ supplierDisplayName }}</p>
          <div v-if="form.contact_email" class="flex items-center gap-2">
            <svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
            <span class="text-xs text-gray-600 truncate">{{ form.contact_email }}</span>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5 text-sm">
          <div v-if="!isNew">
            <p class="text-xs text-gray-400">Estado</p>
            <StatusBadge :docstatus="po.docstatus" :status="po.status" class="mt-0.5" />
          </div>
          <div v-if="form.transaction_date">
            <p class="text-xs text-gray-400">Fecha</p>
            <p class="font-medium text-gray-700">{{ fmtDate(form.transaction_date) }}</p>
          </div>
          <div v-if="form.schedule_date">
            <p class="text-xs text-gray-400">Entrega Esperada</p>
            <p class="font-medium" :class="isOverdue(form.schedule_date, po.docstatus) ? 'text-red-500' : 'text-gray-700'">{{ fmtDate(form.schedule_date) }}</p>
          </div>
        </div>

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
        </div>

        <div v-if="!isNew" class="bg-white rounded-xl border border-gray-200 p-4 space-y-2 text-xs text-gray-400">
          <div v-if="po.creation"><p class="font-medium text-gray-500">Creada</p><p>{{ fmtDatetime(po.creation) }}</p></div>
          <div v-if="po.modified"><p class="font-medium text-gray-500">Modificada</p><p>{{ fmtDatetime(po.modified) }}</p></div>
        </div>
      </div>
    </div>

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
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import { call, defaultPrintFormat } from "@/utils/frappe.js";

const props  = defineProps({ name: { type: String, default: "" } });
const router = useRouter();

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = {
      "Draft": "Borrador", "To Receive and Bill": "Por Recibir/Facturar",
      "To Bill": "Por Facturar", "To Receive": "Por Recibir",
      "Completed": "Completada", "Cancelled": "Cancelada",
    };
    const STATUS_COLOR = {
      "To Receive and Bill": "bg-blue-100 text-blue-700",
      "To Bill": "bg-purple-100 text-purple-700",
      "To Receive": "bg-amber-100 text-amber-700",
      "Completed": "bg-green-100 text-green-700",
    };
    return () => {
      const ds    = p.docstatus ?? 0;
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

const loading   = ref(true);
const saving    = ref(false);
const acting    = ref("");
const activeTab = ref("general");
const toast     = reactive({ show: false, msg: "", type: "success" });
const isNew     = computed(() => !props.name || props.name === "nueva");

const po = reactive({
  name: "", docstatus: 0, status: "", creation: "", modified: "",
  total_taxes_and_charges: 0, supplier_name: "",
  // Doble validación (Enviar -> Revisor -> Aprobador, ver roles.py) -- requisito
  // para poder confirmar (submit_purchase_order).
  revisado_yelke: false, revisado_por_yelke: "", revisado_en_yelke: "",
});
const permisos = reactive({ puede_revisar: true, puede_aprobar: true });

const form = reactive({
  name: "", supplier: "", company: "",
  transaction_date: "", schedule_date: "",
  currency: "MXN", buying_price_list: "", conversion_rate: 1,
  taxes_and_charges: "", additional_discount_percentage: 0,
  tc_name: "", terms: "", supplier_address: "",
  contact_person: "", contact_email: "", contact_mobile: "",
  items: [],
});
const formOriginal = ref({});

const defaults = reactive({
  suppliers: [], price_lists: [], currencies: [], tax_templates: [],
  terms_templates: [], warehouses: [], uoms: [],
  default_currency: "MXN", default_price_list: "",
});

const itemIndex = ref([]);

const canEdit = computed(() => isNew.value || po.docstatus === 0);

const isDirty = computed(() => {
  const orig = formOriginal.value;
  if (!orig || !Object.keys(orig).length) return isNew.value;
  const keys = ["supplier","company","transaction_date","schedule_date","currency",
    "buying_price_list","taxes_and_charges","tc_name","terms","contact_email"];
  if (!keys.every(k => (form[k] ?? "") === (orig[k] ?? ""))) return true;
  if (form.items.length !== (orig.items || []).length) return true;
  return form.items.some(r => r._dirty);
});

const supplierDisplayName = computed(() =>
  defaults.suppliers.find(s => s.name === form.supplier)?.supplier_name || form.supplier
);

const totals = computed(() => {
  const subtotal = form.items.reduce((s, r) => s + (r.amount || 0), 0);
  const taxes    = isNew.value ? 0 : (po.total_taxes_and_charges || 0);
  return { subtotal, grand: subtotal + taxes };
});

function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function fmtN(v) { return new Intl.NumberFormat("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0); }
function fmtDate(s) { if (!s) return "—"; const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00"); return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" }); }
function fmtDatetime(s) { if (!s) return ""; return new Date(s).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
function isOverdue(dateStr, docstatus) { if (!dateStr || docstatus !== 1) return false; return new Date(dateStr + "T23:59:59") < new Date(); }
function today() { return new Date().toISOString().split("T")[0]; }
function addDays(n) { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split("T")[0]; }
function showToast(msg, type = "success") { toast.msg = msg; toast.type = type; toast.show = true; setTimeout(() => (toast.show = false), 3500); }

function addItem() {
  form.items.push({
    item_code: "", item_name: "", description: "", image: "",
    qty: 1, uom: "", stock_uom: "", conversion_factor: 1,
    rate: 0, price_list_rate: 0, discount_percentage: 0,
    amount: 0, schedule_date: form.schedule_date || addDays(7),
    warehouse: "", _dirty: true,
  });
  activeTab.value = "items";
}

function recalcRow(row) { row.amount = (row.rate || 0) * (row.qty || 1); }

async function fillItemDefaults(row) {
  if (!row.item_code) return;
  row._dirty = true;
  try {
    const res = await call("costeo_yelke.api.purchase_order_api.get_item_details_for_po", {
      item_code: row.item_code, price_list: form.buying_price_list || "",
    });
    if (res) {
      row.item_name       = res.item_name || row.item_code;
      row.description     = res.description || "";
      row.stock_uom       = res.stock_uom || "";
      row.uom             = res.uom || res.stock_uom || "";
      row.rate            = res.rate || 0;
      row.price_list_rate = res.price_list_rate || 0;
      row.image           = res.image || "";
      recalcRow(row);
    }
  } catch { /* ignore */ }
}

async function loadItemIndex() {
  try {
    const items = await call("frappe.client.get_list", {
      doctype: "Item", fields: ["name","item_name"],
      filters: [["disabled","=",0]], limit_page_length: 500, order_by: "item_name asc",
    });
    itemIndex.value = items || [];
  } catch { /* ignore */ }
}

function syncFromPO(data) {
  Object.assign(po, {
    name: data.name, docstatus: data.docstatus, status: data.status,
    creation: data.creation, modified: data.modified,
    total_taxes_and_charges: data.total_taxes_and_charges || 0,
    supplier_name: data.supplier_name || "",
    revisado_yelke: !!data.revisado_yelke,
    revisado_por_yelke: data.revisado_por_yelke || "",
    revisado_en_yelke: data.revisado_en_yelke || "",
  });
  const scalars = ["supplier","company","transaction_date","schedule_date","currency",
    "buying_price_list","conversion_rate","taxes_and_charges","additional_discount_percentage",
    "tc_name","terms","supplier_address","contact_person","contact_email","contact_mobile"];
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

async function save() {
  saving.value = true;
  let ok = false;
  try {
    const scheduleDate = form.schedule_date || addDays(7);
    const payload = {
      name: isNew.value ? "" : form.name,
      supplier: form.supplier, company: form.company,
      transaction_date: form.transaction_date, schedule_date: scheduleDate,
      currency: form.currency, buying_price_list: form.buying_price_list,
      conversion_rate: form.conversion_rate || 1,
      taxes_and_charges: form.taxes_and_charges,
      tc_name: form.tc_name, terms: form.terms,
      contact_email: form.contact_email, contact_mobile: form.contact_mobile,
      items: form.items.map(r => ({
        item_code: r.item_code, item_name: r.item_name, description: r.description,
        qty: r.qty, uom: r.uom, conversion_factor: r.conversion_factor || 1,
        rate: r.rate, discount_percentage: r.discount_percentage || 0,
        warehouse: r.warehouse, schedule_date: r.schedule_date || scheduleDate,
      })),
    };
    const saved = await call("costeo_yelke.api.purchase_order_api.save_purchase_order", {
      data: JSON.stringify(payload),
    });
    syncFromPO(saved);
    showToast(isNew.value ? "Orden creada" : "Orden guardada");
    if (isNew.value) router.replace(`/ordenes-compra/${encodeURIComponent(saved.name)}`);
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
  if (po.docstatus !== 0) return;
  acting.value = "confirm";
  try {
    const res = await call("costeo_yelke.api.purchase_order_api.submit_purchase_order", { name: po.name });
    Object.assign(po, { docstatus: res.docstatus, status: res.status });
    showToast("Orden de compra confirmada");
  } catch (e) {
    showToast(e.message || "Error al confirmar", "error");
  } finally {
    acting.value = "";
  }
}

// Doble validación (Enviar -> Revisor -> Aprobador) -- paso previo obligatorio a
// "Confirmar OC" (ver submit_purchase_order).
async function revisarPO() {
  acting.value = "review";
  try {
    const res = await call("costeo_yelke.api.purchase_order_api.marcar_revisada_purchase_order", { name: po.name });
    po.revisado_yelke = true;
    po.revisado_por_yelke = res.revisado_por_yelke;
    showToast("Orden de compra revisada");
  } catch (e) {
    showToast(e.message || "No se pudo revisar", "error");
  } finally {
    acting.value = "";
  }
}
async function loadPermisos() {
  try { Object.assign(permisos, await call("costeo_yelke.api.purchase_order_api.get_permisos_validacion_yelke")); }
  catch { /* si falla, se dejan en true -- el backend igual bloquea si no toca */ }
}

async function cancelPO() {
  if (!confirm("¿Cancelar esta orden de compra?")) return;
  acting.value = "cancel";
  try {
    const res = await call("costeo_yelke.api.purchase_order_api.cancel_purchase_order", { name: po.name });
    Object.assign(po, { docstatus: res.docstatus, status: res.status });
    showToast("Orden cancelada");
  } catch (e) {
    showToast(e.message || "Error al cancelar", "error");
  } finally {
    acting.value = "";
  }
}

async function makePurchaseInvoice() {
  acting.value = "makePinv";
  try {
    const res = await call("costeo_yelke.api.purchase_order_api.make_purchase_invoice_from_po", { po_name: po.name });
    showToast("Factura de compra creada — abriendo en Desk…");
    setTimeout(() => window.open(`/app/purchase-invoice/${encodeURIComponent(res.name)}`, "_blank"), 800);
  } catch (e) {
    showToast(e.message || "Error al crear factura", "error");
  } finally {
    acting.value = "";
  }
}

async function openPrint() {
  const fmt = await defaultPrintFormat("Purchase Order");
  window.open(`/printview?doctype=Purchase+Order&name=${encodeURIComponent(po.name)}&format=${encodeURIComponent(fmt)}&no_letterhead=0`, "_blank");
}

onMounted(async () => {
  loading.value = true;
  loadPermisos();
  try {
    const defs = await call("costeo_yelke.api.purchase_order_api.get_purchase_order_form_defaults");
    await loadItemIndex();
    defaults.suppliers      = defs.suppliers      || [];
    defaults.price_lists    = defs.price_lists    || [];
    defaults.currencies     = defs.currencies     || [];
    defaults.tax_templates  = defs.tax_templates  || [];
    defaults.terms_templates = defs.terms_templates || [];
    defaults.warehouses     = defs.warehouses     || [];
    defaults.uoms           = defs.uoms           || [];
    form.company            = defs.company          || "";
    form.currency           = defs.default_currency || "MXN";
    form.buying_price_list  = defs.default_price_list || "";
    form.transaction_date   = today();
    form.schedule_date      = addDays(7);
    if (!isNew.value) {
      const data = await call("costeo_yelke.api.purchase_order_api.get_purchase_order", { name: props.name });
      syncFromPO(data);
    }
  } catch (e) {
    showToast(e.message || "Error al cargar", "error");
  } finally {
    loading.value = false;
  }
});

watch(() => form.items, (items) => { items.forEach(r => recalcRow(r)); }, { deep: true });
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-gray-500 block mb-1; }
.field-input  { @apply w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white transition-colors disabled:bg-gray-50 disabled:text-gray-500; }
.btn-icon     { @apply w-8 h-8 border border-gray-200 rounded-md flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
