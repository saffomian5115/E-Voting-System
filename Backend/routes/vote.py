"""
routes/vote.py — Module 5: Voting System Routes

POST /api/vote  — Vote cast karo (fingerprint + schedule + location check)
GET  /api/vote/status  — Voter ki eligibility check karo
"""

from flask import Blueprint, request, jsonify, session
from bson import ObjectId
from datetime import datetime
from config import voters_col, candidates_col, schedule_col
from fingerprint import match_template, _validate_b64
import urllib.request
import urllib.error
import json

vote_bp = Blueprint("vote", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Vote Cast
# ══════════════════════════════════════════════════════════════════════════════

@vote_bp.route("/vote", methods=["POST"])
def cast_vote():
    """
    Vote cast karo.

    Checks (is order mein):
      1. Voter logged in hai?
      2. Voting schedule active hai?
      3. Voter pehle vote nahi de chuka?
      4. Candidate valid hai?
      5. Fingerprint verify hota hai?

    Request JSON:
      {
        "candidate_id": "<mongo_id>",
        "fp_template" : "<base64>",
        "latitude"    : 31.5497,       (optional)
        "longitude"   : 74.3436        (optional)
      }

    Response:
      { "success": true, "message": "Vote kamyab!" }
      { "error": "..." }
    """
    # ── 1. Login check ────────────────────────────────────────────────────────
    voter_id = session.get("voter_id")
    if not voter_id:
        return jsonify({"error": "Pehle login karo", "auth": False}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    candidate_id = data.get("candidate_id", "").strip()
    fp_template  = data.get("fp_template",  "").strip()
    latitude     = data.get("latitude")
    longitude    = data.get("longitude")

    if not candidate_id:
        return jsonify({"error": "candidate_id zaroori hai"}), 422
    if not fp_template:
        return jsonify({"error": "Fingerprint template zaroori hai"}), 422

    # FP validate karo
    try:
        _validate_b64(fp_template)
    except ValueError as e:
        return jsonify({"error": f"Fingerprint invalid: {e}"}), 422

    # ── 2. Schedule check ─────────────────────────────────────────────────────
    schedule = schedule_col.find_one({})
    if not schedule:
        return jsonify({"error": "Voting schedule set nahi hui — admin se rabta karo"}), 403

    now = datetime.utcnow()
    if now < schedule["start"]:
        diff = schedule["start"] - now
        hours = int(diff.total_seconds() // 3600)
        mins  = int((diff.total_seconds() % 3600) // 60)
        return jsonify({
            "error": f"Voting abhi shuru nahi hui — {hours}h {mins}m baad shuru hogi",
            "schedule_start": schedule["start"].isoformat()
        }), 403

    if now > schedule["end"]:
        return jsonify({
            "error": "Voting khatam ho chuki hai",
            "schedule_end": schedule["end"].isoformat()
        }), 403

    # ── 3. Voter DB se fetch + hasVoted check ─────────────────────────────────
    try:
        voter_oid = ObjectId(voter_id)
    except Exception:
        return jsonify({"error": "Invalid voter session"}), 400

    voter = voters_col.find_one({"_id": voter_oid})
    if not voter:
        session.clear()
        return jsonify({"error": "Voter nahi mila — dobara login karo", "auth": False}), 401

    if voter.get("hasVoted"):
        return jsonify({"error": "Aap pehle hi vote de chuke hain — double vote allowed nahi"}), 403

    # ── 4. Candidate check ────────────────────────────────────────────────────
    try:
        cand_oid = ObjectId(candidate_id)
    except Exception:
        return jsonify({"error": "Invalid candidate ID"}), 400

    candidate = candidates_col.find_one({"_id": cand_oid})
    if not candidate:
        return jsonify({"error": "Candidate nahi mila"}), 404

    # ── 5. Fingerprint verify ─────────────────────────────────────────────────
    stored_fp = voter.get("fp_template", "")
    if not stored_fp:
        return jsonify({"error": "Voter ka fingerprint registered nahi — admin se rabta karo"}), 403

    fp_ok = match_template(fp_template, stored_fp)
    if not fp_ok:
        return jsonify({"error": "Fingerprint verify nahi hua — sahi ungli rakho ya dobara try karo"}), 401

    # ── Location reverse geocode ──────────────────────────────────────────────
    location_data = None
    if latitude is not None and longitude is not None:
        location_data = _reverse_geocode(latitude, longitude)

    # ── Vote record karo (atomic) ─────────────────────────────────────────────
    # Candidate votes++ karo
    candidates_col.update_one(
        {"_id": cand_oid},
        {"$inc": {"votes": 1}}
    )

    # Voter hasVoted = True karo
    voters_col.update_one(
        {"_id": voter_oid},
        {"$set": {
            "hasVoted"     : True,
            "voted_at"     : now,
            "vote_location": location_data,
        }}
    )

    return jsonify({
        "success"  : True,
        "message"  : f"Vote kamyab! Aapne '{candidate['name']}' ({candidate['party']}) ko vote diya.",
        "candidate": {
            "name" : candidate["name"],
            "party": candidate["party"],
        }
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Voter Eligibility Status
# ══════════════════════════════════════════════════════════════════════════════

@vote_bp.route("/vote/status", methods=["GET"])
def vote_status():
    """
    Voter ki current eligibility check karo — vote page ke liye.

    Response:
      {
        "can_vote"       : true/false,
        "reason"         : "...",
        "voter"          : { "name": "...", "hasVoted": false },
        "schedule"       : { "start": "...", "end": "...", "is_active": true },
        "voting_active"  : true/false
      }
    """
    voter_id = session.get("voter_id")
    if not voter_id:
        return jsonify({
            "can_vote"     : False,
            "reason"       : "Login nahi hua",
            "auth"         : False,
            "voting_active": False,
        }), 200  # 200 intentional — vote page handle kare

    # Voter fetch
    try:
        voter = voters_col.find_one(
            {"_id": ObjectId(voter_id)},
            {"password": 0, "fp_template": 0}
        )
    except Exception:
        return jsonify({"can_vote": False, "reason": "Session invalid", "auth": False}), 200

    if not voter:
        return jsonify({"can_vote": False, "reason": "Voter nahi mila", "auth": False}), 200

    # Schedule check
    schedule = schedule_col.find_one({})
    now       = datetime.utcnow()
    is_active = False
    schedule_info = None

    if schedule:
        is_active = schedule["start"] <= now <= schedule["end"]
        schedule_info = {
            "start"    : schedule["start"].isoformat(),
            "end"      : schedule["end"].isoformat(),
            "is_active": is_active,
            "is_past"  : now > schedule["end"],
        }

    # hasVoted check
    if voter.get("hasVoted"):
        return jsonify({
            "can_vote"     : False,
            "reason"       : "Aap pehle hi vote de chuke hain",
            "voter"        : _safe_voter(voter),
            "schedule"     : schedule_info,
            "voting_active": is_active,
        }), 200

    if not schedule:
        return jsonify({
            "can_vote"     : False,
            "reason"       : "Voting schedule set nahi hui",
            "voter"        : _safe_voter(voter),
            "schedule"     : None,
            "voting_active": False,
        }), 200

    if not is_active:
        if now < schedule["start"]:
            reason = "Voting abhi shuru nahi hui"
        else:
            reason = "Voting khatam ho chuki hai"

        return jsonify({
            "can_vote"     : False,
            "reason"       : reason,
            "voter"        : _safe_voter(voter),
            "schedule"     : schedule_info,
            "voting_active": False,
        }), 200

    return jsonify({
        "can_vote"     : True,
        "reason"       : "Aap vote de sakte hain",
        "voter"        : _safe_voter(voter),
        "schedule"     : schedule_info,
        "voting_active": True,
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _reverse_geocode(lat: float, lon: float) -> dict:
    """
    OpenStreetMap Nominatim se coordinates ko city/area mein convert karo.
    Free API — no key needed.
    """
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?lat={lat}&lon={lon}&format=json&accept-language=en"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EVotingSystem/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data    = json.loads(resp.read().decode())
            address = data.get("address", {})
            return {
                "latitude" : lat,
                "longitude": lon,
                "city"     : address.get("city") or address.get("town") or address.get("village", ""),
                "area"     : address.get("suburb") or address.get("neighbourhood") or address.get("county", ""),
                "state"    : address.get("state", ""),
                "country"  : address.get("country", ""),
                "display"  : data.get("display_name", ""),
            }
    except Exception as e:
        print(f"[VOTE] Geocode error: {e}")
        return {
            "latitude" : lat,
            "longitude": lon,
            "city"     : "",
            "area"     : "",
            "state"    : "",
            "country"  : "",
            "display"  : "",
        }


def _safe_voter(voter: dict) -> dict:
    """Voter doc se safe fields nikalo."""
    voted_at = voter.get("voted_at")
    return {
        "id"      : str(voter["_id"]),
        "name"    : voter.get("name", ""),
        "email"   : voter.get("email", ""),
        "hasVoted": voter.get("hasVoted", False),
        "voted_at": voted_at.isoformat() if voted_at else None,
    }