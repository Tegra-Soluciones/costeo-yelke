// Verificación en dos pasos (costeo_yelke/dos_pasos.py): la primera vez, después de la
// contraseña, la pantalla de login muestra el QR, la liga que abre la app de
// autenticación del celular y la clave en texto, y ahí mismo pide el primer código.
// Reemplaza continue_otp_app de frappe/templates/includes/login/login.js.
(function () {
	if (location.pathname.replace(/\/+$/, "") !== "/login") return;

	var celular = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
	var ESTILO = {
		caja: "text-align:left;color:var(--text-color,#1f272e);font-size:13px;line-height:1.45;padding-bottom:14px",
		titulo: "font-size:15px;font-weight:600;margin:0 0 4px",
		paso: "margin:12px 0 6px",
		num: "display:inline-flex;width:20px;height:20px;border-radius:50%;background:#f97316;color:#fff;font-size:11px;font-weight:700;align-items:center;justify-content:center;margin-right:6px",
		qr: "display:block;width:176px;height:176px;margin:8px auto;border-radius:8px",
		boton: "display:block;text-align:center;margin:8px 0;padding:10px 12px;border-radius:8px;background:#f97316;color:#fff;font-weight:600;text-decoration:none",
		clave: "display:flex;align-items:center;gap:8px;margin-top:6px;padding:8px 10px;border-radius:8px;background:var(--control-bg,#f4f5f6)",
		texto: "flex:1;font-family:ui-monospace,Menlo,monospace;font-size:14px;letter-spacing:.5px;word-break:break-all",
		copiar: "border:0;background:none;color:#ea580c;font-weight:600;font-size:12px;cursor:pointer;padding:0",
		nota: "color:var(--text-muted,#6b7280);font-size:12px;margin-top:4px",
	};

	function el(tag, estilo, texto) {
		var e = document.createElement(tag);
		if (estilo) e.style.cssText = estilo;
		if (texto) e.textContent = texto;
		return e;
	}

	function paso(n, texto) {
		var p = el("p", ESTILO.paso);
		p.appendChild(el("span", ESTILO.num, String(n)));
		p.appendChild(document.createTextNode(texto));
		return p;
	}

	function panelAlta(datos) {
		var caja = el("div", ESTILO.caja);
		caja.appendChild(el("p", ESTILO.titulo, "Activa la verificación en dos pasos"));
		caja.appendChild(el("p", ESTILO.nota, "Solo esta vez. Después, cada vez que entres te pedirá el código de la app."));

		caja.appendChild(paso(1, "Instala en tu celular Google Authenticator o Microsoft Authenticator."));

		var qr = el("img", ESTILO.qr);
		qr.src = "data:image/svg+xml;base64," + datos.svg;
		qr.alt = "Código QR para la app de autenticación";
		var abrir = el("a", ESTILO.boton, "Agregar a mi app de autenticación");
		abrir.href = datos.uri;

		if (celular) {
			caja.appendChild(paso(2, "Toca el botón para agregar tu cuenta de Yelke a la app:"));
			caja.appendChild(abrir);
			caja.appendChild(el("p", ESTILO.nota, "Si no se abre, en la app toca «+» › «Ingresar clave» y escribe esta clave:"));
		} else {
			caja.appendChild(paso(2, "En la app toca «+» › «Escanear código QR» y escanea este código:"));
			caja.appendChild(qr);
			caja.appendChild(el("p", ESTILO.nota, "¿No puedes escanear? En la app elige «Ingresar clave» y escribe esta:"));
		}

		var fila = el("div", ESTILO.clave);
		fila.appendChild(el("span", ESTILO.texto, datos.clave.replace(/(.{4})/g, "$1 ").trim()));
		var copiar = el("button", ESTILO.copiar, "Copiar");
		copiar.type = "button";
		copiar.onclick = function () {
			var listo = function () { copiar.textContent = "Copiada"; };
			if (navigator.clipboard) navigator.clipboard.writeText(datos.clave).then(listo, function () {});
		};
		fila.appendChild(copiar);
		caja.appendChild(fila);

		if (celular) {
			var otro = el("details", "margin-top:8px");
			otro.appendChild(el("summary", ESTILO.nota + ";cursor:pointer", "Escanear el QR desde otro celular"));
			otro.appendChild(qr);
			caja.appendChild(otro);
		}

		caja.appendChild(paso(3, "Escribe el código de 6 dígitos que te muestra la app:"));
		caja.appendChild(el("p", ESTILO.nota, "Tienes " + (datos.minutos || 15) + " minutos; si se vence, vuelve a poner tu contraseña."));
		return caja;
	}

	function ajustarCampo() {
		var campo = document.getElementById("login_token");
		if (!campo) return;
		campo.setAttribute("inputmode", "numeric");
		campo.setAttribute("autocomplete", "one-time-code");
		campo.setAttribute("maxlength", "7");
		campo.setAttribute("placeholder", "Código de 6 dígitos");
	}

	function instalar() {
		var original = window.continue_otp_app;
		if (typeof original !== "function" || original.yelke) return;
		var nueva = function (setup, datos) {
			original(setup, datos);
			ajustarCampo();
			if (setup || !datos || !datos.uri) return;
			var div = document.getElementById("otp_div");
			var aviso = document.getElementById("qr_info");  // «contacte al administrador»
			if (aviso && aviso.parentNode) aviso.parentNode.remove();
			if (div) div.insertBefore(panelAlta(datos), div.firstChild);
		};
		nueva.yelke = true;
		window.continue_otp_app = nueva;
	}

	instalar();
	document.addEventListener("DOMContentLoaded", instalar);
})();
