# Respaldos y monitoreo de producción (erp.yelke.com.mx)

Cumple la cláusula Décima Segunda del contrato: diario conservado 7 días, semanal 4 semanas y uno antes de cada publicación. Aquí se conserva más de lo comprometido.

## Qué hay y dónde

| Qué | Dónde | Cada cuándo | Se conserva |
|---|---|---|---|
| Completo: base, archivos públicos y privados, `site_config` (formato estándar de ERPNext) | NAS `/share/ZFS19_DATA/TEOCUITATL/Backups/erpnext-yelke/diario/AAAA-MM-DD/` | 02:00 | 14 días |
| Semanal y mensual (ligas duras del diario) | `semanal/`, `mensual/` | domingo y día 1 | 8 semanas y 12 meses |
| Solo la base (`mysqldump` con la posición del binlog) | `bd/` | 08, 14 y 20 h | 3 días |
| Binlogs: todo cambio desde el último respaldo | `binlog/` | cada hora | 15 días |
| Respaldo previo a cada publicación (`update_costeo.sh --backup`) | `previo-publicacion/` | al publicar | 30 días |
| Copia fuera del NAS | Mac de Daniel `~/Trabajo/respaldos-yelke/nas/` (LaunchAgent `mx.tegra.respaldo-yelke`) | cada 3 h | 30 diarios, 13 semanales, 24 mensuales |

- **Discos:** los respaldos viven en `zpool2` (mirror de discos duros). La base y el sitio viven en `zpool1` (mirror de SSD), así que la falla de un grupo de discos no se lleva los dos.
- **Snapshots:** TEOCUITATL además tiene los snapshots del NAS.
- **Quién lo corre:** el contenedor `cimix-yelke-respaldo-1`, servicio `respaldo` del `docker-compose.yml` del stack `cimix-yelke`, con `respaldo.sh servicio`. El script vive en el NAS en `/share/ZFS18_DATA/Container/yelke-respaldo/respaldo.sh`; esta carpeta es su copia versionada.
- **Verificación:** cada respaldo se revisa antes de darse por bueno:
  - el gzip está íntegro y el volcado terminó («Dump completed»);
  - trae `tabCosteo`;
  - los tar se pueden leer;
  - `site_config` trae `encryption_key`;
  - se genera un `SHA256SUMS`.

## Avisos

- **Correo a daniel@tegra.mx:** desde la cuenta «Notificaciones» del sitio.
  - Llega cuando algo falla; si sigue fallando, se repite cada 6 h.
  - Llega otro cuando la falla se resuelve.
  - Cada lunes a las 08:00 llega un resumen. Si el lunes no llega, algo está mal.
- **Monitor externo:** `.github/workflows/monitor-produccion.yml`.
  - Corre cada 10 min en GitHub, fuera del NAS.
  - Revisa que el sitio responda y lee `/files/salud-….json`, cuya URL está en el secreto `SALUD_URL`.
  - Si encuentra una falla nueva, GitHub manda «Run failed» por correo a quien modificó ese archivo por última vez.

## Comandos (en el NAS, `ssh erpnext-yelke`)

```bash
docker exec cimix-yelke-respaldo-1 bash /opt/respaldo/respaldo.sh estado
docker exec cimix-yelke-respaldo-1 bash /opt/respaldo/respaldo.sh completo      # uno ahora
docker exec cimix-yelke-respaldo-1 bash /opt/respaldo/respaldo.sh correo-prueba
docker logs --tail 50 cimix-yelke-respaldo-1
```

## Restaurar

**Completo (lo normal), en el mismo NAS o en otro servidor con la misma versión:**

```bash
D=/share/ZFS19_DATA/TEOCUITATL/Backups/erpnext-yelke/diario/AAAA-MM-DD
docker cp $D cimix-yelke-backend-1:/tmp/r
docker exec -it cimix-yelke-backend-1 bash -lc 'cd ~/frappe-bench && bench --site erp.yelke.com.mx restore \
  /tmp/r/*-database.sql.gz --with-public-files /tmp/r/*-files.tar --with-private-files /tmp/r/*-private-files.tar \
  --db-root-password "$MYSQL_ROOT_PASSWORD"'
```

En un servidor nuevo, copia también el `encryption_key` de `*-site_config_backup.json` al `site_config.json`. Sin él, las contraseñas guardadas (correo, etc.) no se pueden leer.

**A un punto en el tiempo (después del último respaldo):**

1. Restaura el último `bd/*.sql.gz`, o la base del último diario.
2. Aplica los binlogs desde la posición que anota el volcado. Está en una línea como `-- CHANGE MASTER TO MASTER_LOG_FILE='mysql-bin.000123', MASTER_LOG_POS=456`.

```bash
mysqlbinlog --start-position=456 binlog/mysql-bin.000123 binlog/mysql-bin.000124 ... \
  --stop-datetime="AAAA-MM-DD HH:MM:SS" | mysql -uroot -p <base>
```
