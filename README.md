# Costeo Yelke

Aplicacion custom para ERPNext orientada al costeo de productos y automatizacion del flujo comercial y de manufactura.

## Alcance

La app gira alrededor del doctype `Costeo` y sus tablas hijas:

- `Costeo Producto`
- `Costeo Producto Detalle`
- `Etapas Costeo`

Con estas estructuras se calcula costo unitario, precio de venta y margen, y se conserva el detalle tecnico por producto terminado.

## Automatizaciones incluidas

Desde `Costeo` se automatiza la creacion de documentos de ERPNext:

- `BOM`
- `Subcontracting BOM`
- `Quotation`
- `Sales Order`
- `Production Plan`
- Flujos posteriores de manufactura y compras asociados al plan

Tambien incluye vista tipo tree y modal de detalle para capturar costos de envio, etapas y componentes por producto.

## Requisitos

- Frappe 15
- ERPNext 15

## Instalacion

```bash
cd $PATH_TO_BENCH
bench get-app https://github.com/Tegra-Soluciones/costeo-yelke.git --branch main
bench --site <tu_sitio> install-app costeo_yelke
bench --site <tu_sitio> migrate
bench build --app costeo_yelke
bench --site <tu_sitio> clear-cache
bench restart
```

## Actualizacion

```bash
cd $PATH_TO_BENCH/apps/costeo_yelke
git checkout main
git pull
cd $PATH_TO_BENCH
bench --site <tu_sitio> migrate
bench build --app costeo_yelke
bench --site <tu_sitio> clear-cache
bench restart
```

## Desarrollo

Esta app usa `pre-commit` para validaciones de formato y lint:

```bash
cd apps/costeo_yelke
pre-commit install
```

Herramientas configuradas:

- `ruff`
- `eslint`
- `prettier`
- `pyupgrade`

## Frontend de Costeo

La logica cliente de `Costeo` esta modularizada en:

- `costeo_yelke/costeo_yelke/doctype/costeo/modules/`

Para regenerar el `costeo.js` final:

```bash
./costeo_yelke/costeo_yelke/doctype/costeo/build_costeo_js.sh
```

Documentacion tecnica adicional:

- `costeo_yelke/costeo_yelke/doctype/costeo/README.md`
- `docs/costeo_yelke_app_architecture.md`

## Licencia

MIT
