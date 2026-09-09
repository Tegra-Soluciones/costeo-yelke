"""Corrida única: pasa a MAYÚSCULAS los datos maestros ya cargados.

De aquí en adelante lo hace el hook (before_insert/before_validate). La lógica
vive en costeo_yelke.overrides.uppercase_master para no duplicarla.
"""

from costeo_yelke.overrides.uppercase_master import homologar_existentes


def execute():
    homologar_existentes()
