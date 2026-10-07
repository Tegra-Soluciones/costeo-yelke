import { reactive, ref } from "vue";
import { call, defaultPrintFormat } from "@/utils/frappe.js";

// Acciones genéricas sobre documentos relacionados (Quotation, Sales Order,
// Purchase Order, etc.): vista previa/impresión, envío por correo o WhatsApp,
// y asignación a usuarios. Compartido por todas las secciones de CosteoDetailPage.
export function useDocumentActions(showToast) {
  const printFmtMap = reactive({});
  const previewKey = ref(0); // fuerza recarga de los iframes de preview

  const pdfModal = reactive({ open: false, doctype: "", name: "" });
  const sendChooser = reactive({ open: false, doctype: "", name: "", email: "", phone: "", printFormats: [], asunto: "", mensaje: "" });
  const waModal = reactive({ open: false, doctype: "", name: "", phone: "", message: "" });
  const sendModal = reactive({ open: false, doctype: "", name: "", recipients: "", subject: "", message: "", sending: false, printFormats: [] });
  const assignModal = reactive({ open: false, doctype: "", name: "", selected: [], sending: false });

  // El formato se resuelve por DOCUMENTO: en Orden de Compra depende del propio
  // documento (subcontratación -> "Orden de Maquila", normal -> "Orden de Compra
  // Yelke"), no solo del doctype.
  const fmtKey = (doctype, name) => (name ? `${doctype}|${name}` : doctype);

  async function ensurePrintFmt(doctype, name) {
    const k = fmtKey(doctype, name);
    if (k in printFmtMap) return printFmtMap[k];
    printFmtMap[k] = "Standard"; // placeholder para evitar fetch duplicado
    printFmtMap[k] = await defaultPrintFormat(doctype, name);
    previewKey.value++; // recarga los iframes con el formato correcto
    return printFmtMap[k];
  }

  // printUrl se llama desde los templates (src de los iframes), que es síncrono:
  // si el formato aún no está resuelto dispara la consulta en segundo plano y
  // devuelve "Standard" por esta vez; al llegar la respuesta sube previewKey y
  // el iframe se recarga ya con el formato correcto.
  function printUrl(doctype, name) {
    const k = fmtKey(doctype, name);
    // Varias pantallas precalientan el formato por doctype (ensurePrintFmt("Sales
    // Order")); ese valor sirve para todo salvo Orden de Compra, donde el formato
    // es por documento y hay que resolverlo sí o sí.
    const porDoctype = doctype === "Purchase Order" ? null : printFmtMap[doctype];
    if (!(k in printFmtMap) && !porDoctype) ensurePrintFmt(doctype, name);
    const fmt = printFmtMap[k] || porDoctype || "Standard";
    return `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(name)}&format=${encodeURIComponent(fmt)}&no_letterhead=0&trigger_print=0&_v=${previewKey.value}`;
  }
  function printDocView(doctype, name) {
    window.open(printUrl(doctype, name).replace("trigger_print=0", "trigger_print=1"), "_blank");
  }
  // Descargar via impresión del navegador (Guardar como PDF): no depende de wkhtmltopdf.
  function downloadPdf(doctype, name) {
    window.open(printUrl(doctype, name).replace("trigger_print=0", "trigger_print=1"), "_blank");
  }
  /** Mismo documento, FORMATO explícito -- la orden a un taller se imprime en dos
   *  PDF distintos (la orden de compra y su ficha de manufactura) y cada botón
   *  tiene que pedir el suyo, no el formato por omisión del documento. */
  function printUrlFmt(doctype, name, fmt) {
    return `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(name)}`
      + `&format=${encodeURIComponent(fmt)}&no_letterhead=0&trigger_print=0&_v=${previewKey.value}`;
  }
  function downloadPdfFmt(doctype, name, fmt) {
    window.open(printUrlFmt(doctype, name, fmt).replace("trigger_print=0", "trigger_print=1"), "_blank");
  }

  async function openPdf(doctype, name) {
    pdfModal.doctype = doctype; pdfModal.name = name;
    await ensurePrintFmt(doctype, name);
    previewKey.value++; pdfModal.open = true;
  }

  /** `opciones.printFormats`: los PDF que se adjuntan (varios del mismo documento).
   *  `opciones.asunto` / `opciones.mensaje`: textos propios de ese envío. */
  function openSend(doctype, name, email, phone, opciones = {}) {
    sendChooser.doctype = doctype; sendChooser.name = name;
    sendChooser.email = email || ""; sendChooser.phone = phone || "";
    sendChooser.printFormats = opciones.printFormats || [];
    sendChooser.asunto = opciones.asunto || "";
    sendChooser.mensaje = opciones.mensaje || "";
    sendChooser.open = true;
  }
  function chooseEmail() {
    sendChooser.open = false;
    sendModal.doctype = sendChooser.doctype; sendModal.name = sendChooser.name;
    sendModal.recipients = sendChooser.email;
    sendModal.subject = sendChooser.asunto
      || `${sendChooser.doctype === "Quotation" ? "Cotización" : sendChooser.doctype} ${sendChooser.name}`;
    sendModal.message = sendChooser.mensaje
      || "Estimado cliente, adjunto encontrará el documento. Quedamos atentos.";
    sendModal.printFormats = sendChooser.printFormats || [];
    sendModal.open = true;
  }
  function chooseWhatsApp() {
    sendChooser.open = false;
    waModal.doctype = sendChooser.doctype; waModal.name = sendChooser.name;
    waModal.phone = sendChooser.phone;
    waModal.message = `Hola, le comparto el documento *${sendChooser.name}*. Adjunto el PDF con el detalle. Quedamos atentos.`;
    waModal.open = true;
  }
  function sendWhatsAppGeneric() {
    const phone = (waModal.phone || "").replace(/[^0-9]/g, "");
    if (!phone) { showToast("Ingresa un número de WhatsApp", "error"); return; }
    const printFormat = printFmtMap[fmtKey(waModal.doctype, waModal.name)] || "Standard";
    const pdfUrl = `/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent(waModal.doctype)}&name=${encodeURIComponent(waModal.name)}&format=${encodeURIComponent(printFormat)}&no_letterhead=0`;
    const a = document.createElement("a");
    a.href = pdfUrl; a.download = `${waModal.name}.pdf`; a.click();
    setTimeout(() => {
      window.open(`https://wa.me/${phone}?text=${encodeURIComponent(waModal.message)}`, "_blank");
    }, 500);
    waModal.open = false;
    showToast("PDF descargado — adjúntalo en WhatsApp");
  }
  async function doSend() {
    sendModal.sending = true;
    try {
      await call("costeo_yelke.api.costeo_api.enviar_por_correo", {
        doctype: sendModal.doctype, name: sendModal.name, recipients: sendModal.recipients,
        subject: sendModal.subject, message: sendModal.message,
        print_formats: (sendModal.printFormats || []).length ? JSON.stringify(sendModal.printFormats) : null,
      });
      sendModal.open = false;
      showToast("Correo enviado");
    } catch (e) { showToast(e.message || "No se pudo enviar", "error"); }
    finally { sendModal.sending = false; }
  }

  function openAssign(doctype, name) {
    assignModal.doctype = doctype; assignModal.name = name; assignModal.selected = []; assignModal.open = true;
  }
  async function doAssign() {
    if (!assignModal.selected.length) return;
    assignModal.sending = true;
    try {
      await call("costeo_yelke.api.costeo_api.asignar_documento", { doctype: assignModal.doctype, name: assignModal.name, assign_to: assignModal.selected.join(",") });
      assignModal.open = false;
      showToast("Asignado");
    } catch (e) { showToast(e.message || "No se pudo asignar", "error"); }
    finally { assignModal.sending = false; }
  }

  return {
    printFmtMap, previewKey,
    pdfModal, sendChooser, waModal, sendModal, assignModal,
    ensurePrintFmt, printUrl, printDocView, downloadPdf, printUrlFmt, downloadPdfFmt,
    openPdf, openSend, chooseEmail, chooseWhatsApp, sendWhatsAppGeneric, doSend,
    openAssign, doAssign,
  };
}
