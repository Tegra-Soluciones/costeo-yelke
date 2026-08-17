import { reactive, ref } from "vue";
import { call, defaultPrintFormat } from "@/utils/frappe.js";

// Acciones genéricas sobre documentos relacionados (Quotation, Sales Order,
// Purchase Order, etc.): vista previa/impresión, envío por correo o WhatsApp,
// y asignación a usuarios. Compartido por todas las secciones de CosteoDetailPage.
export function useDocumentActions(showToast) {
  const printFmtMap = reactive({});
  const previewKey = ref(0); // fuerza recarga de los iframes de preview

  const pdfModal = reactive({ open: false, doctype: "", name: "" });
  const sendChooser = reactive({ open: false, doctype: "", name: "", email: "", phone: "" });
  const waModal = reactive({ open: false, doctype: "", name: "", phone: "", message: "" });
  const sendModal = reactive({ open: false, doctype: "", name: "", recipients: "", subject: "", message: "", sending: false });
  const assignModal = reactive({ open: false, doctype: "", name: "", selected: [], sending: false });

  async function ensurePrintFmt(doctype) {
    if (doctype in printFmtMap) return printFmtMap[doctype];
    printFmtMap[doctype] = "Standard"; // placeholder para evitar fetch duplicado
    printFmtMap[doctype] = await defaultPrintFormat(doctype);
    previewKey.value++; // recarga los iframes con el formato correcto
    return printFmtMap[doctype];
  }

  function printUrl(doctype, name) {
    return `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(name)}&format=${encodeURIComponent(printFmtMap[doctype] || "Standard")}&no_letterhead=0&trigger_print=0&_v=${previewKey.value}`;
  }
  function printDocView(doctype, name) {
    window.open(printUrl(doctype, name).replace("trigger_print=0", "trigger_print=1"), "_blank");
  }
  // Descargar via impresión del navegador (Guardar como PDF): no depende de wkhtmltopdf.
  function downloadPdf(doctype, name) {
    window.open(printUrl(doctype, name).replace("trigger_print=0", "trigger_print=1"), "_blank");
  }

  async function openPdf(doctype, name) {
    pdfModal.doctype = doctype; pdfModal.name = name;
    await ensurePrintFmt(doctype);
    previewKey.value++; pdfModal.open = true;
  }

  function openSend(doctype, name, email, phone) {
    sendChooser.doctype = doctype; sendChooser.name = name;
    sendChooser.email = email || ""; sendChooser.phone = phone || "";
    sendChooser.open = true;
  }
  function chooseEmail() {
    sendChooser.open = false;
    sendModal.doctype = sendChooser.doctype; sendModal.name = sendChooser.name;
    sendModal.recipients = sendChooser.email;
    sendModal.subject = `${sendChooser.doctype === "Quotation" ? "Cotización" : sendChooser.doctype} ${sendChooser.name}`;
    sendModal.message = "Estimado cliente, adjunto encontrará el documento. Quedamos atentos.";
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
    const printFormat = printFmtMap[waModal.doctype] || "Standard";
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
      await call("costeo_yelke.api.costeo_api.enviar_por_correo", { doctype: sendModal.doctype, name: sendModal.name, recipients: sendModal.recipients, subject: sendModal.subject, message: sendModal.message });
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
    ensurePrintFmt, printUrl, printDocView, downloadPdf,
    openPdf, openSend, chooseEmail, chooseWhatsApp, sendWhatsAppGeneric, doSend,
    openAssign, doAssign,
  };
}
