// Doble captura de datos sensibles en el escritorio de ERPNext (pedido de Yelke):
// RFC de clientes y proveedores y cuentas de banco. El servidor exige que las dos
// capturas coincidan (costeo_yelke/api/confirmaciones.py); aquí solo se ayuda:
//   - el primer campo se oculta (como contraseña) en cuanto se empieza a escribir,
//     para que la confirmación se teclee y no se copie;
//   - la confirmación aparece solo al dar de alta o al cambiar el dato;
//   - debajo se ve en vivo si coinciden.
//
// Uso (en el JS del doctype): costeoYelkeDobleCaptura("Customer", [{ campo, confirmar, tipo }], opciones)
//   tipo:     "rfc" (sin espacios, mayúsculas) | "cuenta" (sin espacios ni guiones)
//   opciones: { obligatorio: bool, aplica: (frm) => bool }
window.costeoYelkeDobleCaptura = function (doctype, pares, opciones = {}) {
	const normalizar = (tipo, v) =>
		tipo === "rfc" ? String(v || "").replace(/\s/g, "").toUpperCase() : String(v || "").replace(/[\s-]/g, "");
	const aplica = (frm) => (opciones.aplica ? opciones.aplica(frm) : true);
	const editando = (frm, p) => frm.is_new() || (frm.__doble_captura_editado || {})[p.campo];

	function marcar(frm, p) {
		const campo = frm.fields_dict[p.confirmar];
		if (!campo || !campo.$wrapper) return;
		const a = normalizar(p.tipo, frm.doc[p.campo]);
		const b = normalizar(p.tipo, frm.doc[p.confirmar]);
		let aviso = "";
		if (a && b) {
			aviso = a === b
				? `<span style="color:#15803d;font-weight:600">${__("Coinciden")}</span>`
				: `<span style="color:#b91c1c;font-weight:600">${__("No coinciden")}</span>`;
		}
		campo.$wrapper.find(".doble-captura-aviso").remove();
		if (aviso) campo.$wrapper.find(".control-input-wrapper").append(`<div class="doble-captura-aviso small mt-1">${aviso}</div>`);
	}

	function preparar(frm) {
		for (const p of pares) {
			const activo = aplica(frm) && editando(frm, p) && (!p.soloConValor || frm.doc[p.campo] || frm.is_new());
			frm.toggle_display(p.confirmar, !!activo && (!p.soloConValor || !!frm.doc[p.campo]));
			frm.toggle_reqd(p.confirmar, !!activo && !!frm.doc[p.campo]);
			if (opciones.obligatorio) frm.toggle_reqd(p.campo, !!activo);
			const control = frm.fields_dict[p.campo];
			const $in = control && control.$input;
			if (!$in) continue;
			$in.attr("autocomplete", "off");
			// Oculto solo mientras se está capturando; ya guardado se ve normal.
			$in.attr("type", activo && frm.doc[p.campo] ? "password" : "text");
			$in.off(".dobleCaptura").on("input.dobleCaptura", () => {
				frm.__doble_captura_editado = { ...(frm.__doble_captura_editado || {}), [p.campo]: true };
				if (aplica(frm)) {
					$in.attr("type", "password");
					frm.toggle_display(p.confirmar, true);
				}
			});
			marcar(frm, p);
		}
	}

	const eventos = { refresh: preparar, onload_post_render: preparar, after_save: (frm) => { frm.__doble_captura_editado = {}; preparar(frm); } };
	for (const p of pares) {
		eventos[p.campo] = (frm) => { frm.__doble_captura_editado = { ...(frm.__doble_captura_editado || {}), [p.campo]: true }; preparar(frm); };
		eventos[p.confirmar] = (frm) => marcar(frm, p);
	}
	if (opciones.recalcularCon) for (const c of opciones.recalcularCon) eventos[c] = preparar;
	frappe.ui.form.on(doctype, eventos);
};
