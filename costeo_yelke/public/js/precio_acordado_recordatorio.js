// =============================================================================
// RECORDATORIO DE VIGENCIA DE PRECIO ACORDADO
// =============================================================================
// Botones para enviar el recordatorio al cliente (correo automático, o WhatsApp vía
// el flujo manual ya usado en el resto de la app: abrir wa.me con el mensaje
// precargado) y para descartarlo cuando ya no aplica.

frappe.ui.form.on("Precio Acordado Recordatorio", {
	refresh(frm) {
		if (frm.doc.estado === "Descartado") return;

		frm.add_custom_button("Enviar por correo", () => {
			frappe.call({
				method: "costeo_yelke.api.item_api.enviar_recordatorio_precio_email",
				args: { recordatorio: frm.doc.name },
				freeze: true,
				freeze_message: "Enviando…",
				callback: () => {
					frappe.show_alert({ message: "Correo enviado", indicator: "green" });
					frm.reload_doc();
				},
			});
		});

		frm.add_custom_button("Enviar por WhatsApp", () => {
			frappe.call({
				method: "costeo_yelke.api.item_api.get_recordatorio_whatsapp_link",
				args: { recordatorio: frm.doc.name },
				callback: (r) => {
					if (!r.message || !r.message.url) return;
					window.open(r.message.url, "_blank");
					frappe.call({
						method: "costeo_yelke.api.item_api.marcar_recordatorio_enviado",
						args: { recordatorio: frm.doc.name, canal: "whatsapp" },
						callback: () => frm.reload_doc(),
					});
				},
			});
		});

		frm.add_custom_button("Descartar", () => {
			frappe.confirm("¿Descartar este recordatorio?", () => {
				frappe.call({
					method: "costeo_yelke.api.item_api.descartar_recordatorio",
					args: { recordatorio: frm.doc.name },
					callback: () => frm.reload_doc(),
				});
			});
		});
	},
});
