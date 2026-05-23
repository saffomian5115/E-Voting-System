/**
 * admin.js — Shared Admin Panel Utilities
 * Sab admin pages is file ko load karti hain
 */

const API = "http://localhost:5000/api";

const SYMBOL_MAP = {
  bat:"🏏", arrow:"🏹", book:"📚", lion:"🦁", tiger:"🐯",
  star:"⭐", flag:"🚩", torch:"🔦", key:"🗝️",  scale:"⚖️",
  tractor:"🚜", wheel:"☸️", flower:"🌸", moon:"🌙",
};

// ══════════════════════════════════════════════════════════════════════════════
// SECTION 1 — Auth
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Admin session verify karo.
 * Agar session nahi mila to login overlay dikhao.
 * @param {Function} onSuccess - session valid hone pe callback
 */
async function requireAdmin(onSuccess) {
  try {
    const res = await fetch(`${API}/admin/me`, { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (data.logged_in) {
        // Login overlay chupao agar exist karta hai
        const overlay = document.getElementById("login-overlay");
        if (overlay) overlay.style.display = "none";

        // Admin name badge update
        const badge = document.getElementById("admin-name");
        if (badge) badge.textContent = data.username;

        if (onSuccess) onSuccess(data.username);
        return true;
      }
    }
  } catch (e) { /* session nahi mila */ }

  // Session nahi — login overlay dikhao ya redirect karo
  const overlay = document.getElementById("login-overlay");
  if (overlay) {
    overlay.style.display = "flex";
  } else {
    window.location.href = "index.html";
  }
  return false;
}

/**
 * Admin login request
 */
async function adminLogin() {
  const userEl = document.getElementById("adm-user");
  const passEl = document.getElementById("adm-pass");
  const errEl  = document.getElementById("login-err");

  if (!userEl || !passEl) return;
  errEl.style.display = "none";

  const username = userEl.value.trim();
  const password = passEl.value;

  if (!username || !password) {
    errEl.textContent   = "Username aur password dono chahiye";
    errEl.style.display = "block";
    return;
  }

  try {
    const res  = await fetch(`${API}/admin/login`, {
      method     : "POST",
      credentials: "include",
      headers    : { "Content-Type": "application/json" },
      body       : JSON.stringify({ username, password }),
    });
    const data = await res.json();

    if (data.success) {
      const overlay = document.getElementById("login-overlay");
      if (overlay) overlay.style.display = "none";
      const badge = document.getElementById("admin-name");
      if (badge) badge.textContent = data.username;
      if (typeof onAdminReady === "function") onAdminReady(data.username);
    } else {
      errEl.textContent   = data.error || "Login fail ho gaya";
      errEl.style.display = "block";
    }
  } catch (e) {
    errEl.textContent   = "Server se connection nahi";
    errEl.style.display = "block";
  }
}

/**
 * Admin logout
 */
async function adminLogout() {
  try {
    await fetch(`${API}/admin/logout`, { credentials: "include" });
  } catch (e) { /* ignore */ }
  window.location.href = "index.html";
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 2 — Toast
// ══════════════════════════════════════════════════════════════════════════════

let _toastTimer = null;

function showToast(msg, type = "ok") {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className   = `show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3800);
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 3 — Formatting Helpers
// ══════════════════════════════════════════════════════════════════════════════

function fmtDate(iso) {
  if (!iso) return "--";
  return new Date(iso).toLocaleString("en-PK", { dateStyle: "medium", timeStyle: "short" });
}

function fmtDateInput(iso) {
  // datetime-local input ke liye: "YYYY-MM-DDTHH:MM"
  if (!iso) return "";
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function symbolEmoji(sym) {
  return SYMBOL_MAP[sym?.toLowerCase()] || "🗳️";
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? "--";
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 4 — Login Overlay HTML injector (optional convenience)
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Agar page mein #login-overlay nahi hai, inject karo
 */
function injectLoginOverlay() {
  if (document.getElementById("login-overlay")) return;
  const div = document.createElement("div");
  div.id = "login-overlay";
  div.style.cssText = "position:fixed;inset:0;background:var(--bg,#04090f);z-index:999;display:flex;align-items:center;justify-content:center;";
  div.innerHTML = `
    <div style="background:#080f1c;border:1px solid rgba(0,234,255,.15);border-radius:16px;padding:2.5rem;width:100%;max-width:360px">
      <p style="font-family:'Orbitron',sans-serif;font-size:.9rem;color:#00eaff;letter-spacing:.18em;text-transform:uppercase;margin-bottom:.3rem">Admin Login</p>
      <p style="font-size:.72rem;color:rgba(255,255,255,.4);margin-bottom:2rem">E-Voting System Control Panel</p>
      <div style="margin-bottom:1rem">
        <label style="display:block;font-size:.68rem;color:rgba(0,234,255,.7);letter-spacing:.1em;text-transform:uppercase;margin-bottom:.4rem">Username</label>
        <input id="adm-user" type="text" placeholder="admin" autocomplete="username"
          style="width:100%;background:#0c1525;border:1px solid rgba(0,234,255,.12);border-radius:6px;color:rgba(255,255,255,.88);font-family:'Share Tech Mono',monospace;font-size:.85rem;padding:.6rem .9rem;outline:none">
      </div>
      <div style="margin-bottom:1rem">
        <label style="display:block;font-size:.68rem;color:rgba(0,234,255,.7);letter-spacing:.1em;text-transform:uppercase;margin-bottom:.4rem">Password</label>
        <input id="adm-pass" type="password" placeholder="••••••••" autocomplete="current-password"
          onkeydown="if(event.key==='Enter')adminLogin()"
          style="width:100%;background:#0c1525;border:1px solid rgba(0,234,255,.12);border-radius:6px;color:rgba(255,255,255,.88);font-family:'Share Tech Mono',monospace;font-size:.85rem;padding:.6rem .9rem;outline:none">
      </div>
      <div id="login-err" style="color:#ff4466;font-size:.72rem;margin-bottom:.8rem;display:none"></div>
      <button onclick="adminLogin()"
        style="width:100%;padding:.8rem;border-radius:7px;border:1.5px solid #00eaff;background:rgba(0,234,255,.1);color:#00eaff;font-family:'Orbitron',sans-serif;font-size:.78rem;letter-spacing:.15em;text-transform:uppercase;cursor:pointer">
        Login Karo
      </button>
    </div>
  `;
  document.body.prepend(div);
}

// Global expose
window.requireAdmin  = requireAdmin;
window.adminLogin    = adminLogin;
window.adminLogout   = adminLogout;
window.showToast     = showToast;
window.fmtDate       = fmtDate;
window.fmtDateInput  = fmtDateInput;
window.symbolEmoji   = symbolEmoji;
window.setText       = setText;
window.injectLoginOverlay = injectLoginOverlay;
window.API           = API;
window.SYMBOL_MAP    = SYMBOL_MAP;