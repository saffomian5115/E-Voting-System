/**
 * login.js — Updated Login Logic
 * CNIC + Fingerprint only — no email/password
 */

const API = "http://localhost:5000/api";

// ── On page load ──────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  checkExistingSession();

  FingerprintScanner.init("fp-container");

  // FP status badge + auto-login on successful scan
  document.addEventListener("fp:statusChange", async (e) => {
    const badge  = document.getElementById("fp-status-badge");
    const hidden = document.getElementById("fp-template-output");

    if (e.detail.status === "verified" && e.detail.template) {
      hidden.value      = e.detail.template;
      badge.textContent = "✓ Fingerprint Ready";
      badge.className   = "ready";

      // Auto-trigger login if CNIC is filled
      const cnic = document.getElementById("cnic").value.trim();
      if (cnic && /^\d{5}-\d{7}-\d$/.test(cnic)) {
        document.getElementById("auto-login-indicator").classList.add("show");
        await loginUser();
        document.getElementById("auto-login-indicator").classList.remove("show");
      }
    } else if (e.detail.status === "failed" || e.detail.status === "error") {
      hidden.value      = "";
      badge.textContent = "✗ Scan failed — try again";
      badge.className   = "failed";
    } else {
      hidden.value      = "";
      badge.textContent = "Not scanned";
      badge.className   = "";
    }
  });

  // CNIC auto-format
  document.getElementById("cnic").addEventListener("input", formatCNIC);
});


// ── CNIC formatter ────────────────────────────────────────────────────────────
function formatCNIC(e) {
  let v   = e.target.value.replace(/\D/g, "");
  let out = "";
  if (v.length > 0)  out  = v.slice(0, 5);
  if (v.length > 5)  out += "-" + v.slice(5, 12);
  if (v.length > 12) out += "-" + v.slice(12, 13);
  e.target.value = out;
}


// ── Session check ─────────────────────────────────────────────────────────────
async function checkExistingSession() {
  try {
    const res  = await fetch(`${API}/me`, { credentials: "include" });
    const data = await res.json();
    if (data.logged_in) {
      window.location.href = "vote.html";
    }
  } catch(e) { /* Backend down — stay on login page */ }
}


// ── Field validation ──────────────────────────────────────────────────────────
function setError(fieldId, msg) {
  const fg  = document.getElementById(`fg-${fieldId}`);
  const err = document.getElementById(`err-${fieldId}`);
  if (!fg || !err) return;
  fg.classList.add("has-error");
  err.textContent = msg;
}

function clearAllErrors() {
  ["cnic"].forEach((id) => {
    const fg  = document.getElementById(`fg-${id}`);
    const err = document.getElementById(`err-${id}`);
    if (fg)  fg.classList.remove("has-error");
    if (err) err.textContent = "";
  });
}

function validateForm() {
  clearAllErrors();
  const CNIC_RE = /^\d{5}-\d{7}-\d{1}$/;
  const cnic    = document.getElementById("cnic").value.trim();

  if (!CNIC_RE.test(cnic)) {
    setError("cnic", "Format: 12345-1234567-1");
    return false;
  }
  return true;
}


// ── Main login function ───────────────────────────────────────────────────────
async function loginUser() {
  if (!validateForm()) {
    showToast("Please enter a valid CNIC", "err");
    return;
  }

  const fpTemplate = document.getElementById("fp-template-output").value;
  if (!fpTemplate) {
    showToast("Please scan your fingerprint first", "err");
    return;
  }

  const btn = document.getElementById("btn-login");
  btn.disabled = true;
  btn.classList.add("loading");

  try {
    const payload = {
      cnic       : document.getElementById("cnic").value.trim(),
      fp_template: fpTemplate,
    };

    const res  = await fetch(`${API}/login`, {
      method     : "POST",
      credentials: "include",
      headers    : { "Content-Type": "application/json" },
      body       : JSON.stringify(payload),
    });

    const data = await res.json();

    if (data.success) {
      showToast(`✓ ${data.message}`, "ok");
      setTimeout(() => {
        window.location.href = data.voter?.hasVoted ? "result.html" : "vote.html";
      }, 1200);
    } else {
      showToast(data.error || "Login failed", "err");
      FingerprintScanner.reset();
      document.getElementById("fp-template-output").value = "";
      const badge = document.getElementById("fp-status-badge");
      badge.textContent = "Not scanned";
      badge.className   = "";
    }
  } catch(err) {
    showToast("Cannot connect to server — is backend running?", "err");
    console.error("[LOGIN]", err);
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
  }
}


// ── Toast ─────────────────────────────────────────────────────────────────────
let _toastTimer = null;
function showToast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className   = `show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}