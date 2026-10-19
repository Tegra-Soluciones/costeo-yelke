// Cuentas de clientes y proveedores: número de cuenta, CLABE y tarjeta se escriben dos
// veces (public/js/doble_captura.js, api/confirmaciones.py). Las de la propia empresa no.
costeoYelkeDobleCaptura("Bank Account", [
	{ campo: "bank_account_no", confirmar: "confirmar_cuenta", tipo: "cuenta", soloConValor: true },
	{ campo: "cuenta_clabe", confirmar: "confirmar_clabe", tipo: "cuenta", soloConValor: true },
	{ campo: "numero_tarjeta", confirmar: "confirmar_tarjeta", tipo: "cuenta", soloConValor: true },
], {
	aplica: (frm) => ["Customer", "Supplier"].includes(frm.doc.party_type),
	recalcularCon: ["party_type"],
});
