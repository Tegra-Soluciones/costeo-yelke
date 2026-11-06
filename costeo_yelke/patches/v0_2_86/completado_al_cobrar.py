"""«Completado» ahora significa cobrado (api/cierre_proyecto.py): los costeos que se
marcaron al facturar se recalculan; los que aún deben regresan a Entregado/En Producción."""
from costeo_yelke.api.cierre_proyecto import revisar_todos


def execute():
    revisar_todos()
