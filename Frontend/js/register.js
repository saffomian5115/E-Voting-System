/**
 * register.js — Module 3: Registration Logic
 * Fingerprint.js ke saath milke kaam karta hai
 */

const API = "http://localhost:5000/api";

// ── On page load ──────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  FingerprintScanner.init("fp-container");

  // FP status badge update karo
  document.addEventListener("fp:statusChange", (e) => {
    const badge  = document.getElementById("fp-status-badge");
    const hidden = document.getElementById("fp-template-output");

    if (e.detail.status === "verified" && e.detail.template) {
      hidden.value       = e.detail.template;
      badge.textContent  = "✓ Fingerprint Ready";
      badge.className    = "ready";
    } else if (e.detail.status === "failed" || e.detail.status === "error") {
      hidden.value       = "";
      badge.textContent  = "✗ Scan fail — dobara try karo";
      badge.className    = "failed";
    } else {
      hidden.value       = "";
      badge.textContent  = "Scan nahi hua";
      badge.className    = "";
    }
  });

  // CNIC auto-format
  document.getElementById("cnic").addEventListener("input", formatCNIC);
});


// ── CNIC auto-formatter ───────────────────────────────────────────────────────
function formatCNIC(e) {
  let v    = e.target.value.replace(/\D/g, "");
  let out  = "";
  if (v.length > 0)  out  = v.slice(0, 5);
  if (v.length > 5)  out += "-" + v.slice(5, 12);
  if (v.length > 12) out += "-" + v.slice(12, 13);
  e.target.value = out;
}


// ── Field validation helpers ──────────────────────────────────────────────────
function setError(fieldId, msg) {
  const fg  = document.getElementById(`fg-${fieldId}`);
  const err = document.getElementById(`err-${fieldId}`);
  if (!fg || !err) return;
  fg.classList.add("has-error");
  err.textContent = msg;
}

function clearError(fieldId) {
  const fg  = document.getElementById(`fg-${fieldId}`);
  const err = document.getElementById(`err-${fieldId}`);
  if (!fg || !err) return;
  fg.classList.remove("has-error");
  err.textContent = "";
}

function clearAllErrors() {
  ["name","age","gender","cnic","email","password","address"].forEach(clearError);
}

function validateForm() {
  clearAllErrors();
  let ok = true;
  const CNIC_RE = /^\d{5}-\d{7}-\d{1}$/;

  const name    = document.getElementById("name").value.trim();
  const age     = parseInt(document.getElementById("age").value);
  const gender  = document.getElementById("gender").value;
  const cnic    = document.getElementById("cnic").value.trim();
  const email   = document.getElementById("email").value.trim();
  const pass    = document.getElementById("password").value;
  const address = document.getElementById("address").value.trim();

  if (!name)                    { setError("name", "Naam zaroori hai");                ok = false; }
  if (isNaN(age) || age < 18)   { setError("age",  "Umar 18+ honi chahiye");           ok = false; }
  if (!gender)                  { setError("gender", "Jins select karo");              ok = false; }
  if (!CNIC_RE.test(cnic))      { setError("cnic",  "Format: 12345-1234567-1");        ok = false; }
  if (!email.includes("@"))     { setError("email",  "Valid email dalen");             ok = false; }
  if (pass.length < 8)          { setError("password","Kam az kam 8 characters");      ok = false; }
  if (!address)                 { setError("address","Pata zaroori hai");              ok = false; }

  return ok;
}


// ── Main register function ────────────────────────────────────────────────────
async function registerUser() {
  // Client validation
  if (!validateForm()) {
    showToast("Form mein errors hain — theek karo", "err");
    return;
  }

  // FP check
  const fpTemplate = document.getElementById("fp-template-output").value;
  if (!fpTemplate) {
    showToast("Fingerprint scan karo — dayen taraf button dabao", "err");
    return;
  }

  // Loading state
  const btn = document.getElementById("btn-register");
  btn.disabled = true;
  btn.classList.add("loading");

  try {
    const payload = {
      name       : document.getElementById("name").value.trim(),
      age        : parseInt(document.getElementById("age").value),
      gender     : document.getElementById("gender").value,
      cnic       : document.getElementById("cnic").value.trim(),
      email      : document.getElementById("email").value.trim().toLowerCase(),
      password   : document.getElementById("password").value,
      address    : document.getElementById("address").value.trim(),
      fp_template: fpTemplate,
    };

    const res  = await fetch(`${API}/register`, {
      method     : "POST",
      credentials: "include",
      headers    : { "Content-Type": "application/json" },
      body       : JSON.stringify(payload),
    });

    const data = await res.json();

    if (data.success) {
      showToast("✓ Registration kamyab! Login page par ja rahe hain...", "ok");
      setTimeout(() => { window.location.href = "login.html"; }, 2000);
    } else {
      showToast(data.error || "Registration fail ho gayi", "err");
    }

  } catch (err) {
    showToast("Server se connection nahi — backend chal raha hai?", "err");
    console.error("[REG]", err);
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
  }
}


// ── Toast notification ────────────────────────────────────────────────────────
let _toastTimer = null;

function showToast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className   = `show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => {
    el.classList.remove("show");
  }, 3500);
}