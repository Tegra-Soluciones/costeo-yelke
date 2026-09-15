const BASE = "";

// El texto real de un frappe.throw()/frappe.msgprint() no viaja en `message` (eso solo
// trae algo en respuestas EXITOSAS) ni en `exc_type` (que es apenas el nombre de la
// clase, ej. "ValidationError") -- viaja en `_server_messages`, una lista de objetos
// codificados en JSON dos veces. Sin esto, cualquier error de validación del backend le
// mostraba al usuario literalmente "ValidationError" en vez de la explicación.
function extractErrorMessage(err, fallback) {
  if (err?._server_messages) {
    try {
      const msgs = JSON.parse(err._server_messages)
        .map((m) => { try { return JSON.parse(m).message; } catch { return m; } })
        .filter(Boolean);
      if (msgs.length) return msgs.join(" ");
    } catch { /* ignore, cae al resto de los campos */ }
  }
  return err?.message || err?.exc_type || fallback;
}

async function request(method, url, body) {
  const opts = {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": getCsrfToken(),
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(err, res.statusText));
  }
  return res.json();
}

function getCsrfToken() {
  return (
    window.frappe?.csrf_token ||
    document.cookie.split("; ").find((r) => r.startsWith("csrf_token="))?.split("=")[1] ||
    "no-token"
  );
}

export const db = {
  getList(doctype, { fields = ["name"], filters = [], orderBy = "modified desc", limit = 50 } = {}) {
    const params = new URLSearchParams({
      fields: JSON.stringify(fields),
      filters: JSON.stringify(filters),
      order_by: orderBy,
      limit_page_length: limit,
    });
    return request("GET", `/api/resource/${encodeURIComponent(doctype)}?${params}`).then(
      (r) => r.data,
    );
  },

  get(doctype, name) {
    return request("GET", `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`).then(
      (r) => r.data,
    );
  },

  create(doctype, doc) {
    return request("POST", `/api/resource/${encodeURIComponent(doctype)}`, doc).then((r) => r.data);
  },

  update(doctype, name, doc) {
    return request(
      "PUT",
      `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
      doc,
    ).then((r) => r.data);
  },

  delete(doctype, name) {
    return request("DELETE", `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`);
  },
};

export function call(method, args = {}) {
  return request("POST", `/api/method/${method}`, args).then((r) => r.message);
}

export async function uploadFile(file, { doctype, docname, folder = "Home", isPrivate = 1 } = {}) {
  const form = new FormData();
  form.append("file", file, file.name);
  form.append("is_private", isPrivate ? 1 : 0);
  form.append("folder", folder);
  if (doctype) form.append("doctype", doctype);
  if (docname) form.append("docname", docname);
  const res = await fetch(BASE + "/api/method/upload_file", {
    method: "POST",
    credentials: "include",
    headers: { "X-Frappe-CSRF-Token": getCsrfToken() },
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(err, res.statusText));
  }
  return (await res.json()).message;
}

const _printFmtCache = {};
export async function defaultPrintFormat(doctype) {
  if (_printFmtCache[doctype]) return _printFmtCache[doctype];
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_default_print_format", { doctype });
    _printFmtCache[doctype] = r?.format || "Standard";
  } catch {
    return "Standard";
  }
  return _printFmtCache[doctype];
}

export function openDesk(doctype, name) {
  window.open(`/app/${slugify(doctype)}/${encodeURIComponent(name)}`, "_blank");
}

/**
 * Uses Frappe's native search_link endpoint which:
 *  - searches by name AND the doctype's title field (item_name, customer_name, etc.)
 *  - respects permissions and link filters
 *  - returns [{value, description}] where value = doc name, description = title label
 */
export async function searchLink(doctype, query, filters = []) {
  try {
    const res = await call("frappe.desk.search.search_link", {
      txt:                    query ?? "",
      doctype,
      filters:                filters.length ? JSON.stringify(filters) : "[]",
      page_length:            15,
      ignore_user_permissions: 0,
      reference_doctype:      "",
    });
    return (Array.isArray(res) ? res : []).map((r) => ({
      value:       r.value,
      description: r.description || "",
    }));
  } catch {
    return [];
  }
}

// Doctypes que tienen un campo "de vitrina" -- distinto de su nombre/ID real --
// que se debe mostrar en vez del nombre en cualquier LinkInput ya resuelto (no
// mientras se busca/edita, ahí se sigue viendo/escribiendo el nombre real). Hoy
// solo Proveedor: "Nombre Comercial" (ver patch v0_2_25) es opcional -- un
// proveedor sin ese campo capturado sigue mostrando su nombre de siempre.
const LINK_DISPLAY_FIELD = { Supplier: "nombre_comercial" };

// name real -> etiqueta de vitrina ya resuelta (o null si no aplica/no tiene). Es
// un cache a nivel de módulo (no por instancia de componente) -- todos los
// LinkInput de la página comparten el mismo, así que un proveedor que ya se
// resolvió en un campo no se vuelve a pedir en el siguiente.
const linkDisplayCache = new Map();
export async function getLinkDisplayLabel(doctype, name) {
  const field = LINK_DISPLAY_FIELD[doctype];
  if (!field || !name) return null;
  const key = `${doctype}::${name}`;
  if (linkDisplayCache.has(key)) return linkDisplayCache.get(key);
  const promise = call("frappe.client.get_value", { doctype, filters: name, fieldname: field })
    .then((r) => r?.[field] || null)
    .catch(() => null);
  linkDisplayCache.set(key, promise);
  const label = await promise;
  linkDisplayCache.set(key, label); // reemplaza la promesa por el valor ya resuelto
  return label;
}

function slugify(str) {
  return str.toLowerCase().replace(/\s+/g, "-");
}

/**
 * "%" entre palabras hace que el LIKE de Frappe (usado por search_link) encuentre
 * el nombre aunque el texto libre no tenga exactamente la misma puntuación que el
 * registro real (ej. "IMPERMEABLE GABARDINA MARS" -> "IMPERMEABLE GABARDINA - MARS").
 */
export function fuzzyQuery(text) {
  return (text || "").trim().split(/\s+/).filter(Boolean).join("%");
}
