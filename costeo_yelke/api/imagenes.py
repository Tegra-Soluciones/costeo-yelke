# Copyright (c) 2026, Ixoom and contributors
"""Imágenes desde un enlace: la imagen del producto del costeo también se puede dar como
URL (además de subirla del equipo o pegarla).

El enlace NO se guarda tal cual: la imagen se descarga y queda como un File más del
sistema, igual que si se hubiera subido. Así no desaparece si la página de origen la
quita o cambia, se ve en los PDF (wkhtmltopdf no siempre alcanza sitios externos) y el
artículo que se crea al cotizar la hereda como cualquier otra.
"""

import ipaddress
import socket
from io import BytesIO
from urllib.parse import urljoin, urlparse

import frappe
import requests
from frappe import _

MAX_BYTES = 10 * 1024 * 1024
MAX_REDIRECCIONES = 3
FORMATOS = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp", "BMP": "bmp"}


def _exigir_destino_publico(url):
	"""Solo direcciones públicas de internet: sin esto, el servidor podría pedirse a sí
	mismo o a la red interna (otros contenedores, el NAS) en nombre de quien escribe el
	enlace."""
	partes = urlparse(url)
	if partes.scheme not in ("http", "https") or not partes.hostname:
		frappe.throw(_("Escribe un enlace completo que empiece con http:// o https://."))
	try:
		direcciones = {info[4][0] for info in socket.getaddrinfo(partes.hostname, partes.port or None)}
	except socket.gaierror:
		frappe.throw(_("No se encontró el sitio «{0}». Revisa el enlace.").format(partes.hostname))
	for ip in direcciones:
		if not ipaddress.ip_address(ip.split("%")[0]).is_global:
			frappe.throw(_("Ese enlace apunta a una dirección interna; usa el enlace público de la imagen."))


def _descargar(url):
	"""Descarga siguiendo redirecciones a mano, para revisar el destino de cada salto."""
	for _salto in range(MAX_REDIRECCIONES + 1):
		_exigir_destino_publico(url)
		try:
			r = requests.get(url, timeout=(5, 20), stream=True, allow_redirects=False,
							 headers={"User-Agent": "Mozilla/5.0 (Costeo Yelke)"})
		except requests.RequestException:
			frappe.throw(_("No se pudo descargar la imagen de ese enlace. Revisa que abra en el navegador."))
		if r.is_redirect:
			url = urljoin(url, r.headers.get("Location", ""))
			continue
		if r.status_code != 200:
			frappe.throw(_("El sitio respondió con un error ({0}) al pedir la imagen.").format(r.status_code))
		contenido = BytesIO()
		for trozo in r.iter_content(64 * 1024):
			contenido.write(trozo)
			if contenido.tell() > MAX_BYTES:
				frappe.throw(_("La imagen pesa más de 10 MB."))
		return contenido.getvalue(), r.headers.get("Content-Type", "")
	frappe.throw(_("El enlace redirige demasiadas veces."))


@frappe.whitelist()
def imagen_desde_enlace(url: str, doctype: str | None = None, docname: str | None = None) -> dict:
	"""Descarga la imagen del enlace y la guarda como File (privado, como las subidas).
	Devuelve su file_url."""
	from PIL import Image

	url = (url or "").strip()
	contenido, tipo = _descargar(url)
	# Se revisa que de verdad sea una imagen (no solo lo que diga el sitio): el error más
	# común es copiar el enlace de la PÁGINA donde aparece la imagen, no el de la imagen.
	try:
		formato = Image.open(BytesIO(contenido)).format
	except Exception:
		formato = None
	if formato not in FORMATOS:
		if "html" in tipo:
			frappe.throw(_("Ese enlace es de una página, no de una imagen. Abre la imagen sola "
						   "(clic derecho → «Abrir imagen en otra pestaña») y copia esa dirección."))
		frappe.throw(_("Ese enlace no es una imagen JPG, PNG, GIF o WEBP."))

	nombre = urlparse(url).path.rsplit("/", 1)[-1].split("?")[0] or "imagen"
	base = nombre.rsplit(".", 1)[0][:80] or "imagen"
	archivo = {"doctype": "File", "file_name": f"{base}.{FORMATOS[formato]}", "content": contenido, "is_private": 1}
	if doctype and docname and frappe.db.exists(doctype, docname):
		archivo.update({"attached_to_doctype": doctype, "attached_to_name": docname})
	f = frappe.get_doc(archivo)
	f.insert(ignore_permissions=True)
	return {"file_url": f.file_url}
