/**
 * script.js — E-Voting System Shared Utilities
 * Common functions jo multiple pages use karti hain
 */

const API = "http://localhost:5000/api";

// ══════════════════════════════════════════════════════════════════════════════
// SECTION 1 — Toast Notifications
// ══════════════════════════════════════════════════════════════════════════════

let _toastTimer = null;

/**
 * Toast notification dikhao
 * @param {string} msg   - message text
 * @param {"ok"|"err"|"info"} type
 * @param {number} duration - ms (default 3500)
 */
function showToast(msg, type = "ok", duration = 3500) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className   = `toast show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), duration);
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 2 — Session / Auth Helpers
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Current voter session check karo
 * @returns {Promise<object|null>} voter object ya null
 */
async function getSession() {
  try {
    const res  = await fetch(`${API}/me`, { credentials: "include" });
    const data = await res.json();
    return data.logged_in ? data.voter : null;
  } catch(e) {
    return null;
  }
}

/**
 * Voter ko logout karo aur login page pe bhejo
 */
async function logoutUser() {
  try {
    await fetch(`${API}/logout`, { credentials: "include" });
  } catch(e) { /* ignore */ }
  window.location.href = "login.html";
}

/**
 * Agar voter logged in nahi to login page pe redirect karo
 * @returns {Promise<object>} voter object
 */
async function requireLogin() {
  const voter = await getSession();
  if (!voter) {
    window.location.href = "login.html";
    return null;
  }
  return voter;
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 3 — Voting Schedule
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Voting schedule check karo
 * @returns {Promise<{is_active, is_past, start, end}|null>}
 */
async function getSchedule() {
  try {
    const res  = await fetch(`${API}/vote/status`, { credentials: "include" });
    const data = await res.json();
    return data.schedule || null;
  } catch(e) {
    return null;
  }
}

/**
 * Schedule ko human-readable format mein dikhao
 * @param {object} schedule
 */
function formatSchedule(schedule) {
  if (!schedule) return "Schedule set nahi hua";
  const start = new Date(schedule.start);
  const end   = new Date(schedule.end);
  const opts  = { dateStyle: "medium", timeStyle: "short" };
  return `${start.toLocaleString("en-PK", opts)} → ${end.toLocaleString("en-PK", opts)}`;
}

/**
 * Countdown string — kitna waqt bacha hai
 * @param {string} targetDateStr - ISO date string
 * @returns {string}
 */
function getCountdown(targetDateStr) {
  const diff = new Date(targetDateStr) - new Date();
  if (diff <= 0) return "Khatam ho gayi";

  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);

  if (h > 0)  return `${h}h ${m}m baad`;
  if (m > 0)  return `${m}m ${s}s baad`;
  return `${s}s baad`;
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 4 — Fingerprint Helpers
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Fingerprint capture karo aur status badge update karo
 * @param {string} badgeId - status badge element ID
 * @param {string} hiddenId - hidden input ID for template
 */
async function captureAndUpdateBadge(badgeId, hiddenId) {
  const badge  = document.getElementById(badgeId);
  const hidden = document.getElementById(hiddenId);

  if (!badge || !hidden) return;

  badge.textContent = "⟳ Scanning...";
  badge.className   = "badge badge-cyan";

  try {
    const template = await FingerprintScanner.capture();
    hidden.value   = template;
    badge.textContent = "✓ Fingerprint Ready";
    badge.className   = "badge badge-green";
  } catch(e) {
    hidden.value      = "";
    badge.textContent = "✗ Scan fail";
    badge.className   = "badge badge-red";
  }
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 5 — Location Capture
// ══════════════════════════════════════════════════════════════════════════════

/**
 * User ka GPS location capture karo
 * @returns {Promise<{latitude, longitude}|null>}
 */
function captureLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      ()    => resolve(null),
      { timeout: 8000, maximumAge: 60000 }
    );
  });
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 6 — Vote Cast (shared logic)
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Vote cast karo — fingerprint + optional location
 * @param {string} candidateId
 * @param {string} fpTemplate - base64
 * @param {{latitude, longitude}|null} location
 * @returns {Promise<{success, message, error}>}
 */
async function castVoteRequest(candidateId, fpTemplate, location = null) {
  const payload = { candidate_id: candidateId, fp_template: fpTemplate };
  if (location) {
    payload.latitude  = location.latitude;
    payload.longitude = location.longitude;
  }

  const res  = await fetch(`${API}/vote`, {
    method     : "POST",
    credentials: "include",
    headers    : { "Content-Type": "application/json" },
    body       : JSON.stringify(payload),
  });
  return res.json();
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 7 — Results
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Results fetch karo
 * @returns {Promise<object>}
 */
async function fetchResults() {
  const res  = await fetch(`${API}/results`, { credentials: "include" });
  return res.json();
}

/**
 * Stats fetch karo
 * @returns {Promise<object>}
 */
async function fetchStats() {
  const res  = await fetch(`${API}/results/stats`, { credentials: "include" });
  return res.json();
}


// ══════════════════════════════════════════════════════════════════════════════
// SECTION 8 — Utilities
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Candidate symbol se emoji nikalo
 * @param {string} symbol
 */
function symbolToEmoji(symbol) {
  const map = {
    bat:"🏏", arrow:"🏹", book:"📚", lion:"🦁", tiger:"🐯",
    star:"⭐", flag:"🚩", torch:"🔦", key:"🗝️", scale:"⚖️",
    tractor:"🚜", wheel:"☸️", flower:"🌸", moon:"🌙",
  };
  return map[symbol?.toLowerCase()] || "🗳️";
}

/**
 * Number ko localized format mein dikhao
 * @param {number} n
 */
function fmtNum(n) {
  if (n == null) return "--";
  return Number(n).toLocaleString("en-PK");
}

/**
 * Date ko readable format
 * @param {string} iso
 */
function fmtDate(iso) {
  if (!iso) return "--";
  return new Date(iso).toLocaleString("en-PK", {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

/**
 * Async wrapper with loading state on button
 * @param {HTMLElement} btn
 * @param {Function} fn
 */
async function withLoading(btn, fn) {
  btn.disabled = true;
  btn.classList.add("loading");
  try {
    await fn();
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
  }
}

/**
 * Confirm dialog dikhao
 * @param {string} msg
 * @param {string} confirmWord - type karna hoga (e.g. "DELETE")
 * @returns {boolean}
 */
function confirmAction(msg, confirmWord = null) {
  if (confirmWord) {
    const input = prompt(`${msg}\n\nConfirm karne ke liye "${confirmWord}" type karo:`);
    return input === confirmWord;
  }
  return confirm(msg);
}

// Global expose
window.showToast     = showToast;
window.logoutUser    = logoutUser;
window.requireLogin  = requireLogin;
window.getSession    = getSession;
window.getSchedule   = getSchedule;
window.formatSchedule = formatSchedule;
window.getCountdown  = getCountdown;
window.captureLocation = captureLocation;
window.castVoteRequest = castVoteRequest;
window.fetchResults  = fetchResults;
window.fetchStats    = fetchStats;
window.symbolToEmoji = symbolToEmoji;
window.fmtNum        = fmtNum;
window.fmtDate       = fmtDate;
window.withLoading   = withLoading;
window.confirmAction = confirmAction;