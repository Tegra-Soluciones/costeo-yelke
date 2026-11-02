<!--
  Alta de una dirección del cliente, completa (todo lo que pide ERPNext). La liga con
  el cliente la pone el servidor (costeo_api.crear_direccion_cliente).
-->
<template>
  <Teleport to="body">
    <div v-if="abierto" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('cerrar')">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="px-6 pt-5 pb-4 border-b border-surface-border">
          <p class="text-[15px] font-semibold text-ink">Nueva dirección</p>
          <p class="p-meta mt-0.5">Se agrega a <b class="text-ink">{{ cliente || "el cliente" }}</b> y queda disponible para todos sus pedidos.</p>
        </div>

        <div class="px-6 py-5 space-y-5">
          <section>
            <p class="p-eyebrow mb-2.5">Identificación</p>
            <div class="grid grid-cols-6 gap-x-3 gap-y-3">
              <label class="col-span-6 sm:col-span-4"><span class="p-field-label">Nombre de la dirección</span>
                <input v-model="f.address_title" v-mayus class="p-field" placeholder="ej. PLANTA MONTERREY" />
                <span class="block text-[11px] text-ink-light mt-1">Si lo dejas vacío, se usa la ciudad.</span></label>
              <label class="col-span-6 sm:col-span-2"><span class="p-field-label">Tipo <span class="text-red-400">*</span></span>
                <select v-model="f.address_type" class="p-field">
                  <option v-for="t in TIPOS" :key="t.v" :value="t.v">{{ t.t }}</option>
                </select></label>
            </div>
          </section>

          <section>
            <p class="p-eyebrow mb-2.5">Domicilio</p>
            <div class="grid grid-cols-6 gap-x-3 gap-y-3">
              <label class="col-span-6 sm:col-span-4"><span class="p-field-label">Calle y número <span class="text-red-400">*</span></span>
                <input v-model="f.address_line1" v-mayus class="p-field" :class="err.address_line1 ? 'border-red-400' : ''" /></label>
              <label class="col-span-6 sm:col-span-2"><span class="p-field-label">Colonia y/o sección</span>
                <input v-model="f.address_line2" v-mayus class="p-field" /></label>
              <label class="col-span-6 sm:col-span-2"><span class="p-field-label">Ciudad o municipio <span class="text-red-400">*</span></span>
                <input v-model="f.city" v-mayus class="p-field" :class="err.city ? 'border-red-400' : ''" /></label>
              <!-- En México, una de las 32 entidades (reglas de captura: el servidor también
                   la exige); otro país, texto libre. -->
              <label class="col-span-3 sm:col-span-2"><span class="p-field-label">Estado <span v-if="esMexico" class="text-red-400">*</span></span>
                <select v-if="esMexico" v-model="f.state" class="p-field" :class="err.state ? 'border-red-400' : ''">
                  <option value="">— Elige —</option>
                  <option v-for="e in ESTADOS" :key="e" :value="e">{{ e }}</option>
                </select>
                <input v-else v-model="f.state" v-mayus class="p-field" /></label>
              <label class="col-span-3 sm:col-span-2"><span class="p-field-label">Código postal <span v-if="esMexico" class="text-red-400">*</span></span>
                <input v-model="f.pincode" class="p-field" :class="err.pincode ? 'border-red-400' : ''" inputmode="numeric"
                       :maxlength="esMexico ? 5 : 10" @input="esMexico && (f.pincode = f.pincode.replace(/\D/g, ''))" /></label>
              <label class="col-span-6 sm:col-span-3"><span class="p-field-label">País <span class="text-red-400">*</span></span>
                <LinkInput v-model="f.country" doctype="Country" placeholder="País…" :error="!!err.country" /></label>
            </div>
          </section>

          <section>
            <p class="p-eyebrow mb-2.5">Contacto en esta dirección</p>
            <div class="grid grid-cols-6 gap-x-3 gap-y-3">
              <label class="col-span-6 sm:col-span-2"><span class="p-field-label">Correo</span>
                <input v-model="f.email_id" type="email" class="p-field" /></label>
              <label class="col-span-3 sm:col-span-2"><span class="p-field-label">Teléfono</span>
                <input v-model="f.phone" type="tel" class="p-field" /></label>
              <label class="col-span-3 sm:col-span-2"><span class="p-field-label">Fax</span>
                <input v-model="f.fax" class="p-field" /></label>
            </div>
          </section>

          <section>
            <p class="p-eyebrow mb-2.5">Impuestos y preferencias</p>
            <div class="grid grid-cols-6 gap-x-3 gap-y-3 items-end">
              <label class="col-span-6 sm:col-span-3"><span class="p-field-label">Categoría de impuestos</span>
                <LinkInput v-model="f.tax_category" doctype="Tax Category" placeholder="(opcional)" /></label>
              <div class="col-span-6 sm:col-span-3 space-y-2 pb-1">
                <label class="flex items-center gap-2 text-[13px] text-ink"><input v-model="f.is_shipping_address" type="checkbox" :true-value="1" :false-value="0" class="accent-brand-500" />Dirección de envío preferida</label>
                <label class="flex items-center gap-2 text-[13px] text-ink"><input v-model="f.is_primary_address" type="checkbox" :true-value="1" :false-value="0" class="accent-brand-500" />Dirección de facturación preferida</label>
              </div>
            </div>
            <p class="text-[11.5px] text-ink-light mt-2">Si la marcas como preferida, la que lo era deja de serlo.</p>
          </section>
        </div>

        <div class="px-6 py-4 border-t border-surface-border flex items-center justify-end gap-2">
          <p v-if="error" class="text-[12px] text-red-600 mr-auto">{{ error }}</p>
          <button type="button" class="p-btn-secondary h-9 text-[13px]" @click="$emit('cerrar')">Cancelar</button>
          <button type="button" class="p-btn-primary h-9 text-[13px]" :disabled="guardando" @click="guardar">{{ guardando ? "Guardando…" : "Guardar dirección" }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { call } from "@/utils/frappe.js";
import LinkInput from "@/components/LinkInput.vue";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  cliente: { type: String, default: "" },
  guardando: { type: Boolean, default: false },
  error: { type: String, default: "" },
});
const emit = defineEmits(["cerrar", "guardar"]);

const TIPOS = [
  { v: "Shipping", t: "Envío" }, { v: "Billing", t: "Facturación" }, { v: "Office", t: "Oficina" },
  { v: "Plant", t: "Planta" }, { v: "Warehouse", t: "Almacén" }, { v: "Shop", t: "Tienda" },
  { v: "Subsidiary", t: "Sucursal" }, { v: "Postal", t: "Postal" }, { v: "Personal", t: "Personal" },
  { v: "Current", t: "Actual" }, { v: "Permanent", t: "Permanente" }, { v: "Other", t: "Otra" },
];
const VACIO = () => ({
  address_title: "", address_type: "Shipping", address_line1: "", address_line2: "", city: "", state: "",
  pincode: "", country: "Mexico", email_id: "", phone: "", fax: "", tax_category: "",
  is_shipping_address: 0, is_primary_address: 0,
});
const f = reactive(VACIO());
const SIN_ERRORES = () => ({ address_line1: false, city: false, country: false, state: false, pincode: false });
const err = reactive(SIN_ERRORES());
const esMexico = computed(() => !f.country || f.country === "Mexico");
// Las 32 entidades salen del servidor (overrides/captura.py), una sola lista para todos.
const ESTADOS = ref([]);
watch(() => props.abierto, async (v) => {
  if (!v) return;
  Object.assign(f, VACIO()); Object.assign(err, SIN_ERRORES());
  if (!ESTADOS.value.length) ESTADOS.value = await call("costeo_yelke.overrides.captura.catalogo_estados").catch(() => []);
});

function guardar() {
  err.address_line1 = !f.address_line1.trim();
  err.city = !f.city.trim();
  err.country = !f.country;
  err.state = esMexico.value && !f.state;
  err.pincode = esMexico.value && !/^\d{5}$/.test(f.pincode);
  if (Object.values(err).some(Boolean)) return;
  emit("guardar", { ...f });
}
</script>
