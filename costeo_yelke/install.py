import frappe


DEFAULT_RAW_MATERIALS_WAREHOUSE = "Materia Prima"


def after_install():
	ensure_default_warehouses()


def after_migrate():
	ensure_default_warehouses()


def ensure_default_warehouses():
	"""Create app-required warehouses in an idempotent way for every company."""
	for company in frappe.get_all("Company", pluck="name"):
		_ensure_company_warehouse(company, DEFAULT_RAW_MATERIALS_WAREHOUSE)


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
