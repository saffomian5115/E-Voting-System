"""
routes/fp.py — Module 2: Fingerprint API Routes
POST /api/fp/verify  — template match karo, True/False return karo
GET  /api/fp/status  — BWAPI service alive hai ya nahi
"""

from flask import Blueprint, request, jsonify, session
from fingerprint import match_by_voter_id, match_template, is_bwapi_alive, _validate_b64

fp_bp = Blueprint("fp", __name__)


# ─── POST /api/fp/verify ──────────────────────────────────────────────────────
@fp_bp.route("/verify", methods=["POST"])
def verify_fingerprint():
    """
    Fingerprint verify karo.

    Two modes:
      1. voter_id + fp_template  → DB stored template se match
      2. fp_template + stored_template → direct comparison (registration ke waqt)

    Request JSON:
      {
        "fp_template"     : "<base64>",          -- required hamesha
        "voter_id"        : "<mongo_id>",         -- mode 1
        "stored_template" : "<base64>"            -- mode 2
      }

    Response:
      { "match": true/false, "mode": "sdk"|"fallback", "message": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    incoming = data.get("fp_template", "").strip()
    if not incoming:
        return jsonify({"error": "fp_template missing hai"}), 400

    # Validate base64
    try:
        _validate_b64(incoming)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    bwapi_up = is_bwapi_alive()
    mode     = "sdk" if bwapi_up else "fallback"

    # ── Mode 1: voter_id given ────────────────────────────────────────────────
    voter_id = data.get("voter_id", "").strip()
    if voter_id:
        matched = match_by_voter_id(voter_id, incoming)
        return jsonify({
            "match"  : matched,
            "mode"   : mode,
            "message": "Fingerprint verified ✓" if matched else "Fingerprint match nahi hua ✗"
        }), 200

    # ── Mode 2: stored_template given ────────────────────────────────────────
    stored = data.get("stored_template", "").strip()
    if stored:
        try:
            _validate_b64(stored)
        except ValueError as e:
            return jsonify({"error": f"stored_template invalid: {e}"}), 422

        matched = match_template(incoming, stored)
        return jsonify({
            "match"  : matched,
            "mode"   : mode,
            "message": "Fingerprint verified ✓" if matched else "Fingerprint match nahi hua ✗"
        }), 200

    return jsonify({"error": "voter_id ya stored_template mein se ek chahiye"}), 400


# ─── GET /api/fp/status ───────────────────────────────────────────────────────
@fp_bp.route("/status", methods=["GET"])
def fp_status():
    """BWAPI service ka status check karo."""
    alive = is_bwapi_alive()
    return jsonify({
        "bwapi_alive": alive,
        "mode"       : "sdk" if alive else "fallback",
        "message"    : "SecuGen BWAPI chal rahi hai ✓" if alive
                       else "BWAPI offline — fallback mode active (dev only)"
    }), 200

# ─── POST /api/fp/capture ─────────────────────────────────────────────────────
@fp_bp.route("/capture", methods=["POST"])
def capture_fingerprint():
    """
    Backend proxy — SecuGen BWAPI se fingerprint capture karo.
    Browser directly BWAPI call nahi kar sakta (SSL/CORS issues),
    isliye Flask middle-man ban ke kaam karta hai.

    Response:
      { "success": true, "template": "<base64>" }
      { "error": "..." }
    """
    from fingerprint import _bwapi_post

    data = request.get_json(silent=True) or {}
    timeout = data.get("timeout", 10000)

    result = _bwapi_post("SGIFPCapture", {
        "Timeout"       : timeout,
        "TemplateFormat": "ISO",
        "licstr"        : "",
    })

    if result is None:
        return jsonify({
            "error": "SecuGen service se connection nahi — FPWebHost.exe chal raha hai?"
        }), 503

    error_code = result.get("ErrorCode", -1)

    if error_code == 0:
        template = result.get("TemplateBase64", "")
        if not template:
            return jsonify({"error": "Template empty aaya — ungli dobara rakho"}), 400
        return jsonify({
            "success" : True,
            "template": template,
        }), 200

    # Error codes mapping
    error_messages = {
        51 : "Device busy — thodi der baad try karo",
        52 : "Capture timeout — ungli sensor par rakho",
        53 : "Capture timeout — ungli sensor par rakho",
        54 : "Finger nahi mila — ungli sensor par rakho",
        55 : "Device connected nahi — USB check karo",
        56 : "Driver error — device reconnect karo",
        59 : "Finger nahi mila — ungli sensor par rakho",
        10004: "Origin error — server config check karo",
    }
    msg = error_messages.get(int(error_code),
                             f"BWAPI error code: {error_code}")
    return jsonify({"error": msg, "error_code": error_code}), 400