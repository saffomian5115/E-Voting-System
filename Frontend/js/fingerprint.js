/**
 * fingerprint.js — Module 2: Frontend Fingerprint Engine
 * SecuGen HU20 + SGI BWAPI (FPWebHost on port 9734)
 *
 * Public API:
 *   FingerprintScanner.init(containerId)   — UI mount karo
 *   FingerprintScanner.capture()           — scan karo, base64 return karo
 *   FingerprintScanner.verify(voterId)     — server se match karo
 *   FingerprintScanner.reset()             — UI reset karo
 */

const FingerprintScanner = (() => {

  // ── Config ────────────────────────────────────────────────────────────────
  const BWAPI_BASE   = "http://localhost:9734";
  const BACKEND_BASE = "http://localhost:5000/api";
  const CAPTURE_URL  = `${BWAPI_BASE}/SGIFPCapture`;
  const TIMEOUT_MS   = 10000;

  // ── State ─────────────────────────────────────────────────────────────────
  let _containerId   = null;
  let _lastTemplate  = null;   // base64 ISO template
  let _status        = "idle"; // idle | scanning | verified | failed

  // ── Status labels ─────────────────────────────────────────────────────────
  const STATUS_TEXT = {
    idle     : { text: "Tayyar hai — Scan karo",    icon: "◎", cls: "fp-idle"     },
    scanning : { text: "Scanning...",                icon: "⟳", cls: "fp-scanning" },
    verified : { text: "Verified ✓",                icon: "✓", cls: "fp-verified" },
    failed   : { text: "Match nahi hua — dobara try karo", icon: "✗", cls: "fp-failed"   },
    error    : { text: "Device error — check karein", icon: "!", cls: "fp-error"    },
  };

  // ══════════════════════════════════════════════════════════════════════════
  // SECTION 1 — UI
  // ══════════════════════════════════════════════════════════════════════════

  /**
   * Container mein fingerprint scanner UI inject karo.
   * @param {string} containerId — HTML element ka id
   */
  function init(containerId) {
    _containerId = containerId;
    const el = document.getElementById(containerId);
    if (!el) { console.error(`[FP] #${containerId} nahi mila`); return; }

    el.innerHTML = `
      <div class="fp-widget" id="fp-widget">

        <!-- Scanner visual -->
        <div class="fp-scanner-ring" id="fp-ring">
          <div class="fp-scanner-inner">
            <svg class="fp-icon" viewBox="0 0 64 64" fill="none"
                 xmlns="http://www.w3.org/2000/svg">
              <!-- Fingerprint lines SVG -->
              <path d="M32 8C19 8 10 18 10 30c0 8 4 15 10 19" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 14c-9 0-16 7-16 16 0 6 3 11 7 14" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 20c-5 0-10 4-10 10 0 4 2 7 5 9" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 26c-2 0-4 2-4 4 0 1.5.8 3 2 4" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 8c13 0 22 10 22 22 0 8-4 15-10 19" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 14c9 0 16 7 16 16 0 6-3 11-7 14" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 20c5 0 10 4 10 10 0 4-2 7-5 9" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <path d="M32 26c2 0 4 2 4 4 0 1.5-.8 3-2 4" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round"/>
              <circle cx="32" cy="30" r="3" fill="currentColor"/>
              <!-- Scan line animation (CSS se control hogi) -->
              <rect class="fp-scanline" x="10" y="28" width="44" height="2"
                    rx="1" fill="currentColor" opacity="0.7"/>
            </svg>
          </div>
        </div>

        <!-- Status text -->
        <div class="fp-status-row">
          <span class="fp-status-icon" id="fp-status-icon">◎</span>
          <span class="fp-status-text" id="fp-status-text">Tayyar hai — Scan karo</span>
        </div>

        <!-- Buttons -->
        <div class="fp-btn-row">
          <button class="fp-btn fp-btn-scan" id="fp-btn-scan"
                  onclick="FingerprintScanner.capture()">
            <span>Fingerprint Scan Karo</span>
          </button>
          <button class="fp-btn fp-btn-reset" id="fp-btn-reset"
                  onclick="FingerprintScanner.reset()" style="display:none">
            Dubara Scan
          </button>
        </div>

        <!-- Hidden template output -->
        <input type="hidden" id="fp-template-output" name="fp_template" value="">
      </div>
    `;

    _injectStyles();
    console.log("[FP] Scanner UI ready");
  }


  // ══════════════════════════════════════════════════════════════════════════
  // SECTION 2 — Capture
  // ══════════════════════════════════════════════════════════════════════════

  /**
   * SecuGen BWAPI se fingerprint capture karo.
   * @returns {Promise<string>}  base64 ISO template
   * @throws  Error agar capture fail ho
   */
  async function capture() {
    if (_status === "scanning") return;

    _setStatus("scanning");
    _lastTemplate = null;

    try {
      const template = await _callBWAPI();
      _lastTemplate  = template;

      // Hidden input update karo (forms ke liye)
      const hiddenInput = document.getElementById("fp-template-output");
      if (hiddenInput) hiddenInput.value = template;

      _setStatus("verified");
      return template;

    } catch (err) {
      console.error("[FP] Capture failed:", err.message);
      _setStatus("error");
      throw err;
    }
  }


  /**
   * BWAPI ko actually call karo — template bytes wapis aate hain.
   * @private
   */
  async function _callBWAPI() {
    const controller = new AbortController();
    const timeoutId  = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const res = await fetch(CAPTURE_URL, {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify({
          Timeout     : 10000,
          Quality     : 50,     // min acceptable quality
          licstr      : "",
          templateformat: "ISO",
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`BWAPI HTTP ${res.status}`);
      }

      const data = await res.json();

      // BWAPI returns ErrorCode 0 on success
      if (data.ErrorCode !== 0 && data.ErrorCode !== "0") {
        throw new Error(`BWAPI error code: ${data.ErrorCode} — ${data.ErrorDescription || ""}`);
      }

      if (!data.BMPBase64 && !data.TemplateBase64) {
        throw new Error("BWAPI se template nahi aaya — finger theek se rakho");
      }

      // TemplateBase64 prefer karo (ISO format), warna BMPBase64
      return data.TemplateBase64 || data.BMPBase64;

    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        throw new Error("Timeout — BWAPI ne 10s mein jawab nahi diya");
      }
      throw err;
    }
  }


  // ══════════════════════════════════════════════════════════════════════════
  // SECTION 3 — Verify (Server-side match)
  // ══════════════════════════════════════════════════════════════════════════

  /**
   * Captured template ko backend se verify karo.
   * @param {string} voterId — MongoDB voter _id (session mein hoga)
   * @returns {Promise<boolean>}
   */
  async function verify(voterId) {
    if (!_lastTemplate) {
      throw new Error("Pehle fingerprint scan karo");
    }

    const res = await fetch(`${BACKEND_BASE}/fp/verify`, {
      method     : "POST",
      credentials: "include",
      headers    : { "Content-Type": "application/json" },
      body       : JSON.stringify({
        fp_template: _lastTemplate,
        voter_id   : voterId,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Server error");
    }

    if (data.match) {
      _setStatus("verified");
    } else {
      _setStatus("failed");
    }

    return data.match;
  }


  /**
   * Directly do templates compare karo (registration ke waqt).
   * @param {string} storedB64 — DB se aaya stored template
   * @returns {Promise<boolean>}
   */
  async function verifyDirect(storedB64) {
    if (!_lastTemplate) {
      throw new Error("Pehle fingerprint scan karo");
    }

    const res = await fetch(`${BACKEND_BASE}/fp/verify`, {
      method     : "POST",
      credentials: "include",
      headers    : { "Content-Type": "application/json" },
      body       : JSON.stringify({
        fp_template      : _lastTemplate,
        stored_template  : storedB64,
      }),
    });

    const data = await res.json();
    const matched = !!data.match;
    _setStatus(matched ? "verified" : "failed");
    return matched;
  }


  // ══════════════════════════════════════════════════════════════════════════
  // SECTION 4 — Helpers
  // ══════════════════════════════════════════════════════════════════════════

  function reset() {
    _lastTemplate = null;
    _setStatus("idle");
    const hiddenInput = document.getElementById("fp-template-output");
    if (hiddenInput) hiddenInput.value = "";
  }

  function getTemplate() { return _lastTemplate; }
  function getStatus()   { return _status; }
  function isReady()     { return _status === "verified" && !!_lastTemplate; }

  function _setStatus(newStatus) {
    _status = newStatus;
    const info      = STATUS_TEXT[newStatus] || STATUS_TEXT.idle;
    const ring      = document.getElementById("fp-ring");
    const iconEl    = document.getElementById("fp-status-icon");
    const textEl    = document.getElementById("fp-status-text");
    const scanBtn   = document.getElementById("fp-btn-scan");
    const resetBtn  = document.getElementById("fp-btn-reset");

    if (!ring) return; // UI not mounted

    // Remove all state classes
    ring.className = "fp-scanner-ring";
    ring.classList.add(info.cls);

    if (iconEl) iconEl.textContent = info.icon;
    if (textEl) textEl.textContent = info.text;

    // Button visibility
    const done = newStatus === "verified" || newStatus === "failed";
    if (scanBtn)  scanBtn.style.display  = done ? "none"  : "";
    if (resetBtn) resetBtn.style.display = done ? ""      : "none";

    // Dispatch custom event (other modules sun sakte hain)
    document.dispatchEvent(new CustomEvent("fp:statusChange", {
      detail: { status: newStatus, template: _lastTemplate }
    }));
  }


  // ── CSS injection ─────────────────────────────────────────────────────────
  function _injectStyles() {
    if (document.getElementById("fp-styles")) return;
    const style = document.createElement("style");
    style.id = "fp-styles";
    style.textContent = `
      .fp-widget {
        display       : flex;
        flex-direction: column;
        align-items   : center;
        gap           : 1.2rem;
        padding       : 1.5rem;
        user-select   : none;
      }

      /* Ring */
      .fp-scanner-ring {
        width           : 130px;
        height          : 130px;
        border-radius   : 50%;
        border          : 2.5px solid rgba(0,234,255,.25);
        display         : flex;
        align-items     : center;
        justify-content : center;
        position        : relative;
        transition      : border-color .4s, box-shadow .4s;
        background      : rgba(0,234,255,.04);
      }
      .fp-scanner-ring.fp-idle     { border-color: rgba(0,234,255,.25); }
      .fp-scanner-ring.fp-scanning {
        border-color: #00eaff;
        box-shadow  : 0 0 22px rgba(0,234,255,.35), inset 0 0 14px rgba(0,234,255,.1);
        animation   : fp-pulse 1.2s ease-in-out infinite;
      }
      .fp-scanner-ring.fp-verified {
        border-color: #00ff88;
        box-shadow  : 0 0 24px rgba(0,255,136,.4);
        color       : #00ff88;
      }
      .fp-scanner-ring.fp-failed {
        border-color: #ff4466;
        box-shadow  : 0 0 20px rgba(255,68,102,.35);
        color       : #ff4466;
      }
      .fp-scanner-ring.fp-error    { border-color: #ffaa00; color: #ffaa00; }

      .fp-scanner-inner {
        width          : 86px;
        height         : 86px;
        display        : flex;
        align-items    : center;
        justify-content: center;
      }
      .fp-icon {
        width : 64px;
        height: 64px;
        color : currentColor;
        opacity: .85;
        transition: color .4s;
      }

      /* Scanline animation */
      @keyframes fp-scan {
        0%   { transform: translateY(-18px); opacity: 0; }
        10%  { opacity: .8; }
        90%  { opacity: .8; }
        100% { transform: translateY(18px);  opacity: 0; }
      }
      .fp-scanning .fp-scanline {
        animation: fp-scan 1.4s linear infinite;
        color: #00eaff;
      }

      @keyframes fp-pulse {
        0%,100% { box-shadow: 0 0 14px rgba(0,234,255,.3), inset 0 0 8px rgba(0,234,255,.08); }
        50%     { box-shadow: 0 0 30px rgba(0,234,255,.5), inset 0 0 20px rgba(0,234,255,.15); }
      }

      /* Status row */
      .fp-status-row {
        display    : flex;
        align-items: center;
        gap        : .5rem;
        font-size  : .85rem;
        color      : rgba(255,255,255,.7);
        font-family: 'Courier New', monospace;
      }
      .fp-status-icon { font-size: 1.1rem; }

      .fp-scanning .fp-status-icon {
        display        : inline-block;
        animation      : fp-spin 1s linear infinite;
      }
      @keyframes fp-spin {
        to { transform: rotate(360deg); }
      }

      /* Buttons */
      .fp-btn-row { display: flex; gap: .7rem; }
      .fp-btn {
        padding      : .55rem 1.3rem;
        border-radius: 6px;
        border       : 1.5px solid rgba(0,234,255,.4);
        background   : rgba(0,234,255,.08);
        color        : #00eaff;
        font-size    : .82rem;
        cursor       : pointer;
        transition   : background .2s, border-color .2s, transform .1s;
        font-family  : 'Courier New', monospace;
        letter-spacing:.03em;
      }
      .fp-btn:hover {
        background  : rgba(0,234,255,.18);
        border-color: #00eaff;
        transform   : translateY(-1px);
      }
      .fp-btn:active { transform: translateY(0); }
      .fp-btn-reset  {
        border-color: rgba(255,255,255,.2);
        color       : rgba(255,255,255,.6);
        background  : transparent;
      }
      .fp-btn-reset:hover {
        border-color: rgba(255,255,255,.5);
        background  : rgba(255,255,255,.06);
        color       : #fff;
      }
    `;
    document.head.appendChild(style);
  }


  // ── Public API ────────────────────────────────────────────────────────────
  return { init, capture, verify, verifyDirect, reset, getTemplate, getStatus, isReady };

})();

// Global expose (non-module scripts ke liye)
window.FingerprintScanner = FingerprintScanner;