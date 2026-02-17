### Costeo Yelke

Motor de costeo y BOMs

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app costeo_yelke
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/costeo_yelke
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### Costeo Frontend

The client logic for the `Costeo` doctype is modularized in:

- `costeo_yelke/costeo_yelke/doctype/costeo/modules/`

Generate the final doctype script with:

```bash
./costeo_yelke/costeo_yelke/doctype/costeo/build_costeo_js.sh
```

Additional architecture notes:

- `costeo_yelke/costeo_yelke/doctype/costeo/README.md`
- `docs/costeo_yelke_app_architecture.md`

### License

mit
