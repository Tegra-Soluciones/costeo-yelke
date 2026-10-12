#!/usr/bin/env bash
# Corre una fase de la limpieza de los ejemplos de capacitacion en produccion.
#
#   bash respaldos/limpiar-produccion.sh 0   -> solo mira, no cambia nada
#   bash respaldos/limpiar-produccion.sh 1   -> facturas, recibos, OC, OV, planes...
#   bash respaldos/limpiar-produccion.sh 2   -> BOM y fichas de manufactura
#   bash respaldos/limpiar-produccion.sh 3   -> costeos a borrador + verificacion
#
# Copia el script de la fase al QNAP, de ahi al contenedor, y lo ejecuta dentro de
# `bench console`. Se usa `exec(open(...).read(), {})` en vez de pegar el archivo
# por stdin porque la consola es IPython y los bloques con lineas en blanco se le
# rompen al pegarlos.
set -euo pipefail

FASE="${1:?uso: $0 0|1|2|3}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTENEDOR=cimix-yelke-backend-1
SITIO=erp.yelke.com.mx

if [ "$FASE" = "0" ]; then
  LOCAL="$DIR/verificar-produccion.py"
else
  LOCAL="$DIR/borrar-ejemplos-fase${FASE}.py"
fi
[ -f "$LOCAL" ] || { echo "no existe $LOCAL"; exit 1; }
REMOTO="/tmp/$(basename "$LOCAL")"

echo "→ copiando $(basename "$LOCAL") al servidor"
scp -q "$LOCAL" erpnext-yelke:"$REMOTO"

echo "→ ejecutando en $SITIO"
# `bash -l -s`: shell de login (sin eso `docker` no esta en el PATH) leyendo el
# guion de aqui abajo.
ssh erpnext-yelke bash -l -s <<REMOTO_EOF
set -e
docker cp "$REMOTO" "${CONTENEDOR}:${REMOTO}"
echo "exec(open('${REMOTO}').read(), {})" \
  | docker exec -i "${CONTENEDOR}" bash -lc "cd /home/frappe/frappe-bench && bench --site ${SITIO} console"
REMOTO_EOF

echo "→ fase ${FASE} terminada"
