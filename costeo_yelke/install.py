import frappe


DEFAULT_RAW_MATERIALS_WAREHOUSE = "Materia Prima"


def after_install():
	ensure_default_warehouses()


def after_migrate():
	ensure_default_warehouses()


def ensure_default_warehouses():
	"""Create app-required warehouses in an idempotent way for every company.

	Corre como hook after_migrate, así que NO puede tronar: si falla con una
	compañía, aborta el resto del bucle de hooks del migrate (y con él, el de las
	apps que vengan después). Cualquier problema con una compañía se registra y se
	sigue con las demás.
	"""
	for company in frappe.get_all("Company", pluck="name"):
		try:
			_ensure_company_warehouse(company, DEFAULT_RAW_MATERIALS_WAREHOUSE)
		except Exception:
			frappe.log_error(
				title="costeo_yelke: no se pudo asegurar el almacén de materia prima",
				message=f"Compañía: {company}\n\n{frappe.get_traceback()}",
			)


def _ensure_company_warehouse(company, warehouse_name):
	if not company or not warehouse_name:
		return None

	existing_warehouse = frappe.db.get_value(
		"Warehouse",
		{"company": company, "warehouse_name": warehouse_name},
		"name",
	)
	if existing_warehouse:
		return existing_warehouse

	# El NOMBRE del documento es "<warehouse_name> - <abbr>". Puede existir ya aunque
	# la búsqueda de arriba no lo encuentre: su campo warehouse_name pudo quedar
	# distinto (renombrado a mano), o dos compañías comparten abreviatura. Insertarlo
	# a ciegas revienta con Duplicate entry y tumba el hook del migrate.
	abbr = frappe.get_cached_value("Company", company, "abbr")
	nombre_documento = f"{warehouse_name} - {abbr}" if abbr else warehouse_name
	if frappe.db.exists("Warehouse", nombre_documento):
		dueño = frappe.db.get_value("Warehouse", nombre_documento, "company")
		if dueño == company:
			return nombre_documento
		# Es de OTRA compañía (abreviaturas repetidas): no se puede crear uno con ese
		# mismo nombre ni se debe reutilizar el ajeno -- se avisa y se deja que el
		# usuario elija el almacén a mano en el Costeo.
		frappe.log_error(
			title="costeo_yelke: abreviatura de compañía duplicada",
			message=(
				f"No se pudo crear '{warehouse_name}' para {company}: el almacén "
				f"'{nombre_documento}' ya existe y pertenece a {dueño}. Revisa que las "
				"compañías no compartan la misma abreviatura."
			),
		)
		return None

	parent_warehouse = _get_company_root_warehouse(company)

	warehouse = frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": warehouse_name,
			"company": company,
			"is_group": 0,
			"parent_warehouse": parent_warehouse,
		}
	)
	warehouse.insert(ignore_permissions=True)
	return warehouse.name


def _get_company_root_warehouse(company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	if abbr:
		root_name = f"All Warehouses - {abbr}"
		if frappe.db.exists("Warehouse", root_name):
			return root_name

	warehouses = frappe.get_all(
		"Warehouse",
		fields=["name", "parent_warehouse"],
		filters={"company": company, "is_group": 1},
		order_by="lft asc",
	)

	for warehouse in warehouses:
		if not warehouse.parent_warehouse:
			return warehouse.name

	if warehouses:
		return warehouses[0].name

	return None
