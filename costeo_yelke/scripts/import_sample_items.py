"""
Import sample items for Costeo Yelke testing.
Run with: bench --site sandbox.local execute costeo_yelke.scripts.import_sample_items.run
"""
import frappe


REQUIRED_UOMS = [
    "MTR - Metro",
    "H87 - Pieza",
    "E48 - Unidad de servicio",
    "Rollo de 10 mts",
    "Rollo de 100 mts",
]

SAT_KEYS = [
    {"name": "11162100", "key": "11162100", "description": "Tejidos de encaje y artículos confeccionados de encaje", "key_name": "Tejidos de encaje"},
    {"name": "73141715", "key": "73141715", "description": "Servicios de bordado o estampado textil", "key_name": "Servicios de bordado"},
    {"name": "53101800", "key": "53101800", "description": "Accesorios de vestuario", "key_name": "Accesorios de vestuario"},
]

ITEMS = [
    {
        "item_code": "MAT-AVI-CIE-001",
        "item_name": "CIERRE NYLON DELCAST FRONTAL 70CM",
        "item_group": "Materia prima",
        "stock_uom": "MTR - Metro",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>CIERRE NYLON DELCAST FRONTAL 70CM</p>",
        "sat_key": "11162100",
        "warehouse_type": "wip",
        "price_list": "Compra estandar",
    },
    {
        "item_code": "MAT-AVI-REF",
        "item_name": 'CINTA REFLEJANTE DE 1" GRIS',
        "item_group": "Materia prima",
        "stock_uom": "MTR - Metro",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": '<p>CINTA REFLEJANTE DE 1" GRIS</p>',
        "sat_key": "11162100",
        "warehouse_type": "wip",
        "price_list": "Compra estandar",
    },
    {
        "item_code": "MAT-TEL-POL",
        "item_name": "FORRO POLAR",
        "item_group": "Materia prima",
        "stock_uom": "MTR - Metro",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>FORRO POLAR</p>",
        "sat_key": "11162100",
        "warehouse_type": "wip",
        "price_list": "Compra estandar",
        "uom_conversions": [
            {"uom": "Rollo de 10 mts", "conversion_factor": 10.0},
            {"uom": "Rollo de 100 mts", "conversion_factor": 100.0},
        ],
    },
    {
        "item_code": "MAT-TEL-TIM",
        "item_name": "TELA TIMBERLAND",
        "item_group": "Materia prima",
        "stock_uom": "MTR - Metro",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "TELA TIMBERLAND",
        "sat_key": "11162100",
        "warehouse_type": "wip",
        "price_list": "Compra estandar",
        "uom_conversions": [
            {"uom": "Rollo de 10 mts", "conversion_factor": 10.0},
            {"uom": "Rollo de 100 mts", "conversion_factor": 100.0},
        ],
    },
    {
        "item_code": "SRV-BORD",
        "item_name": "SERVICIO DE BORDADO",
        "item_group": "Servicios",
        "stock_uom": "E48 - Unidad de servicio",
        "is_stock_item": 0,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>SERVICIO DE BORDADO</p>",
        "sat_key": "73141715",
        "warehouse_type": "branch",
        "price_list": "Compra estandar",
    },
    {
        "item_code": "SRV-ESTM",
        "item_name": "SERVICIO DE ESTAMPADO",
        "item_group": "Servicios",
        "stock_uom": "E48 - Unidad de servicio",
        "is_stock_item": 0,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>SERVICIO DE ESTAMPADO</p>",
        "sat_key": "73141715",
        "warehouse_type": "branch",
        "price_list": "Compra estandar",
    },
    {
        "item_code": "SRV-CONF",
        "item_name": "SERVICIO DE CONFECCIÓN Y CORTE",
        "item_group": "Servicios",
        "stock_uom": "E48 - Unidad de servicio",
        "is_stock_item": 0,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "SERVICIO DE CONFECCIÓN Y CORTE",
        "sat_key": "73141715",
        "warehouse_type": "branch",
        "price_list": "Compra estandar",
    },
    {
        "item_code": "SEM-TIM-BOR-3",
        "item_name": "CHAMARRA TIMBERLAND BORDADA",
        "item_group": "Sub-Ensamblajes",
        "stock_uom": "H87 - Pieza",
        "brand": "Yelke",
        "is_stock_item": 1,
        "is_purchase_item": 0,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>CHAMARRA TIMBERLAND BORDADA</p>",
        "sat_key": "53101800",
        "warehouse_type": "wip",
    },
    {
        "item_code": "SEM-TIM-DTF-2",
        "item_name": "CHAMARRA TIMBERLAND CON DTF",
        "item_group": "Sub-Ensamblajes",
        "stock_uom": "H87 - Pieza",
        "brand": "Yelke",
        "is_stock_item": 1,
        "is_purchase_item": 0,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>CHAMARRA TIMBERLAND CON DTF</p>",
        "sat_key": "53101800",
        "warehouse_type": "wip",
    },
    {
        "item_code": "SEM-TIM-CON-1",
        "item_name": "CHAMARRA TIMBERLAND CONFECCIONADA",
        "item_group": "Sub-Ensamblajes",
        "stock_uom": "H87 - Pieza",
        "brand": "Yelke",
        "is_stock_item": 1,
        "is_purchase_item": 0,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 1,
        "description": "<p>CHAMARRA TIMBERLAND CONFECCIONADA</p>",
        "sat_key": "53101800",
        "warehouse_type": "wip",
    },
    {
        "item_code": "YLK-CHA-TIM",
        "item_name": "CHAMARRA TIMBERLAND YELKE",
        "item_group": "Productos Terminados",
        "stock_uom": "H87 - Pieza",
        "brand": "Yelke",
        "is_stock_item": 1,
        "is_purchase_item": 0,
        "is_sales_item": 1,
        "include_item_in_manufacturing": 1,
        "description": "CHAMARRA TIMBERLAND YELKE",
        "sat_key": "53101800",
        "warehouse_type": "finished",
        "price_list": "Venta estándar",
        "warranty_period": 30,
    },
]


def run():
    company = frappe.db.get_default("company") or (frappe.get_all("Company", pluck="name", limit=1) or [""])[0]
    if not company:
        print("ERROR: No company found in the system.")
        return

    warehouses = frappe.get_all("Warehouse", fields=["name"], filters={"is_group": 0, "disabled": 0, "company": company})
    wh_map = {}
    for w in warehouses:
        n = w["name"].lower()
        if "proceso" in n or "proceso" in n:
            wh_map["wip"] = w["name"]
        elif "terminad" in n or "finished" in n:
            wh_map["finished"] = w["name"]
        elif "sucursal" in n or "branch" in n:
            wh_map["branch"] = w["name"]
        elif "tránsito" in n or "transito" in n or "transit" in n:
            wh_map["transit"] = w["name"]

    # Fallback: use any warehouse
    any_wh = warehouses[0]["name"] if warehouses else None
    for k in ["wip", "finished", "branch", "transit"]:
        if k not in wh_map and any_wh:
            wh_map[k] = any_wh

    print(f"Using company: {company}")
    print(f"Warehouse map: {wh_map}")

    # 1. Create required UOMs
    for uom_name in REQUIRED_UOMS:
        if not frappe.db.exists("UOM", uom_name):
            uom = frappe.new_doc("UOM")
            uom.uom_name = uom_name
            uom.flags.ignore_permissions = True
            uom.insert()
            print(f"  Created UOM: {uom_name}")
        else:
            print(f"  UOM exists: {uom_name}")

    # 2. Create SAT keys (for Mexico Compliance)
    for sat in SAT_KEYS:
        if not frappe.db.exists("SAT Product or Service Key", sat["name"]):
            doc = frappe.new_doc("SAT Product or Service Key")
            doc.key = sat["key"]
            doc.description = sat["description"]
            doc.key_name = sat["key_name"]
            doc.enabled = 1
            doc.flags.ignore_permissions = True
            doc.insert()
            print(f"  Created SAT key: {sat['name']}")
        else:
            print(f"  SAT key exists: {sat['name']}")

    frappe.db.commit()

    # 3. Create items
    created = 0
    skipped = 0
    for item_data in ITEMS:
        if frappe.db.exists("Item", item_data["item_code"]):
            print(f"  Item {item_data['item_code']} exists, skipping")
            skipped += 1
            continue

        doc = frappe.new_doc("Item")
        doc.item_code = item_data["item_code"]
        doc.item_name = item_data["item_name"]
        doc.item_group = item_data["item_group"]
        doc.stock_uom = item_data["stock_uom"]
        doc.is_stock_item = item_data.get("is_stock_item", 1)
        doc.is_purchase_item = item_data.get("is_purchase_item", 1)
        doc.is_sales_item = item_data.get("is_sales_item", 0)
        doc.include_item_in_manufacturing = item_data.get("include_item_in_manufacturing", 0)
        doc.description = item_data.get("description", "")
        doc.country_of_origin = "Mexico"

        if item_data.get("brand"):
            doc.brand = item_data["brand"]

        if item_data.get("warranty_period"):
            doc.warranty_period = item_data["warranty_period"]

        # SAT key (requires Mexico Compliance)
        sat_key = item_data.get("sat_key")
        if sat_key and frappe.db.exists("SAT Product or Service Key", sat_key):
            doc.mx_product_service_key = sat_key

        # Item defaults
        wh_type = item_data.get("warehouse_type", "wip")
        warehouse = wh_map.get(wh_type, any_wh)
        price_list = item_data.get("price_list", "")

        doc.append("item_defaults", {
            "company": company,
            "default_warehouse": warehouse,
            "default_price_list": price_list if frappe.db.exists("Price List", price_list) else "",
        })

        # UOM conversions
        for conv in item_data.get("uom_conversions", []):
            if frappe.db.exists("UOM", conv["uom"]):
                doc.append("uoms", {
                    "uom": conv["uom"],
                    "conversion_factor": conv["conversion_factor"],
                })

        doc.flags.ignore_permissions = True
        try:
            doc.insert()
            frappe.db.commit()
            created += 1
            print(f"  Created item: {item_data['item_code']} — {item_data['item_name']}")
        except Exception as e:
            frappe.db.rollback()
            print(f"  ERROR creating {item_data['item_code']}: {e}")

    print(f"\nDone! Created: {created}, Skipped: {skipped}")
