"""Re-corre la homologación a MAYÚSCULAS de los existentes.

v0_2_22 tenía un guard con `frappe.db.exists()` que, por la collation
case-insensitive de MariaDB, tomaba un cambio de sólo-mayúsculas como colisión y
saltaba el rename (afectaba Item y Brand). Ya corregido en homologar_existentes();
esta corrida idempotente termina lo que quedó pendiente.
"""

from costeo_yelke.overrides.uppercase_master import homologar_existentes


def execute():
    homologar_existentes()
