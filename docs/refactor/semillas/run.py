import sys, frappe
sys.path.insert(0, "/private/tmp/claude-502/-Users-trabajo-Documents-frappe-bench-v15-apps-costeo-yelke/455962b2-ce0b-409b-b631-99f79fded5f9/scratchpad")
frappe.init(site="sandbox.local", sites_path="/Users/trabajo/Trabajo/frappe-bench-v15/sites"); frappe.connect(); frappe.set_user("Administrator")
import e2e
try:
    getattr(e2e, "fase_" + sys.argv[1])(*sys.argv[2:])
except Exception:
    frappe.db.rollback(); import traceback; traceback.print_exc()
