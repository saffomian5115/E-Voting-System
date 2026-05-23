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