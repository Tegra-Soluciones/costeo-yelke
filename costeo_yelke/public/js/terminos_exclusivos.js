// Términos y condiciones exclusivos de un cliente o proveedor (overrides/terminos.py):
// en el Escritorio, la lista de «Términos» solo ofrece los generales y los de esa parte,
// y al cambiar de cliente/proveedor se ponen los suyos. Se carga en los cuatro
// formularios; el guardia evita registrar los eventos dos veces.
if (!window.costeoYelkeTerminos) {
	window.costeoYelkeTerminos = true;
	const DOCUMENTOS = {
		Quotation: ["party_name", "venta"],
		"Sales Order": ["customer", "venta"],
		"Sales Invoice": ["customer", "venta"],
		"Purchase Order": ["supplier", "compra"],
	};
	const parte = (frm, campo) =>
		frm.doctype === "Quotation" && frm.doc.quotation_to !== "Customer" ? "" : frm.doc[campo] || "";

	for (const [doctype, [campo, tipo]] of Object.entries(DOCUMENTOS)) {
		frappe.ui.form.on(doctype, {
			setup(frm) {
				frm.set_query("tc_name", () => ({
					query: "costeo_yelke.overrides.terminos.buscar_terminos",
					filters: { tipo, parte: parte(frm, campo) },
				}));
			},
			[campo](frm) {
				if (frm.doc.docstatus !== 0) return;
				frappe.call({
					method: "costeo_yelke.overrides.terminos.termino_por_defecto",
					args: { tipo, parte: parte(frm, campo), company: frm.doc.company },
					callback: (r) => {
						if (r.message && r.message !== frm.doc.tc_name) frm.set_value("tc_name", r.message);
					},
				});
			},
		});
	}
}
