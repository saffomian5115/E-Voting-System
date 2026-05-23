/**
 * login.js — Module 3: Login Logic
 * Email + Password + Fingerprint — teeno zaroori
 */

const API = "http://localhost:5000/api";

// ── On page load ──────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  // Agar pehle se logged in hai to redirect karo
  checkExistingSession();

  // Fingerprint scanner init
  FingerprintScanner.init("fp-container");

  // FP status badge
  document.addEventListener("fp:statusChange", (e) => {
    const badge  = document.getElementById("fp-status-badge");
    const hidden = document.getElementById("fp-template-output");

    if (e.detail.status === "verified" && e.detail.template) {
      hidden.value      = e.detail.template;
      badge.textContent = "✓ Fingerprint Ready";
      badge.className   = "ready";
    } else if (e.detail.status === "failed" || e.detail.status === "error") {
      hidden.value      = "";
      badge.textContent = "✗ Scan fail — dobara try karo";
      badge.className   = "failed";
    } else {
      hidden.value      = "";
      badge.textContent = "Scan nahi hua";
      badge.className   = "";
    }
  });

  // Enter key support
  document.getElementById("password").addEventListener("keydown", (e) => {
    if (e.key === "Enter") loginUser();
  });
});


// ── Session check ─────────────────────────────────────────────────────────────
async function checkExistingSession() {
  try {
    const res = await fetch(`${API}/me`, { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (data.logged_in) {
        window.location.href = "vote.html";
      }
    }
  } catch (e) {
    // Backend down — koi baat nahi, login page pe rehne do
  }
}


// ── Field validation helpers ──────────────────────────────────────────────────
function setError(fieldId, msg) {
  const fg  = document.getElementById(`fg-${fieldId}`);
  const err = document.getElementById(`err-${fieldId}`);
  if (!fg || !err) return;
  fg.classList.add("has-error");
  err.textContent = msg;
}

function clearAllErrors() {
  ["email", "password"].forEach((id) => {
    const fg  = document.getElementById(`fg-${id}`);
    const err = document.getElementById(`err-${id}`);
    if (fg)  fg.classList.remove("has-error");
    if (err) err.textContent = "";
  });
}

function validateForm() {
  clearAllErrors();
  let ok = true;

  const email    = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !email.includes("@")) {
    setError("email", "Valid email dalen");
    ok = false;
  }
  if (!password || password.length < 8) {
    setError("password", "Password 8 characters se zyada hona chahiye");
    ok = false;
  }
  return ok;
}


// ── Main login function ───────────────────────────────────────────────────────
async function loginUser() {
  if (!validateForm()) {
    showToast("Form mein errors hain — theek karo", "err");
    return;
  }

  const fpTemplate = document.getElementById("fp-template-output").value;
  if (!fpTemplate) {
    showToast("Fingerprint scan karo — dayen taraf button dabao", "err");
    return;
  }

  const btn = document.getElementById("btn-login");
  btn.disabled = true;
  btn.classList.add("loading");

  try {
    const payload = {
      email      : document.getElementById("email").value.trim().toLowerCase(),
      password   : document.getElementById("password").value,
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
        window.location.href = data.voter.hasVoted ? "result.html" : "vote.html";
      }, 1500);
    } else {
      showToast(data.error || "Login fail ho gaya", "err");
      // FP reset karo taake dobara scan kar sake
      FingerprintScanner.reset();
      document.getElementById("fp-template-output").value = "";
      document.getElementById("fp-status-badge").textContent = "Scan nahi hua";
      document.getElementById("fp-status-badge").className = "";
    }

  } catch (err) {
    showToast("Server se connection nahi — backend chal raha hai?", "err");
    console.error("[LOGIN]", err);
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