// Términos y condiciones que se ofrecen en un documento (backend overrides/terminos.py):
// los generales del tipo (venta o compra) más los exclusivos de ese cliente o proveedor.
// Los exclusivos de otra parte no salen; el que ya tiene el documento siempre se muestra.
export function terminosPara(lista, tipo, parte, actual = "") {
  return (lista || []).filter((t) => {
    if (actual && t.name === actual) return true;
    if (tipo === "venta" && t.selling === 0) return false;
    if (tipo === "compra" && t.buying === 0) return false;
    const exclusivo = tipo === "venta" ? t.exclusivo_cliente : t.exclusivo_proveedor;
    return !exclusivo || exclusivo === parte;
  });
}
