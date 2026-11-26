#!/bin/bash
# Copia de los respaldos de Yelke fuera del NAS (a esta computadora), por Tailscale.
#
# La instala un LaunchAgent (mx.tegra.respaldo-yelke) que la corre cada 3 horas y al
# despertar la Mac: trae lo nuevo de diario/, semanal/, mensual/ y previo-publicacion/
# del NAS. Conserva aquí 30 diarios y todo lo semanal/mensual (90 días / 24 meses).
#
#   DESTINO   carpeta local (por omisión ~/Trabajo/respaldos-yelke/nas)
#   NAS       alias de ssh del NAS (por omisión erpnext-yelke)
set -uo pipefail

NAS="${NAS:-erpnext-yelke}"
ORIGEN="/share/ZFS19_DATA/TEOCUITATL/Backups/erpnext-yelke"
DESTINO="${DESTINO:-$HOME/Trabajo/respaldos-yelke/nas}"
LOG="$DESTINO/sincronizacion.log"
mkdir -p "$DESTINO"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# sin conexión al NAS (fuera de Tailscale, sin red): se intenta en la siguiente vuelta
if ! ssh -o BatchMode=yes -o ConnectTimeout=15 "$NAS" true 2>/dev/null; then
	log "sin conexión al NAS; se reintenta luego"
	exit 0
fi

for sub in diario semanal mensual previo-publicacion; do
	if rsync -a --partial --timeout=300 -e "ssh -o BatchMode=yes" \
		--rsync-path=/usr/bin/rsync "$NAS:$ORIGEN/$sub/" "$DESTINO/$sub/" 2>>"$LOG"; then
		:
	else
		log "ERROR al copiar $sub"
	fi
done

# verificación de lo más reciente con su SHA256SUMS
ultimo=$(ls -1d "$DESTINO"/diario/20??-??-?? 2>/dev/null | sort | tail -1)
if [ -n "$ultimo" ] && [ -f "$ultimo/SHA256SUMS" ]; then
	if (cd "$ultimo" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1); then
		log "OK $(basename "$ultimo") verificado"
	else
		log "ERROR: $(basename "$ultimo") no coincide con su SHA256SUMS"
	fi
fi

# retención local
# (head -n -N no existe en macOS: se calcula a mano)
podar_mac() {
	local dirs n
	dirs=$(ls -1d "$1"/20??-??-?? 2>/dev/null | sort)
	n=$(printf '%s\n' "$dirs" | grep -c . || true)
	[ "$n" -gt "$2" ] && printf '%s\n' "$dirs" | head -n $(( n - $2 )) | while read -r d; do rm -rf "$d"; done
	return 0
}
podar_mac "$DESTINO/diario" 30
podar_mac "$DESTINO/semanal" 13
podar_mac "$DESTINO/mensual" 24
find "$DESTINO/previo-publicacion" -type f -mtime +90 -delete 2>/dev/null
tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
