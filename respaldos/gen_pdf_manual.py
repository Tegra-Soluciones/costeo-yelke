"""Genera el PDF del manual, cuidando que nada quede cortado entre hojas.

El manual en pantalla es una sola página larga; en papel hay que decidir dónde
corta cada hoja. Sin reglas, el navegador parte por donde le toque: una imagen a
la mitad, un encabezado solo al pie, una tabla de la que solo pasa un renglón.

Lo que se le impone:
  · cada sección arranca en hoja nueva;
  · figuras, tablas, avisos, pasos y tarjetas no se parten NUNCA;
  · un encabezado nunca se queda sin al menos una línea de su texto debajo;
  · una imagen alta se escala para caber en una hoja en vez de cortarse;
  · nada de líneas sueltas al principio o al final de una hoja (viudas/huérfanas).

Uso:  python3 respaldos/gen_pdf_manual.py
Deja el PDF en respaldos/Manual-Costeo-Yelke.pdf
"""
import io
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, "..", "costeo_yelke", "www", "manual-costeo.html")
TMP_HTML = "/tmp/manual_print.html"
SALIDA = os.path.join(AQUI, "Manual-Costeo-Yelke.pdf")

# Alto útil de una hoja carta con los márgenes de abajo, en milímetros:
# 279.4 (carta) - 18 (arriba) - 20 (abajo) = 241. Se deja holgura para el pie.
ALTO_UTIL_MM = 225

CSS_IMPRESION = """
<style id="css-impresion">
@page { size: Letter; margin: 18mm 16mm 20mm 16mm; }

/* El ancho lo manda la hoja, no el contenedor de pantalla. */
.page { max-width: 100%% !important; padding: 0 !important; margin: 0 !important; }

/* Portada e índice, cada uno en su hoja. */
.cover { padding-top: 24mm !important; padding-bottom: 0 !important; break-after: page; }
.cover h1 { font-size: 34px; }
/* Las novedades son una lista larga: en pantalla caben debajo de la portada, en
   papel la desbordaban y empujaban el índice. Van en su propia hoja. */
.meta > div:last-child { break-before: page; padding-top: 6mm; }
.novedades { font-size: 15px; display: block; margin-bottom: 10px; }
.novedades-list li { margin-bottom: 7px; }

nav.toc { padding: 0 !important; break-after: page; }
nav.toc li { padding: 9px 0; }
nav.toc .toc-pag { margin-left: auto; font-size: 13px; color: #8b8b93;
  font-variant-numeric: tabular-nums; padding-left: 10px; }

/* Cada sección empieza en hoja nueva. La primera no, para no dejar una en blanco. */
section { break-before: page; border-top: none !important; padding: 0 0 6mm !important; }
section:first-of-type { break-before: auto; }

/* Lo que NUNCA se parte entre hojas. */
figure, .callout, .role-card, .two-col,
ol.steps li, ul.plain li, tr { break-inside: avoid; page-break-inside: avoid; }

/* Las TABLAS sí pueden partirse, pero solo entre renglones: cada renglón queda
   entero (regla de arriba) y el encabezado se repite en la hoja siguiente. Si se
   les prohibe partirse, una tabla más alta que una hoja -- como la del glosario --
   se empuja completa a la hoja siguiente, deja la anterior en blanco y de todos
   modos acaba partiéndose. */
table { break-inside: auto; page-break-inside: auto; }

/* Un encabezado jamás se queda solo al pie de la hoja. El subtítulo de sección
   (.sec-dek) NO lleva esta regla a propósito: es un párrafo largo, y obligarlo a
   pegarse al bloque siguiente hacía que se partiera a media frase cuando lo que
   venía detrás era una tabla grande que no cabía. */
h2, h3, h4, .sec-title { break-after: avoid; page-break-after: avoid; }
.sec-dek { break-inside: avoid; }

/* Una imagen alta se escala para caber en UNA hoja en vez de cortarse. */
figure img, figure svg {
  max-height: %(alto)smm; width: auto; max-width: 100%%;
  display: block; margin: 0 auto;
}
figcaption { break-before: avoid; }

/* Si una tabla llegara a partirse, su encabezado se repite en la hoja siguiente. */
thead { display: table-header-group; }

/* Nada de líneas sueltas arriba o abajo de una hoja. */
p, li, td { orphans: 3; widows: 3; }

/* Los enlaces internos no sirven en papel: que no se vean como enlaces. */
a { color: inherit !important; text-decoration: none !important; }

/* Que los fondos de los avisos y los encabezados de tabla sí se impriman. */
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
</style>
"""


def construir_html():
    html = io.open(FUENTE, encoding="utf-8").read()
    css = CSS_IMPRESION % {"alto": ALTO_UTIL_MM}
    assert "</head>" in html
    html = html.replace("</head>", css + "</head>", 1)
    io.open(TMP_HTML, "w", encoding="utf-8").write(html)
    return TMP_HTML


def render(ruta_html):
    from playwright.sync_api import sync_playwright
    pie = (
        '<div style="width:100%;font-size:8pt;color:#8b8b93;'
        'font-family:Inter,-apple-system,Segoe UI,sans-serif;'
        'padding:0 16mm;display:flex;justify-content:space-between;">'
        '<span>Manual del sistema · Yelke</span>'
        '<span class="pageNumber"></span></div>'
    )
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_context().new_page()
        pg.goto("file://" + ruta_html, wait_until="networkidle")
        pg.wait_for_timeout(4000)
        pg.emulate_media(media="print")
        pg.pdf(path=SALIDA, format="Letter", print_background=True,
               display_header_footer=True,
               header_template='<div></div>', footer_template=pie,
               margin={"top": "18mm", "right": "16mm", "bottom": "20mm", "left": "16mm"})
        b.close()
    return SALIDA


def paginas_de_secciones(pdf, titulos):
    """En qué página del PDF arranca cada sección, leyendo el texto del propio PDF.

    Un índice impreso sin números de página no sirve para nada, y los números no se
    pueden saber antes de maquetar: hay que generar el PDF, leerlo y volver a
    generarlo con los números puestos."""
    import subprocess
    total = int(subprocess.run(["pdfinfo", pdf], capture_output=True, text=True)
                .stdout.split("Pages:")[1].split()[0])
    encontrados, pendientes = {}, list(titulos)
    for n in range(1, total + 1):
        txt = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), pdf, "-"],
                             capture_output=True, text=True).stdout
        # el título de sección es lo primero de su hoja: basta mirar el arranque
        cabeza = "\n".join(txt.strip().splitlines()[:3])
        for t in list(pendientes):
            if t and t in cabeza:
                encontrados[t] = n
                pendientes.remove(t)
    return encontrados


def inyectar_paginas(ruta_html, mapa, titulos_por_id):
    import re
    html = io.open(ruta_html, encoding="utf-8").read()
    for sid, titulo in titulos_por_id.items():
        pag = mapa.get(titulo)
        if not pag:
            continue
        patron = r'(<li><a href="#%s">[^<]*)(</a></li>)' % sid
        html = re.sub(patron, r'\1</a><span class="toc-pag">%d</span></li>' % pag, html, count=1)
    io.open(ruta_html, "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    import re
    ruta = construir_html()
    pdf = render(ruta)

    # Pasada 2: leer en qué página quedó cada sección y escribirlo en el índice.
    fuente = io.open(FUENTE, encoding="utf-8").read()
    titulos = {}
    for m in re.finditer(r'<section id="(s\d+)">', fuente):
        t = re.search(r'sec-title">([^<]+)', fuente[m.end():m.end() + 400])
        titulos[m.group(1)] = (t.group(1).strip() if t else "Introducción")
    mapa = paginas_de_secciones(pdf, set(titulos.values()))
    inyectar_paginas(ruta, mapa, titulos)
    pdf = render(ruta)
    print("índice con números de página: %d de %d secciones ubicadas" % (len(mapa), len(titulos)))
    print("PDF: %s  (%.1f MB)" % (pdf, os.path.getsize(pdf) / 1048576.0))
