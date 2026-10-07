// Cuenta bancaria del proveedor (v0_2_50): solo se ofrecen las cuentas registradas a nombre de ESTE proveedor.
frappe.ui.form.on("Supplier", {
	setup(frm) {
		frm.set_query("cuenta_bancaria_proveedor", () => ({
			filters: { party_type: "Supplier", party: frm.doc.name },
		}));
	},
});
