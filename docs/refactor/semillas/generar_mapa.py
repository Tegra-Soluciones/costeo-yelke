"""Genera docs/refactor/mapa-servidor.tsv y 03-MAPA-SERVIDOR.md desde costeo_api.py (HEAD 519ce25 + cambios de seguridad)."""
import ast, collections, re, subprocess
APP = "/Users/trabajo/Trabajo/frappe-bench-v15/apps/costeo_yelke"
src = open(f"{APP}/costeo_yelke/api/costeo_api.py").read()
t = ast.parse(src)
D = "costeo_yelke.dominio."
# (primera línea del rango, destino). Un símbolo cae en el último rango cuyo inicio <= su línea.
RANGOS = [
 (1, "comun.constantes"),
 (27, "costeo.ciclo"),
 (119, "ventas.lineas"),
 (542, "costeo.variantes"),
 (739, "ventas.cotizacion"),
 (788, "ingenieria.articulos"),
 (931, "ventas.cotizacion"),
 (979, "ingenieria.articulos"),
 (1250, "ingenieria.flujo"),
 (1726, "ventas.cotizacion"),
 (1738, "documentos.validacion"),
 (1969, "costeo.ciclo"),
 (2011, "documentos.validacion"),
 (2028, "ventas.orden_venta"),
 (2193, "talleres.avance"),
 (2376, "facturacion.venta"),
 (2441, "entregas.remision"),
 (2741, "facturacion.overhead"),
 (2754, "costos.costo_real"),
 (2993, "facturacion.overhead"),
 (3056, "entregas.remision"),
 (3093, "facturacion.compra"),
 (3471, "reportes.tablero"),
 (3607, "ingenieria.boms"),
 (3620, "costeo.ciclo"),
 (3627, "ventas.orden_venta"),
 (3646, "ventas.precio_acordado"),
 (3697, "ventas.orden_venta"),
 (3740, "costeo.ciclo"),
 (3774, "catalogo.precios"),
 (3811, "ingenieria.boms"),
 (4240, "planeacion.legado"),
 (4358, "ingenieria.boms"),
 (4501, "planeacion.plan"),
 (4678, "ventas.impuestos"),
 (4713, "costeo.relacionados"),
 (4888, "planeacion.plan"),
 (5173, "planeacion.solicitud"),
 (5295, "comun.unidades"),
 (5369, "planeacion.solicitud"),
 (5415, "compras.precios"),
 (5533, "compras.ordenes"),
 (5729, "planeacion.lotes_material"),
 (6073, "planeacion.posicion"),
 (6192, "compras.ordenes"),
 (6313, "compras.recibos"),
 (6520, "talleres.orden_manufactura"),
 (6765, "talleres.subcontratos"),
 (6821, "comun.alcance"),
 (6917, "talleres.lotes"),
 (7362, "documentos.contactos"),
 (7379, "comun.productos"),
 (7404, "talleres.saldos"),
 (7518, "talleres.subcontratos"),
 (7661, "talleres.encargos"),
 (8154, "talleres.recibos"),
 (8196, "comun.costos_adicionales"),
 (8239, "talleres.encargos"),
 (8286, "talleres.envios"),
 (8705, "talleres.sobrantes"),
 (8892, "talleres.envios"),
 (9072, "talleres.recibos"),
 (9100, "talleres.lotes"),
 (9378, "talleres.paradas"),
 (9487, "talleres.ramas"),
 (9660, "talleres.paradas"),
 (9880, "talleres.envios"),
 (9914, "talleres.recibos"),
 (10007, "compras.cotizaciones_proveedor"),
 (10082, "compras.flete"),
 (10176, "comun.moneda"),
 (10234, "compras.documento"),
 (10549, "planeacion.plan"),
 (10703, "reportes.reporte_final"),
 (11077, "documentos.contactos"),
 (11114, "documentos.envio"),
]
EXC = {  # excepciones por nombre
 "get_lotes_produccion": "vistas.lotes",
 "_party_links": "comun.contactos",
 "_vistas_de_documento": "comun.permisos",
 "_get_plan_for_so": "comun.alcance",
 "get_cotizacion_defaults": "ventas.cotizacion",
 "_contabilizar_overhead_factura": "facturacion.overhead",
 "get_default_print_format": "documentos.impresion",
 "_piece_states_de": "ingenieria.piezas",
 "_items_intermedios": "ingenieria.piezas",
 "_payable_account_para_proveedor": "entregas.flete_cliente",
 "_crear_poliza_flete_remision": "entregas.flete_cliente",
 "mr_crear_ocs_por_lotes": "compras.ordenes",
 "_transitive_upstream": "talleres.ramas",
 "_parada_subensamblajes": "talleres.paradas",
 "_productos_del_lote": "talleres.lotes",
 "plan_dividir_lotes": "planeacion.legado",
 "plan_crear_ordenes_trabajo": "planeacion.legado",
 "crear_boms": "planeacion.legado",
 "get_costeo_list": "costeo.ciclo",
}
LEGADO_MUERTO = {"crear_ordenes_trabajo", "plan_dividir_lotes", "crear_boms", "get_costeo_list", "set_costeo_status", "crear_pos_subcontratacion"}
starts = [r[0] for r in RANGOS]
def destino(name, line):
    if name in EXC: return EXC[name]
    i = max(i for i, s in enumerate(starts) if s <= line)
    return RANGOS[i][1]
rows = []
for n in t.body:
    if isinstance(n, ast.FunctionDef):
        wl = any("whitelist" in ast.unparse(d) for d in n.decorator_list)
        doc = (ast.get_docstring(n) or "").strip().split("\n")[0][:90].replace("|", "/").replace("\t", " ")
        rows.append((n.name, "funcion", "W" if wl else "", n.lineno, n.end_lineno - n.lineno + 1, destino(n.name, n.lineno), doc))
    elif isinstance(n, (ast.Assign, ast.AnnAssign)):
        tg = n.targets[0] if isinstance(n, ast.Assign) else n.target
        name = ast.unparse(tg)
        rows.append((name, "constante", "", n.lineno, n.end_lineno - n.lineno + 1, destino(name, n.lineno), ""))
# quién usa qué (llamadas internas por nombre)
nombres = {r[0] for r in rows}
usos = collections.defaultdict(set)
for n in t.body:
    if isinstance(n, ast.FunctionDef):
        dst = destino(n.name, n.lineno)
        for x in ast.walk(n):
            if isinstance(x, ast.Name) and x.id in nombres and x.id != n.name:
                usos[x.id].add(dst)
with open(f"{APP}/docs/refactor/mapa-servidor.tsv", "w") as f:
    f.write("simbolo\ttipo\twhitelist\tlinea_519ce25\tlineas\tdestino\tusado_desde\n")
    for r in rows:
        f.write(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t{r[4]}\t{D}{r[5]}\t{','.join(sorted(u for u in usos[r[0]] if u != r[5]))}\n")
# resumen por destino
por = collections.defaultdict(list)
for r in rows: por[r[5]].append(r)
area_tot = collections.Counter()
md = []
for dst in sorted(por):
    lst = por[dst]; tot = sum(r[4] for r in lst); area_tot[dst.split(".")[0]] += tot
    md.append(f"\n#### `dominio/{dst.replace('.', '/')}.py` — {len(lst)} símbolos, ~{tot} líneas\n")
    md.append("| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |\n|---|---|---|---|---|")
    for r in sorted(lst, key=lambda r: r[3]):
        ext = ", ".join(sorted(u for u in usos[r[0]] if u != dst))
        marca = " ⚠️ legado" if r[0] in LEGADO_MUERTO else ""
        md.append(f"| `{r[0]}`{marca} | {'sí' if r[2] else ''} | {r[4]} | {ext} | {r[6]} |")
open("/tmp/mapa_detalle.md", "w").write("\n".join(md))
print("símbolos", len(rows))
for a, v in sorted(area_tot.items(), key=lambda x: -x[1]): print(f"  {a:<12} {v}")
for dst in sorted(por): print(f"    {dst:<34} {sum(r[4] for r in por[dst]):>5}")
