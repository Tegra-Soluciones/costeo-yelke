"""Arma el PDF A4 del manual decidiendo HOJA POR HOJA qué cabe en cada una.

Por qué no se deja al navegador
-------------------------------
Generar el PDF con las reglas de impresión de CSS (`break-inside: avoid` y
compañía) deja la decisión en manos del motor del navegador, que las respeta
"en lo posible": si un bloque no le cabe, lo parte igual. El resultado es
impredecible — una imagen cortada, una tabla de la que pasa un solo renglón.

Aquí se hace al revés. Se mide cada bloque del manual con su estilo real y se
van llenando hojas de alto fijo: si el siguiente bloque no cabe en lo que queda,
la hoja se cierra y el bloque arranca la siguiente, entero. Cada hoja del
documento final es un `<div>` de 297 mm exactos, así que el PDF no tiene nada
que decidir — solo imprime una hoja por página.

Lo que garantiza
----------------
  · nada se parte entre hojas: ni figuras, ni avisos, ni renglones de tabla;
  · un encabezado nunca se queda solo: viaja con el bloque que le sigue;
  · una imagen más alta que la hoja se reduce para caber, nunca se recorta;
  · las tablas y listas que de verdad son más altas que una hoja se reparten
    entre renglones completos, repitiendo su encabezado;
  · márgenes parejos y pie de página con folio en todas las hojas.

Uso:  python3 respaldos/gen_pdf_a4.py
"""
import io
import os
import re
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, "..", "costeo_yelke", "www", "manual-costeo.html")
TMP = "/tmp/manual_a4.html"
SALIDA = os.path.join(AQUI, "Manual-Costeo-Yelke-A4.pdf")

# Hoja A4 y márgenes, en milímetros.
HOJA_W, HOJA_H = 210, 297
MG_SUP, MG_INF, MG_IZQ, MG_DER = 22, 24, 20, 20
ALTO_PIE = 10                      # franja reservada al pie de página
ANCHO_CONT = HOJA_W - MG_IZQ - MG_DER          # 170 mm
ALTO_CONT = HOJA_H - MG_SUP - MG_INF - ALTO_PIE  # 241 mm

ESTILO_DOC = """
<style id="estilo-hojas">
  @page { size: A4; margin: 0; }
  html, body { margin: 0; padding: 0; background: #fff; }
  .hoja {
    width: %(w)smm; height: %(h)smm;
    padding: %(sup)smm %(der)smm %(inf)smm %(izq)smm;
    box-sizing: border-box; position: relative; overflow: hidden;
    background: #fff; break-after: page; page-break-after: always;
  }
  .hoja:last-child { break-after: auto; page-break-after: auto; }
  .contenido { width: %(cw)smm; }
  /* El primer bloque de una hoja no arrastra su margen superior: si lo hiciera,
     el texto arrancaría más abajo en unas hojas que en otras. */
  .contenido > *:first-child { margin-top: 0 !important; }
  .pie {
    position: absolute; left: %(izq)smm; right: %(der)smm; bottom: %(pie)smm;
    display: flex; justify-content: space-between; align-items: baseline;
    font-size: 8.5pt; color: #9b9ba3;
    border-top: 0.3mm solid #e4e4e7; padding-top: 2.5mm;
  }
  .pie .folio { font-variant-numeric: tabular-nums; }
  /* Portada */
  .hoja.portada { padding-top: 58mm; }
  .hoja.portada .marca { font-size: 11px; font-weight: 700; letter-spacing: .18em;
    text-transform: uppercase; color: #e8590c; margin-bottom: 26px; }
  .hoja.portada h1 { font-size: 40px; line-height: 1.12; font-weight: 800;
    margin: 0 0 22px; letter-spacing: -0.015em; }
  .hoja.portada .dek { font-size: 15.5px; line-height: 1.65; color: #52525b;
    margin: 0 0 40px; max-width: 135mm; }
  .hoja.portada .ficha { border-top: 0.4mm solid #e4e4e7; padding-top: 20px;
    font-size: 12.5px; color: #52525b; line-height: 1.95; }
  .hoja.portada .ficha b { color: #18181b; }
  .hoja.portada .aviso { margin-top: 22px; font-size: 11.5px; line-height: 1.6;
    color: #92400e; background: #fffaeb; border-left: 0.8mm solid #fde68a;
    padding: 10px 14px; max-width: 150mm; }
  .hoja.portada .sello { position: absolute; left: %(izq)smm; bottom: 30mm;
    font-size: 11px; color: #9b9ba3; }
  /* Índice */
  .idx h2 { font-size: 26px; margin: 0 0 26px; }
  .idx ol { list-style: none; margin: 0; padding: 0; counter-reset: sec -1; }
  .idx li { counter-increment: sec; display: flex; align-items: baseline; gap: 14px;
    padding: 11px 0; border-bottom: 0.3mm solid #ececef; font-size: 14px; }
  .idx li::before { content: counter(sec); font-size: 12px; color: #9b9ba3;
    width: 16px; flex-shrink: 0; font-variant-numeric: tabular-nums; }
  .idx .pt { flex: 1; border-bottom: 0.3mm dotted #d4d4d8; margin: 0 4px; transform: translateY(-3px); }
  .idx .pg { font-size: 12.5px; color: #52525b; font-variant-numeric: tabular-nums; }
  /* En papel los enlaces no se tocan. */
  a { color: inherit !important; text-decoration: none !important; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  /* Una figura nunca más alta que la mancha de texto. */
  figure img, figure svg { max-height: %(imgmax)smm; width: auto; max-width: 100%%;
    display: block; margin: 0 auto; }
</style>
""" % {"w": HOJA_W, "h": HOJA_H, "sup": MG_SUP, "inf": MG_INF, "izq": MG_IZQ,
       "der": MG_DER, "cw": ANCHO_CONT, "pie": MG_INF - 12, "imgmax": ALTO_CONT - 16}


# ── Paginador: corre dentro del navegador, donde se puede medir ─────────────
JS_PAGINAR = r"""
async (datos) => {
  const { bloques, anchoMM, altoMM } = datos;
  const MM = 96 / 25.4;
  const ALTO = Math.floor(altoMM * MM);

  // Caja oculta con el MISMO ancho y estilos que tendrá la hoja real.
  const caja = document.createElement('div');
  caja.style.cssText = 'position:absolute;left:-10000px;top:0;width:' + anchoMM + 'mm;';
  document.body.appendChild(caja);
  let cur = document.createElement('div');
  cur.className = 'contenido';
  cur.style.width = anchoMM + 'mm';
  caja.appendChild(cur);

  const hojas = [];
  const cabe = () => cur.scrollHeight <= ALTO;
  const cerrar = () => {
    if (cur.children.length) hojas.push(cur.innerHTML);
    cur = document.createElement('div');
    cur.className = 'contenido';
    cur.style.width = anchoMM + 'mm';
    caja.replaceChildren(cur);
  };
  // Una imagen recién insertada mide 0 hasta que el navegador la decodifica. Si se
  // mide antes, una figura entera cuenta como un par de píxeles y en la hoja caben
  // cosas que en realidad no caben: es lo que partía el documento.
  const listaImagenes = async (el) => {
    const imgs = [...el.querySelectorAll('img')];
    await Promise.all(imgs.map(i => {
      if (i.complete && i.naturalWidth) return Promise.resolve();
      if (i.decode) return i.decode().catch(() => {});
      return new Promise(r => { i.onload = i.onerror = r; });
    }));
  };

  const nodo = (html) => {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  };
  const altoSolo = (el) => {
    const prueba = document.createElement('div');
    prueba.className = 'contenido';
    prueba.style.cssText = 'position:absolute;left:-10000px;width:' + anchoMM + 'mm;';
    document.body.appendChild(prueba);
    prueba.appendChild(el.cloneNode(true));
    const h = prueba.scrollHeight;
    prueba.remove();
    return h;   // se llama solo sobre tablas y listas, que no llevan imágenes
  };

  // Un párrafo corrido sí se puede partir, pero SOLO entre líneas y dejando al
  // menos dos de cada lado. Se usa un Range del navegador en vez de cortar el
  // texto a mano para no romper las negritas ni el código de en medio.
  const DOS_LINEAS = 54;
  function partirParrafo(el, limite) {
    const textos = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) textos.push(n);
    const cortes = [];
    for (const t of textos) {
      const v = t.nodeValue;
      for (let i = 0; i < v.length; i++) if (v[i] === ' ') cortes.push([t, i + 1]);
    }
    if (cortes.length < 12 || !el.firstChild) return null;
    const trozo = (desde, hasta) => {
      const r = document.createRange();
      if (desde) r.setStart(desde[0], desde[1]); else r.setStartBefore(el.firstChild);
      if (hasta) r.setEnd(hasta[0], hasta[1]); else r.setEndAfter(el.lastChild);
      const d = el.cloneNode(false);
      d.appendChild(r.cloneContents());
      return d;
    };
    let lo = 0, hi = cortes.length - 1, mejor = -1;
    while (lo <= hi) {                       // último corte cuya cabeza aún cabe
      const m = (lo + hi) >> 1;
      if (altoSolo(trozo(null, cortes[m])) <= limite) { mejor = m; lo = m + 1; }
      else { hi = m - 1; }
    }
    if (mejor < 0) return null;
    const cabeza = trozo(null, cortes[mejor]);
    const cola = trozo(cortes[mejor], null);
    if (altoSolo(cabeza) < DOS_LINEAS || altoSolo(cola) < DOS_LINEAS) return null;
    const resto = altoSolo(cola) > ALTO ? (partirParrafo(cola, ALTO) || [cola]) : [cola];
    return [cabeza].concat(resto);
  }

  // Parte un bloque que no cabe. `primero` es el alto disponible para el primer
  // trozo: cuando el bloque empieza a media hoja es el hueco que queda, y así una
  // tabla arranca debajo de su encabezado en vez de dejar la hoja a medias.
  function partir(el, primero) {
    const tope = (trozos) => trozos.length ? ALTO : (primero || ALTO);
    const tag = el.tagName.toLowerCase();
    // Tabla: se reparte entre renglones, repitiendo el encabezado.
    if (tag === 'table') {
      const filas = [...el.querySelectorAll('tr')];
      const esCab = filas.length && filas[0].querySelector('th');
      const cab = esCab ? filas.shift() : null;
      const trozos = []; let act = null;
      for (const f of filas) {
        if (!act) {
          act = el.cloneNode(false);
          const tb = document.createElement('tbody');
          act.appendChild(tb);
          if (cab) tb.appendChild(cab.cloneNode(true));
        }
        const tb0 = act.querySelector('tbody');
        tb0.appendChild(f.cloneNode(true));
        // Un renglón que por sí solo no cabe se queda entero: partirlo lo cortaría.
        const propios = tb0.children.length - (cab ? 1 : 0);
        if (altoSolo(act) > tope(trozos) && propios > 1) {
          tb0.lastElementChild.remove();
          trozos.push(act);
          act = null;
          const nuevo = el.cloneNode(false);
          const tb = document.createElement('tbody');
          nuevo.appendChild(tb);
          if (cab) tb.appendChild(cab.cloneNode(true));
          tb.appendChild(f.cloneNode(true));
          act = nuevo;
        }
      }
      if (act && act.querySelector('tbody').children.length > (cab ? 1 : 0)) trozos.push(act);
      return trozos.length > 1 ? trozos : [el];
    }
    // Listas y rejillas: se reparten entre elementos completos.
    if (['ol', 'ul', 'div'].includes(tag) && el.children.length > 1) {
      const hijos = [...el.children];
      const trozos = []; let act = el.cloneNode(false);
      for (const h of hijos) {
        act.appendChild(h.cloneNode(true));
        if (altoSolo(act) > tope(trozos) && act.children.length > 1) {
          act.lastElementChild.remove();
          trozos.push(act);
          act = el.cloneNode(false);
          act.appendChild(h.cloneNode(true));
        }
      }
      if (act.children.length) trozos.push(act);
      return trozos.length > 1 ? trozos : [el];
    }
    // Párrafo de texto corrido (los avisos y notas con recuadro no se tocan).
    if (tag === 'p' && !el.className) {
      const trozos = partirParrafo(el, primero || ALTO);
      if (trozos) return trozos;
    }
    return [el];
  }

  const esTitulo = (el) => /^h[2-4]$/i.test(el.tagName) ||
                           el.classList.contains('sec-title') ||
                           el.classList.contains('sec-dek');

  for (let i = 0; i < bloques.length; i++) {
    const b = bloques[i];
    if (b.saltar) { cerrar(); }         // empieza sección: hoja nueva
    let el = nodo(b.html);
    if (!el) continue;

    cur.appendChild(el);
    await listaImagenes(el);
    if (cabe()) {
      // Un encabezado no se queda solo al pie: debe caber él y lo que sigue.
      if (esTitulo(el) && i + 1 < bloques.length && !bloques[i + 1].saltar) {
        const sig = nodo(bloques[i + 1].html);
        if (sig) {
          cur.appendChild(sig);
          await listaImagenes(sig);
          const juntos = cabe();
          sig.remove();
          if (!juntos && cur.children.length > 1) {
            // Antes de bajar el encabezado: ¿lo que sigue se puede partir y
            // arrancar debajo de él? Si sí se queda, porque moverlo dejaría la
            // hoja anterior casi en blanco.
            const hueco = ALTO - cur.scrollHeight;
            const arranca = hueco > ALTO * 0.2 && partir(sig, hueco).length > 1;
            if (!arranca) { el.remove(); cerrar(); cur.appendChild(el); }
          }
        }
      }
      continue;
    }

    // No cupo.
    el.remove();
    const colocar = (trozos) => {
      for (const t of trozos) {
        cur.appendChild(t);
        if (!cabe() && cur.children.length > 1) { t.remove(); cerrar(); cur.appendChild(t); }
      }
    };
    if (cur.children.length) {
      // Todavía queda sitio en la hoja: si el bloque es partible, que empiece
      // aquí. Sin esto una tabla grande se iba entera a la hoja siguiente y
      // dejaba atrás su propio encabezado, solo, en media hoja en blanco.
      const hueco = ALTO - cur.scrollHeight;
      if (hueco > ALTO * 0.2) {
        const trozos = partir(el, hueco);
        if (trozos.length > 1) { colocar(trozos); continue; }
      }
      cerrar();
    }
    // Hoja vacía: el bloque es más alto que una hoja entera.
    cur.appendChild(el);
    await listaImagenes(el);
    if (!cabe()) { el.remove(); colocar(partir(el, ALTO)); }
  }
  cerrar();
  caja.remove();
  return hojas;
}
"""


def partes_del_manual():
    """Saca del manual su estilo, la portada, el índice y los bloques de cada sección."""
    html = io.open(FUENTE, encoding="utf-8").read()
    estilo = re.search(r"<style>.*?</style>", html, re.S).group(0)

    portada = re.search(r'<div class="page cover">(.*?)</div>\s*<nav class="toc page">', html, re.S).group(1)
    indice = re.search(r'<nav class="toc page">(.*?)</nav>', html, re.S).group(1)

    secciones = []
    for m in re.finditer(r'<section id="(s\d+)">(.*?)</section>', html, re.S):
        sid, cuerpo = m.group(1), m.group(2)
        tit = re.search(r'<h2 class="sec-title">([^<]+)</h2>', cuerpo)
        secciones.append({"id": sid, "titulo": (tit.group(1).strip() if tit else "Introducción"),
                          "html": cuerpo})
    return estilo, portada, indice, secciones


def bloques_de(secciones):
    """Cada hijo directo de la sección es un bloque indivisible."""
    salida = []
    for s in secciones:
        trozos = re.findall(
            r'<(p|h2|h3|h4|figure|table|ol|ul|div|blockquote)\b[^>]*>.*?</\1>|<hr\s*/?>',
            s["html"], re.S)
        # re.findall con grupos devuelve el grupo; hay que volver a recorrer con finditer
        trozos = [m.group(0) for m in re.finditer(
            r'<(p|h2|h3|h4|figure|table|ol|ul|div|blockquote)\b[^>]*>.*?</\1>|<hr\s*/?>',
            s["html"], re.S)]
        for i, t in enumerate(trozos):
            salida.append({"html": t, "saltar": i == 0, "sec": s["id"]})
    return salida


def construir(estilo, portada, indice, bloques_html, paginas_idx=None):
    from playwright.sync_api import sync_playwright
    base = ("<!DOCTYPE html><html lang=es><head><meta charset=utf-8>"
            "<title>Manual del sistema · Yelke</title>" + estilo + ESTILO_DOC + "</head><body>")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_context().new_page()
        pg.set_content(base + "</body></html>", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        hojas = pg.evaluate(JS_PAGINAR, {"bloques": bloques_html,
                                         "anchoMM": ANCHO_CONT, "altoMM": ALTO_CONT})
        b.close()
    return hojas


def documento(estilo, portada, indice, hojas, paginas_idx):
    """Arma el HTML final: portada, índice y una hoja por cada bloque paginado."""
    pie = ('<div class="pie"><span>Manual del sistema de costeo, venta y producción · Yelke</span>'
           '<span class="folio">%d</span></div>')

    # Portada
    tit = re.search(r"<h1>(.*?)</h1>", portada, re.S).group(1)
    dek = re.search(r'<p class="dek">(.*?)</p>', portada, re.S).group(1)
    ficha = re.search(r'<div class="meta">(.*?)</div>\s*$', portada, re.S)
    # `<div ...>` con atributos incluido: el aviso de que el ejemplo ya no existe
    # lleva un style y con `<div>` a secas se perdía.
    filas = re.findall(r"<div[^>]*>(.*?)</div>", ficha.group(1), re.S) if ficha else []
    filas = [f for f in filas if "novedades" not in f]
    # Los tres primeros renglones son la ficha; el aviso del ejemplo va aparte,
    # más discreto, para que la portada se lea limpia.
    aviso = next((f for f in filas if "ilustrativos" in f), "")
    datos = [f for f in filas if f != aviso][:3]
    p_portada = ('<div class="hoja portada"><p class="marca">Yelke</p><h1>%s</h1>'
                 '<p class="dek">%s</p><div class="ficha">%s</div>'
                 '%s<div class="sello">Documento interno · %s</div></div>'
                 % (tit, dek, "".join("<div>%s</div>" % f for f in datos),
                    ('<p class="aviso">%s</p>' % aviso) if aviso else "",
                    "octubre de 2026"))

    # Índice, con números de página si ya se conocen
    lis = re.findall(r'<li><a href="#(s\d+)">(.*?)</a>', indice)
    filas_idx = "".join(
        '<li><span>%s</span><span class="pt"></span><span class="pg">%s</span></li>'
        % (t, (paginas_idx or {}).get(sid, ""))
        for sid, t in lis)
    p_indice = ('<div class="hoja"><div class="contenido idx"><h2>Contenido</h2>'
                '<ol>%s</ol></div>%s</div>' % (filas_idx, pie % 2))

    cuerpo = [p_portada, p_indice]
    for i, h in enumerate(hojas):
        cuerpo.append('<div class="hoja"><div class="contenido">%s</div>%s</div>'
                      % (h, pie % (i + 3)))
    return ("<!DOCTYPE html><html lang=es><head><meta charset=utf-8>"
            "<title>Manual del sistema · Yelke</title>" + estilo + ESTILO_DOC +
            "</head><body>" + "".join(cuerpo) + "</body></html>")


def render(html, salida):
    from playwright.sync_api import sync_playwright
    io.open(TMP, "w", encoding="utf-8").write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_context().new_page()
        pg.goto("file://" + TMP, wait_until="networkidle")
        pg.wait_for_timeout(3500)
        pg.emulate_media(media="print")
        pg.pdf(path=salida, width="210mm", height="297mm", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        b.close()
    return salida


if __name__ == "__main__":
    estilo, portada, indice, secciones = partes_del_manual()
    bl = bloques_de(secciones)
    print("secciones: %d · bloques: %d" % (len(secciones), len(bl)))

    hojas = construir(estilo, portada, indice, bl)
    print("hojas de contenido: %d" % len(hojas))

    # En qué hoja arranca cada sección (portada=1, índice=2, contenido desde 3).
    paginas = {}
    idx = 0
    for i, h in enumerate(hojas):
        for s in secciones:
            if s["id"] not in paginas and ('>%s<' % s["titulo"]) in h:
                paginas[s["id"]] = i + 3
    render(documento(estilo, portada, indice, hojas, paginas), SALIDA)
    total = int(subprocess.run(["pdfinfo", SALIDA], capture_output=True, text=True)
                .stdout.split("Pages:")[1].split()[0])
    print("PDF: %s · %d páginas · %.1f MB" % (SALIDA, total, os.path.getsize(SALIDA) / 1048576.0))
    print("secciones ubicadas en el índice: %d de %d" % (len(paginas), len(secciones)))
