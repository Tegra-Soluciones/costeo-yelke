<!--
  Los archivos de UNA factura (compra o venta): el PDF, obligatorio para validarla, y
  el XML del CFDI, opcional. Las facturas del sistema son para contabilidad -- la real
  es la del proveedor o la que se timbra en el otro sistema --, así que lo que se
  guarda aquí es ese archivo. El candado vive en el servidor
  (contabilidad.validar_archivos_factura); aquí solo se suben y se muestran.

  Cada archivo se sube adjunto a la factura y se guarda en su campo en el momento,
  igual que la OC del cliente en la orden de venta.
-->
<template>
  <div class="grid gap-x-4 gap-y-2" :class="apilado ? 'grid-cols-1' : 'sm:grid-cols-2'">
    <div>
      <p class="field-label">Factura (PDF) <span v-if="!soloLectura && !pdf" class="text-red-600 font-normal">· obligatoria para validar</span></p>
      <OcClienteAdjunto
        :model-value="pdf" :solo-lectura="soloLectura" :subiendo="subiendo === 'factura_pdf'"
        texto="Adjuntar el PDF" accept=".pdf,application/pdf"
        @archivo="subir($event, 'factura_pdf')" @quitar="guardar('factura_pdf', '')"
      />
    </div>
    <div>
      <p class="field-label">Factura (XML) <span class="text-ink-light font-normal">· opcional</span></p>
      <OcClienteAdjunto
        :model-value="xml" :solo-lectura="soloLectura" :subiendo="subiendo === 'factura_xml'"
        texto="Adjuntar el XML" accept=".xml,text/xml,application/xml"
        @archivo="subir($event, 'factura_xml')" @quitar="guardar('factura_xml', '')"
      />
    </div>
    <p v-if="aviso" class="text-[11.5px] text-red-600">{{ aviso }}</p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import OcClienteAdjunto from "./OcClienteAdjunto.vue";
import { call, uploadFile } from "@/utils/frappe.js";

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
  pdf: { type: String, default: "" },
  xml: { type: String, default: "" },
  soloLectura: { type: Boolean, default: false },
  apilado: { type: Boolean, default: false },   // columna angosta: uno debajo del otro
});
const emit = defineEmits(["update:pdf", "update:xml"]);
const subiendo = ref("");
const aviso = ref("");
const EXT = { factura_pdf: ".pdf", factura_xml: ".xml" };

async function guardar(campo, valor) {
  await call("frappe.client.set_value", { doctype: props.doctype, name: props.docname, fieldname: campo, value: valor });
  emit(campo === "factura_pdf" ? "update:pdf" : "update:xml", valor);
}

async function subir(ev, campo) {
  const file = ev?.target?.files?.[0];
  if (!file) return;
  aviso.value = "";
  if (!file.name.toLowerCase().endsWith(EXT[campo])) {
    aviso.value = `Ese archivo no es ${EXT[campo] === ".pdf" ? "un PDF" : "un XML"}.`;
    if (ev?.target) ev.target.value = "";
    return;
  }
  subiendo.value = campo;
  try {
    const res = await uploadFile(file, { doctype: props.doctype, docname: props.docname });
    await guardar(campo, res?.file_url || "");
  } catch (e) {
    aviso.value = e.message || "No se pudo subir el archivo";
  } finally {
    subiendo.value = "";
    if (ev?.target) ev.target.value = "";   // deja re-elegir el mismo archivo
  }
}
</script>
