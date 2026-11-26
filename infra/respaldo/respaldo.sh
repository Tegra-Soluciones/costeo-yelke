#!/bin/bash
# Respaldos de producción de Yelke (erp.yelke.com.mx).
#
# Corre dentro del contenedor «respaldo» del stack cimix-yelke (misma imagen que el
# backend: trae bench, mysqldump y python). Los respaldos se escriben en /respaldos,
# que en el NAS es /share/TEOCUITATL/Backups/erpnext-yelke: otro grupo de discos
# (zpool2) distinto del que tiene la base y los archivos del sitio (zpool1).
#
#   respaldo.sh servicio    bucle del contenedor (lo que corre siempre)
#   respaldo.sh completo    base + archivos ahora (formato estándar de ERPNext)
#   respaldo.sh bd          solo la base ahora (mysqldump con posición del binlog)
#   respaldo.sh estado      imprime el estado
#
# Calendario (hora de México):
#   cada 15 min   copia los respaldos previos a publicación que deja update_costeo.sh
#   cada hora     cierra el binlog en curso y lo copia (recuperación a un punto en el
#                 tiempo: lo más que se pierde si se pierde el disco de la base es 1 h)
#   02:00         completo -> diario/ (14 días); domingo también semanal/ (8 semanas);
#                 día 1 también mensual/ (12 meses)
#   08, 14, 20 h  base -> bd/ (3 días)
#   lunes 08:00   correo de resumen (si no llega, algo está mal)
# Al arrancar, si el último completo tiene más de 26 h o la última base más de 7 h,
# se hacen en ese momento.
#
# Cualquier falla manda correo a ALERTA (una vez por falla, y se repite cada 6 h si
# sigue). Además publica /files/<SALUD_ARCHIVO> que revisa el monitor de GitHub.

set -uo pipefail

SITE="${SITE:-erp.yelke.com.mx}"
BENCH=/home/frappe/frappe-bench
DEST="${DEST:-/respaldos}"
ALERTA="${ALERTA:-daniel@tegra.mx}"
DB_HOST="${DB_HOST:-mariadb}"
DIAS_DIARIO=14; SEMANAS=8; MESES=12; DIAS_BD=3; DIAS_BINLOG=15; DIAS_PREVIO=30

ESTADO="$DEST/estado"
mkdir -p "$DEST"/{diario,semanal,mensual,bd,binlog,previo-publicacion,tmp} "$ESTADO"

log() { echo "[$(date '+%F %T')] $*"; }
ahora() { date +%s; }

nombre_bd() {
	python3 -c "import json;print(json.load(open('$BENCH/sites/$SITE/site_config.json'))['db_name'])"
}

# ── correo ────────────────────────────────────────────────────────────────────
correo() {  # correo <asunto> <texto>
	local kwargs
	kwargs=$(ASUNTO="$1" TEXTO="$2" PARA="$ALERTA" python3 -c '
import json, os, html
cuerpo = "<pre style=\"font-family:monospace;font-size:13px\">" + html.escape(os.environ["TEXTO"]) + "</pre>"
print(repr({"recipients": [os.environ["PARA"]], "subject": os.environ["ASUNTO"],
                  "message": cuerpo, "now": True}))')
	(cd "$BENCH" && timeout 120 bench --site "$SITE" execute frappe.sendmail --kwargs "$kwargs") >"$ESTADO/correo.log" 2>&1
}

falla() {  # falla <clave> <texto>
	local clave="$1" texto="$2" marca="$ESTADO/alerta-$1"
	log "FALLA [$clave] $texto"
	echo "$(ahora) $texto" > "$ESTADO/falla-$clave"
	if [ ! -f "$marca" ] || [ $(( $(ahora) - $(stat -c %Y "$marca") )) -gt 21600 ]; then
		if correo "⚠ Yelke: falla en respaldos ($clave)" "$texto

Servidor: NAS TGRYlotl, contenedor cimix-yelke-respaldo-1
Últimos respaldos:
$(resumen)"; then touch "$marca"; else log "no se pudo mandar el correo de alerta"; fi
	fi
	publicar_salud
	return 1
}

resuelto() {  # resuelto <clave>
	local clave="$1"
	if [ -f "$ESTADO/falla-$clave" ]; then
		rm -f "$ESTADO/falla-$clave" "$ESTADO/alerta-$clave"
		correo "✓ Yelke: respaldos ($clave) de nuevo bien" "$(resumen)" || true
	fi
}

# ── verificaciones ────────────────────────────────────────────────────────────
verificar_sql_gz() {  # <archivo> <bytes mínimos>
	local f="$1" min="$2"
	[ -s "$f" ] || { echo "no existe o está vacío: $f"; return 1; }
	[ "$(stat -c %s "$f")" -ge "$min" ] || { echo "demasiado chico ($(stat -c %s "$f") bytes): $f"; return 1; }
	gzip -t "$f" 2>/dev/null || { echo "gzip dañado: $f"; return 1; }
	zcat "$f" | tail -c 300 | grep -q "Dump completed" || { echo "el volcado no terminó: $f"; return 1; }
	{ zcat "$f" || true; } | grep -q -m1 'CREATE TABLE `tabCosteo`' || { echo "no trae la tabla tabCosteo: $f"; return 1; }
}

# ── respaldos ─────────────────────────────────────────────────────────────────
respaldo_bd() {
	local db tmp final err
	db=$(nombre_bd) || { falla bd "no pude leer site_config.json"; return 1; }
	tmp="$DEST/tmp/bd-$(date +%Y%m%d_%H%M).sql.gz"
	final="$DEST/bd/$(basename "$tmp")"
	log "base: inicia ($db)"
	# Con binlog activo, el volcado anota su posición para luego aplicar los binlogs.
	local posicion=()
	[ "$(mysql -h "$DB_HOST" -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e 'SELECT @@log_bin' 2>/dev/null)" = 1 ] && posicion=(--master-data=2)
	if ! mysqldump -h "$DB_HOST" -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --quick \
		--routines --triggers --events --hex-blob "${posicion[@]}" --databases "$db" 2>"$ESTADO/bd.err" | gzip -6 > "$tmp"; then
		rm -f "$tmp"; falla bd "mysqldump falló: $(tail -3 "$ESTADO/bd.err")"; return 1
	fi
	if ! err=$(verificar_sql_gz "$tmp" 1000000); then rm -f "$tmp"; falla bd "$err"; return 1; fi
	mv "$tmp" "$final"
	ahora > "$ESTADO/ultimo-bd"; echo "$final" >> "$ESTADO/ultimo-bd"
	find "$DEST/bd" -name '*.sql.gz' -mtime +$DIAS_BD -delete
	log "base: OK $(stat -c %s "$final") bytes $final"
	resuelto bd
	publicar_salud
}

respaldo_completo() {
	local tmp dir dia f err
	dia=$(date +%F)
	tmp="$DEST/tmp/completo-$dia"
	dir="$DEST/diario/$dia"
	rm -rf "$tmp"; mkdir -p "$tmp"
	log "completo: inicia"
	if ! (cd "$BENCH" && timeout 3600 bench --site "$SITE" backup --with-files --backup-path "$tmp") > "$ESTADO/completo.log" 2>&1; then
		falla completo "bench backup falló: $(tail -5 "$ESTADO/completo.log")"; rm -rf "$tmp"; return 1
	fi
	f=$(ls "$tmp"/*-database.sql.gz 2>/dev/null | head -1)
	if ! err=$(verificar_sql_gz "$f" 1000000); then falla completo "$err"; rm -rf "$tmp"; return 1; fi
	for tipo in files.tar private-files.tar site_config_backup.json; do
		ls "$tmp"/*-"$tipo" >/dev/null 2>&1 || { falla completo "falta el archivo *-$tipo"; rm -rf "$tmp"; return 1; }
	done
	for t in "$tmp"/*.tar; do
		tar tf "$t" >/dev/null 2>&1 || { falla completo "tar dañado: $t"; rm -rf "$tmp"; return 1; }
	done
	grep -q encryption_key "$tmp"/*-site_config_backup.json || { falla completo "site_config sin encryption_key"; rm -rf "$tmp"; return 1; }
	(cd "$tmp" && sha256sum -- * > SHA256SUMS)
	rm -rf "$dir"; mv "$tmp" "$dir"
	# domingo -> semanal, día 1 -> mensual (ligas duras: no ocupan espacio extra)
	[ "$(date +%u)" = 7 ] && { rm -rf "$DEST/semanal/$dia"; cp -al "$dir" "$DEST/semanal/$dia"; }
	[ "$(date +%d)" = 01 ] && { rm -rf "$DEST/mensual/$dia"; cp -al "$dir" "$DEST/mensual/$dia"; }
	podar "$DEST/diario" $DIAS_DIARIO; podar "$DEST/semanal" $SEMANAS; podar "$DEST/mensual" $MESES
	ahora > "$ESTADO/ultimo-completo"; echo "$dir" >> "$ESTADO/ultimo-completo"
	# el completo trae la base: cuenta también como respaldo de base
	ahora > "$ESTADO/ultimo-bd"; echo "$f" | sed "s#$tmp#$dir#" >> "$ESTADO/ultimo-bd"
	log "completo: OK $(du -cb "$dir"/* | tail -1 | cut -f1) bytes $dir"
	resuelto completo
	publicar_salud
}

podar() {  # podar <carpeta> <cuántos conservar>  (carpetas con nombre AAAA-MM-DD)
	ls -1d "$1"/20??-??-?? 2>/dev/null | sort | head -n -"$2" | while read -r d; do rm -rf "$d"; done
}

copiar_binlogs() {
	# Se bajan por la red con mariadb-binlog (no hace falta acceso a los archivos de la
	# base). Solo los ya cerrados: todos menos el último de SHOW BINARY LOGS.
	local logs actual b
	logs=$(mysql -h "$DB_HOST" -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "SHOW BINARY LOGS" 2>/dev/null | cut -f1) || return 0
	[ -n "$logs" ] || return 0   # binlog apagado
	actual=$(echo "$logs" | tail -1)
	for b in $logs; do
		[ "$b" = "$actual" ] && continue
		[ -f "$DEST/binlog/$b" ] && continue
		if (cd "$DEST/tmp" && rm -f "$b" && mariadb-binlog -h "$DB_HOST" -uroot -p"$MYSQL_ROOT_PASSWORD" \
				--read-from-remote-server --raw "$b" 2>"$ESTADO/binlog.err") && [ -s "$DEST/tmp/$b" ]; then
			mv "$DEST/tmp/$b" "$DEST/binlog/$b"
			resuelto binlog
		else
			rm -f "$DEST/tmp/$b"; falla binlog "no pude copiar el binlog $b: $(tail -2 "$ESTADO/binlog.err")"; return 1
		fi
	done
	find "$DEST/binlog" -name 'mysql-bin.*' -mtime +$DIAS_BINLOG -delete
}

cerrar_binlog() {
	# Cierra el binlog en curso para que lo capturado hasta ahora quede copiado.
	mysql -h "$DB_HOST" -uroot -p"$MYSQL_ROOT_PASSWORD" -e "FLUSH BINARY LOGS" 2>/dev/null || true
}

copiar_previos_publicacion() {
	# update_costeo.sh --backup deja el respaldo en sites/<sitio>/private/backups (en el
	# mismo volumen que el sitio, y Frappe solo conserva unos cuantos): se copian aquí.
	local src="$BENCH/sites/$SITE/private/backups"
	[ -d "$src" ] || return 0
	find "$src" -maxdepth 1 -type f -mmin +2 | while read -r f; do
		[ -f "$DEST/previo-publicacion/$(basename "$f")" ] || cp -p "$f" "$DEST/previo-publicacion/"
	done
	find "$DEST/previo-publicacion" -type f -mtime +$DIAS_PREVIO -delete
}

# ── estado ────────────────────────────────────────────────────────────────────
edad_h() {  # horas desde el último <bd|completo>, o 9999
	local f="$ESTADO/ultimo-$1"
	[ -f "$f" ] || { echo 9999; return; }
	echo $(( ($(ahora) - $(head -1 "$f")) / 3600 ))
}

resumen() {
	echo "Último completo: $(tail -1 "$ESTADO/ultimo-completo" 2>/dev/null || echo ninguno) (hace $(edad_h completo) h)"
	echo "Última base:     $(tail -1 "$ESTADO/ultimo-bd" 2>/dev/null || echo ninguna) (hace $(edad_h bd) h)"
	echo "Diarios: $(ls -1d "$DEST"/diario/20* 2>/dev/null | wc -l) · semanales: $(ls -1d "$DEST"/semanal/20* 2>/dev/null | wc -l) · mensuales: $(ls -1d "$DEST"/mensual/20* 2>/dev/null | wc -l) · binlogs: $(ls -1 "$DEST"/binlog/mysql-bin.* 2>/dev/null | wc -l)"
	echo "Espacio usado: $(du -sh "$DEST" 2>/dev/null | cut -f1)"
	local fallas; fallas=$(cat "$ESTADO"/falla-* 2>/dev/null)
	[ -n "$fallas" ] && echo "Fallas abiertas:" && echo "$fallas"
	return 0
}

publicar_salud() {
	# Lo lee el monitor de GitHub (.github/workflows/monitor-produccion.yml). Solo fechas.
	[ -n "${SALUD_ARCHIVO:-}" ] || return 0
	local f="$BENCH/sites/$SITE/public/files/$SALUD_ARCHIVO"
	printf '{"completo_h": %s, "bd_h": %s, "fallas": %s, "generado": "%s"}\n' \
		"$(edad_h completo)" "$(edad_h bd)" "$(ls "$ESTADO"/falla-* 2>/dev/null | wc -l)" "$(date -Iseconds)" > "$f.tmp" \
		&& mv "$f.tmp" "$f"
}

# ── servicio ──────────────────────────────────────────────────────────────────
servicio() {
	log "servicio de respaldos iniciado (sitio $SITE, destino $DEST, alertas a $ALERTA)"
	sleep 60  # que la base y el sitio terminen de arrancar
	[ "$(edad_h completo)" -ge 26 ] && respaldo_completo
	[ "$(edad_h bd)" -ge 7 ] && respaldo_bd
	publicar_salud
	while true; do
		# despierta en el siguiente múltiplo de 15 minutos
		sleep $(( 900 - $(ahora) % 900 + 5 ))
		local h m u
		h=$(date +%H); m=$(date +%M); u=$(date +%u)
		copiar_previos_publicacion
		if [ "$m" -lt 15 ]; then
			case "$h" in
				02) respaldo_completo ;;
				08|14|20) respaldo_bd ;;
			esac
			[ "$h" = 08 ] && [ "$u" = 1 ] && correo "Yelke: resumen semanal de respaldos" "$(resumen)"
		fi
		# cada hora se cierra el binlog en curso y se copia (pérdida máxima: 1 hora)
		[ "$m" -lt 15 ] && cerrar_binlog
		copiar_binlogs
		# Red de seguridad: si por lo que sea no se ha hecho, se avisa.
		[ "$(edad_h completo)" -ge 30 ] && falla vencido "El último respaldo completo tiene $(edad_h completo) horas."
		[ "$(edad_h completo)" -lt 30 ] && resuelto vencido
		publicar_salud
	done
}

case "${1:-servicio}" in
	servicio) servicio ;;
	completo) respaldo_completo ;;
	bd) respaldo_bd ;;
	binlog) cerrar_binlog; copiar_binlogs ;;
	estado) resumen ;;
	correo-prueba) correo "Yelke: prueba de alerta de respaldos" "Si te llega este correo, las alertas de respaldos funcionan.

$(resumen)" && echo enviado ;;
	*) echo "uso: $0 servicio|completo|bd|binlog|estado|correo-prueba"; exit 2 ;;
esac
