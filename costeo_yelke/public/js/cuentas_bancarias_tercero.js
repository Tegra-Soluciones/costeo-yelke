// Ficha de proveedor y cliente: TODAS sus cuentas bancarias con su moneda
// (api/moneda_terceros.py). Son informativas; en cada pago se usa la del tercero en la
// moneda del dinero. El guardia evita registrar los eventos dos veces.
if (!window.costeoYelkeCuentasTercero) {
	window.costeoYelkeCuentasTercero = true;
	const pintar = (frm) => {
		const campo = frm.fields_dict.cuentas_bancarias_html;
		if (!campo) return;
		if (frm.is_new()) {
			campo.$wrapper.html(`<p class="text-muted small">${__("Guarda primero para agregar sus cuentas bancarias.")}</p>`);
			return;
		}
		frappe.call({
			method: "costeo_yelke.api.moneda_terceros.get_cuentas_bancarias",
			args: { party_type: frm.doctype, party: frm.doc.name },
			callback: ({ message: cuentas = [] }) => {
				const e = frappe.utils.escape_html;
				const filas = cuentas.map((c) => `
					<tr${c.disabled ? ' class="text-muted"' : ""}>
						<td><a href="/app/bank-account/${encodeURIComponent(c.name)}">${e(c.account_name || c.name)}</a>${c.is_default ? ` <span class="indicator-pill green">${__("Predeterminada")}</span>` : ""}${c.disabled ? ` (${__("deshabilitada")})` : ""}</td>
						<td><b>${e(c.moneda || "")}</b></td>
						<td>${e(c.bank || "")}</td>
						<td>${e(c.bank_account_no || "")}</td>
						<td>${e(c.cuenta_clabe || c.numero_tarjeta || "")}</td>
					</tr>`).join("");
				campo.$wrapper.html(`
					<div class="frappe-control">
						${cuentas.length ? `<table class="table table-bordered table-sm" style="margin-bottom:8px">
							<thead><tr><th>${__("Cuenta")}</th><th>${__("Moneda")}</th><th>${__("Banco")}</th><th>${__("Número")}</th><th>${__("CLABE / tarjeta")}</th></tr></thead>
							<tbody>${filas}</tbody></table>`
							: `<p class="text-muted small">${__("Sin cuentas bancarias registradas.")}</p>`}
						<button class="btn btn-xs btn-default agregar-cuenta">${__("Agregar cuenta bancaria")}</button>
						<p class="text-muted small" style="margin-top:6px">${__("Una por moneda (pesos, dólares…). En cada pago se elige sola la de la moneda en que se paga.")}</p>
					</div>`);
				campo.$wrapper.find(".agregar-cuenta").on("click", () => {
					frappe.new_doc("Bank Account", { party_type: frm.doctype, party: frm.doc.name,
						moneda: frm.doc.default_currency || "MXN", account_name: `${frm.doc.name} ${frm.doc.default_currency || "MXN"}` });
				});
			},
		});
	};
	for (const dt of ["Supplier", "Customer"]) {
		frappe.ui.form.on(dt, { refresh: pintar });
	}
}
