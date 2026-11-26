const TOKEN_KEY = "hb_token";
let token = sessionStorage.getItem(TOKEN_KEY) || "";
let me = null;
let branches = [];
const products = new Map();

const $ = (id) => document.getElementById(id);

function showMsg(text) {
  const el = $("msg");
  el.textContent = text;
  el.classList.toggle("hidden", !text);
}

function showView(name) {
  $("login-view").classList.toggle("hidden", name !== "login");
  $("common-view").classList.toggle("hidden", name !== "common");
  $("admin-view").classList.toggle("hidden", name !== "admin");
  $("user-bar").classList.toggle("hidden", name === "login");
}

async function api(url, opts = {}) {
  const headers = new Headers(opts.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(url, { ...opts, headers });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token && !url.startsWith("/auth/login")) logout();
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Error ${res.status}`);
  }
  return data;
}

function logout(message = "") {
  token = "";
  me = null;
  sessionStorage.removeItem(TOKEN_KEY);
  $("stock-result").textContent = "";
  showView("login");
  showMsg(message);
}

function fillBranches(selectEl, selectedId = null) {
  selectEl.replaceChildren();
  for (const b of branches) {
    const opt = document.createElement("option");
    opt.value = String(b.branch_id);
    opt.textContent = `${b.name} (${b.location})`;
    if (selectedId === b.branch_id) opt.selected = true;
    selectEl.appendChild(opt);
  }
}

async function loadProducts(q = "") {
  const qs = new URLSearchParams({ limit: "100" });
  if (q.trim()) qs.set("q", q.trim());
  const data = await api(`/products?${qs}`);
  const sel = $("product-select");
  sel.replaceChildren();
  for (const p of data.results || []) {
    products.set(p.id, p);
    const opt = document.createElement("option");
    opt.value = String(p.id);
    opt.textContent = `#${p.id} | ${p.sku} - ${p.name} ($${p.unit_price})`;
    sel.appendChild(opt);
  }
}

async function loadStock() {
  const rows = await api("/stock?in_stock_only=true");
  const tbody = $("stock-body");
  tbody.replaceChildren();
  for (const row of rows) {
    let p = products.get(row.product_id);
    if (!p) {
      p = await api(`/products/${row.product_id}`).catch(() => null);
      if (p) products.set(p.id, p);
    }
    const tr = document.createElement("tr");
    for (const val of [row.product_id, p?.sku || "-", p?.name || `#${row.product_id}`, row.quantity]) {
      const td = document.createElement("td");
      td.textContent = String(val);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function loadUsers() {
  const users = await api("/users");
  const tbody = $("users-body");
  tbody.replaceChildren();
  for (const u of users) {
    const tr = document.createElement("tr");
    const branch = branches.find((b) => b.branch_id === u.branch_id);
    for (const val of [u.user_id, u.username, branch ? branch.name : "-", u.status]) {
      const td = document.createElement("td");
      td.textContent = String(val);
      tr.appendChild(td);
    }
    const actTd = document.createElement("td");
    if (me && u.user_id === me.user_id) {
      actTd.textContent = "Admin";
    } else {
      const wrap = document.createElement("div");
      wrap.className = "row";

      const bSel = document.createElement("select");
      fillBranches(bSel, u.branch_id);
      const bBtn = document.createElement("button");
      bBtn.type = "button";
      bBtn.textContent = "Cambiar sucursal";
      bBtn.onclick = async () => {
        try {
          await api(`/users/${u.user_id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ branch_id: Number(bSel.value) }),
          });
          showMsg(`Sucursal actualizada para ${u.username}`);
          await loadUsers();
        } catch (e) { showMsg(e.message); }
      };

      const pIn = document.createElement("input");
      pIn.type = "password";
      pIn.placeholder = "Nueva clave";
      pIn.size = 10;
      const pBtn = document.createElement("button");
      pBtn.type = "button";
      pBtn.textContent = "Cambiar clave";
      pBtn.onclick = async () => {
        try {
          await api(`/users/${u.user_id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: pIn.value }),
          });
          pIn.value = "";
          showMsg(`Contrasena actualizada para ${u.username}`);
        } catch (e) { showMsg(e.message); }
      };

      const dBtn = document.createElement("button");
      dBtn.type = "button";
      dBtn.textContent = "Eliminar";
      dBtn.disabled = u.status === "deleted";
      dBtn.onclick = async () => {
        try {
          await api(`/users/${u.user_id}`, { method: "DELETE" });
          showMsg(`Usuario ${u.username} eliminado (soft-delete)`);
          await loadUsers();
        } catch (e) { showMsg(e.message); }
      };

      wrap.append(bSel, bBtn, pIn, pBtn, dBtn);
      actTd.appendChild(wrap);
    }
    tr.appendChild(actTd);
    tbody.appendChild(tr);
  }
}

async function initSession() {
  if (!token) return showView("login");
  try {
    me = await api("/auth/me");
    const bText = me.branch ? ` | Sucursal: ${me.branch.name} (${me.branch.location})` : "";
    $("user-info").textContent = `${me.username} (${me.role_name})${bText}`;
    if (me.role_name === "admin") {
      showView("admin");
      branches = await api("/branches");
      fillBranches($("new-branch"));
      await loadUsers();
    } else {
      showView("common");
      $("branch-title").textContent = me.branch
        ? `Sucursal asignada: #${me.branch.branch_id} ${me.branch.name} (${me.branch.location})`
        : `Sucursal #${me.branch_id}`;
      await loadProducts().catch((e) => showMsg(e.message));
      await loadStock();
    }
  } catch (e) {
    logout(e.message);
  }
}

$("login-form").onsubmit = async (e) => {
  e.preventDefault();
  showMsg("");
  try {
    const body = new URLSearchParams({
      username: $("login-user").value.trim(),
      password: $("login-pass").value,
    });
    const res = await api("/auth/login", { method: "POST", body });
    token = res.access_token;
    sessionStorage.setItem(TOKEN_KEY, token);
    await initSession();
  } catch (err) { showMsg(err.message); }
};

$("logout-btn").onclick = () => logout();
$("product-select").onchange = () => { $("stock-result").textContent = ""; };

$("search-form").onsubmit = async (e) => {
  e.preventDefault();
  showMsg("");
  try { await loadProducts($("search-q").value); } catch (err) { showMsg(err.message); }
};

$("check-btn").onclick = async () => {
  showMsg("");
  const pid = Number($("product-select").value);
  if (!pid) return;
  try {
    const s = await api(`/stock/${pid}`);
    $("stock-result").textContent = `Disponible: ${s.quantity} unidades`;
  } catch (err) {
    $("stock-result").textContent = err.message === "Stock item not found" ? "Disponible: 0 unidades" : err.message;
  }
};

$("stock-form").onsubmit = async (e) => {
  e.preventDefault();
  showMsg("");
  try {
    const s = await api("/stock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: Number($("product-select").value),
        quantity: Number($("stock-qty").value),
        operation: $("stock-op").value,
      }),
    });
    $("stock-result").textContent = `Disponible: ${s.quantity} unidades`;
    showMsg(`Stock actualizado: ${s.quantity} unidades`);
    await loadStock();
  } catch (err) { showMsg(err.message); }
};

$("create-user-form").onsubmit = async (e) => {
  e.preventDefault();
  showMsg("");
  try {
    const u = await api("/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("new-user").value.trim(),
        password: $("new-pass").value,
        branch_id: Number($("new-branch").value),
      }),
    });
    e.target.reset();
    showMsg(`Usuario ${u.username} creado`);
    await loadUsers();
  } catch (err) { showMsg(err.message); }
};

initSession();
