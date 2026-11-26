#!/bin/bash
# Mueve los datos de MariaDB de Yelke del volumen de Docker (dataset compartido con
# todos los contenedores del NAS, zpool1/zfs530/zfs5300002) a una carpeta compartida
# propia (su propio dataset ZFS, con su propio ZIL), y activa el binlog.
#
# Uso (en el NAS):  bash mover-base-a-dataset-propio.sh /share/ZFSnn_DATA/YelkeDatos
#
# El volumen viejo (erpnext-yelke-mariadb) NO se borra: para regresar, se restaura el
# docker-compose.yml que se guarda en /share/ZFS18_DATA/Container/yelke-respaldo/ y
# se recrea el servicio mariadb.
set -euo pipefail
export PATH=/share/ZFS530_DATA/.qpkg/container-station/bin:$PATH

DATOS="${1:?falta la carpeta del dataset propio}"
NUEVO="$DATOS/mariadb"
APPD=/share/ZFS18_DATA/Container/container-station-data/application/cimix-yelke
GUARDA=/share/ZFS18_DATA/Container/yelke-respaldo
APP="cimix-yelke-frontend-1 cimix-yelke-backend-1 cimix-yelke-websocket-1 cimix-yelke-queue-short-1 cimix-yelke-queue-long-1 cimix-yelke-scheduler-1 cimix-yelke-respaldo-1"
paso() { echo; echo "==> $(date '+%T') $*"; }

[ -d "$DATOS" ] || { echo "no existe $DATOS"; exit 1; }
if [ -d "$NUEVO" ] && [ -n "$(ls -A "$NUEVO")" ]; then echo "$NUEVO ya tiene datos; no se toca"; exit 1; fi
grep -q -- '- mariadb-data:/var/lib/mysql' "$APPD/docker-compose.yml" || { echo "el compose ya no usa mariadb-data"; exit 1; }

paso "respaldo completo antes de mover"
docker exec cimix-yelke-respaldo-1 bash /opt/respaldo/respaldo.sh completo

paso "detener la aplicación y la base"
docker stop $APP >/dev/null
docker stop -t 180 cimix-yelke-mariadb-1 >/dev/null

paso "copiar datos a $NUEVO"
mkdir -p "$NUEVO"
docker run --rm -v erpnext-yelke-mariadb:/viejo:ro -v "$NUEVO":/nuevo alpine sh -c 'cp -a /viejo/. /nuevo/ && sync'

paso "comparar copia (md5 de cada archivo)"
docker run --rm -v erpnext-yelke-mariadb:/viejo:ro -v "$NUEVO":/nuevo:ro alpine sh -c \
	'cd /viejo && find . -type f -exec md5sum {} + | sort -k2 > /tmp/a && cd /nuevo && md5sum -c -s /tmp/a && echo "copia idéntica: $(wc -l < /tmp/a) archivos"'

paso "docker-compose.yml: base en el dataset propio + binlog"
cp "$APPD/docker-compose.yml" "$GUARDA/docker-compose.yml.antes-bd-propia-$(date +%Y%m%d%H%M)"
awk -v nuevo="$NUEVO" '
	/^      - mariadb-data:\/var\/lib\/mysql$/ { print "      - " nuevo ":/var/lib/mysql"; next }
	/^      - --innodb-buffer-pool-size=2G$/ {
		print
		print "      - --log-bin=mysql-bin"
		print "      - --server-id=1"
		print "      - --binlog-format=ROW"
		print "      - --sync-binlog=1"
		print "      - --expire-logs-days=10"
		next }
	{ print }' "$APPD/docker-compose.yml" > /tmp/dc.nuevo
grep -q -- "- $NUEVO:/var/lib/mysql" /tmp/dc.nuevo && grep -q -- '--log-bin=mysql-bin' /tmp/dc.nuevo
cat /tmp/dc.nuevo > "$APPD/docker-compose.yml"; rm /tmp/dc.nuevo
cd "$APPD"
docker compose -f docker-compose.yml config -q

paso "levantar la base"
docker compose -f docker-compose.yml up -d --no-deps --pull never mariadb
for i in $(seq 1 60); do
	[ "$(docker inspect -f '{{.State.Health.Status}}' cimix-yelke-mariadb-1)" = healthy ] && break
	sleep 3
done
docker inspect -f '{{.State.Health.Status}} {{range .Mounts}}{{.Source}}{{end}}' cimix-yelke-mariadb-1

paso "levantar la aplicación"
docker start $APP >/dev/null
docker ps --format '{{.Names}} {{.Status}}' | grep cimix-yelke
