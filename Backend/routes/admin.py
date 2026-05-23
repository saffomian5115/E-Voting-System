"""
routes/admin.py — Module 4: Admin Panel Routes

POST   /api/admin/login               — Admin login
GET    /api/admin/logout              — Admin logout
GET    /api/admin/me                  — Admin session check

GET    /api/admin/candidates          — Sab candidates list
POST   /api/admin/candidates          — Naya candidate add
DELETE /api/admin/candidates/<id>     — Candidate remove

POST   /api/admin/schedule            — Voting schedule set karo
GET    /api/admin/schedule            — Current schedule dekho

GET    /api/admin/voters              — Sab voters list
POST   /api/admin/reset               — Sab votes reset karo
GET    /api/admin/stats               — Dashboard stats
"""

from flask import Blueprint, request, jsonify, session
import bcrypt
from bson import ObjectId
from datetime import datetime
from config import admin_col, voters_col, candidates_col, schedule_col

admin_bp = Blueprint("admin", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 0 — Middleware Helper
# ══════════════════════════════════════════════════════════════════════════════

def admin_required(fn):
    """
    Decorator — route pe lagao, admin session check karta hai.
    Agar admin logged in nahi to 401 return karta hai.
    """
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin login zaroori hai", "auth": False}), 401
        return fn(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Admin Auth
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/login", methods=["POST"])
def admin_login():
    """
    Admin login — username + password.

    Request JSON:
      { "username": "admin", "password": "admin123" }

    Response:
      { "success": true, "message": "..." }
      { "error": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username aur password dono chahiye"}), 422

    admin = admin_col.find_one({"username": username})
    if not admin:
        return jsonify({"error": "Username ya password galat hai"}), 401

    pw_ok = bcrypt.checkpw(
        password.encode("utf-8"),
        admin["password"].encode("utf-8")
    )
    if not pw_ok:
        return jsonify({"error": "Username ya password galat hai"}), 401

    # Admin session set karo
    session["is_admin"]    = True
    session["admin_user"]  = username

    return jsonify({
        "success" : True,
        "message" : f"Khush amdeed, {username}!",
        "username": username
    }), 200


@admin_bp.route("/logout", methods=["GET"])
def admin_logout():
    """Admin session clear karo."""
    session.pop("is_admin",   None)
    session.pop("admin_user", None)
    return jsonify({"success": True, "message": "Admin logout ho gaya"}), 200


@admin_bp.route("/me", methods=["GET"])
@admin_required
def admin_me():
    """Admin session alive hai ya nahi."""
    return jsonify({
        "logged_in": True,
        "username" : session.get("admin_user")
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Candidates Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/candidates", methods=["GET"])
@admin_required
def get_candidates():
    """
    Sab candidates ki list — vote counts ke saath.

    Response:
      {
        "candidates": [
          {
            "id"    : "...",
            "name"  : "Imran Khan",
            "party" : "PTI",
            "symbol": "bat",        (optional)
            "votes" : 42
          }, ...
        ],
        "total": 5
      }
    """
    docs = list(candidates_col.find({}))
    candidates = []
    for c in docs:
        candidates.append({
            "id"    : str(c["_id"]),
            "name"  : c.get("name", ""),
            "party" : c.get("party", ""),
            "symbol": c.get("symbol", ""),
            "votes" : c.get("votes", 0),
        })
    return jsonify({"candidates": candidates, "total": len(candidates)}), 200


@admin_bp.route("/candidates", methods=["POST"])
@admin_required
def add_candidate():
    """
    Naya candidate add karo.

    Request JSON:
      {
        "name"  : "Imran Khan",       -- required
        "party" : "PTI",              -- required
        "symbol": "bat"               -- optional
      }

    Response:
      { "success": true, "id": "...", "message": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    name  = data.get("name", "").strip()
    party = data.get("party", "").strip()

    if not name:
        return jsonify({"error": "Candidate ka naam zaroori hai"}), 422
    if not party:
        return jsonify({"error": "Party ka naam zaroori hai"}), 422

    # Duplicate check (same name + same party)
    existing = candidates_col.find_one({
        "name" : {"$regex": f"^{name}$", "$options": "i"},
        "party": {"$regex": f"^{party}$", "$options": "i"}
    })
    if existing:
        return jsonify({"error": f"'{name}' ({party}) pehle se registered hai"}), 409

    doc = {
        "name"      : name,
        "party"     : party,
        "symbol"    : data.get("symbol", "").strip(),
        "votes"     : 0,
        "created_at": datetime.utcnow(),
    }

    result = candidates_col.insert_one(doc)
    return jsonify({
        "success": True,
        "id"     : str(result.inserted_id),
        "message": f"Candidate '{name}' add ho gaya"
    }), 201


@admin_bp.route("/candidates/<candidate_id>", methods=["DELETE"])
@admin_required
def delete_candidate(candidate_id):
    """
    Candidate delete karo.

    Response:
      { "success": true, "message": "..." }
    """
    try:
        oid = ObjectId(candidate_id)
    except Exception:
        return jsonify({"error": "Invalid candidate ID"}), 400

    candidate = candidates_col.find_one({"_id": oid})
    if not candidate:
        return jsonify({"error": "Candidate nahi mila"}), 404

    # Agar voting chal rahi hai to delete na karo
    if _is_voting_active():
        return jsonify({"error": "Voting chal rahi hai — candidates delete nahi kar sakte"}), 403

    candidates_col.delete_one({"_id": oid})
    return jsonify({
        "success": True,
        "message": f"Candidate '{candidate.get('name')}' delete ho gaya"
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Voting Schedule
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/schedule", methods=["POST"])
@admin_required
def set_schedule():
    """
    Voting schedule set karo.

    Request JSON:
      {
        "start": "2025-08-01T09:00:00",   -- ISO format
        "end"  : "2025-08-01T17:00:00"    -- ISO format
      }

    Response:
      { "success": true, "schedule": { "start": "...", "end": "..." } }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    start_str = data.get("start", "").strip()
    end_str   = data.get("end",   "").strip()

    if not start_str or not end_str:
        return jsonify({"error": "start aur end dono zaroori hain"}), 422

    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt   = datetime.fromisoformat(end_str)
    except ValueError:
        return jsonify({"error": "Date format galat — ISO format use karo: YYYY-MM-DDTHH:MM:SS"}), 422

    if end_dt <= start_dt:
        return jsonify({"error": "End time, start time se baad hona chahiye"}), 422

    # Upsert — sirf ek schedule hoti hai system mein
    schedule_col.replace_one(
        {},
        {
            "start"     : start_dt,
            "end"       : end_dt,
            "set_by"    : session.get("admin_user"),
            "updated_at": datetime.utcnow(),
        },
        upsert=True
    )

    return jsonify({
        "success" : True,
        "schedule": {
            "start"  : start_dt.isoformat(),
            "end"    : end_dt.isoformat(),
        },
        "message": "Voting schedule set ho gayi"
    }), 200


@admin_bp.route("/schedule", methods=["GET"])
@admin_required
def get_schedule():
    """
    Current voting schedule.

    Response:
      {
        "schedule": {
          "start"    : "2025-08-01T09:00:00",
          "end"      : "2025-08-01T17:00:00",
          "is_active": true/false,
          "is_past"  : true/false
        }
      }
      ya { "schedule": null }  agar set nahi hua
    """
    doc = schedule_col.find_one({})
    if not doc:
        return jsonify({"schedule": None}), 200

    now       = datetime.utcnow()
    start_dt  = doc["start"]
    end_dt    = doc["end"]
    is_active = start_dt <= now <= end_dt
    is_past   = now > end_dt

    return jsonify({
        "schedule": {
            "start"    : start_dt.isoformat(),
            "end"      : end_dt.isoformat(),
            "is_active": is_active,
            "is_past"  : is_past,
            "set_by"   : doc.get("set_by", "admin"),
        }
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Voters Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/voters", methods=["GET"])
@admin_required
def get_voters():
    """
    Sab registered voters ki list.

    Query params (optional):
      ?voted=true   — sirf jo vote de chuke
      ?voted=false  — sirf jo abhi nahi vote kiye
      ?q=<search>   — name ya CNIC se search

    Response:
      {
        "voters": [
          {
            "id"          : "...",
            "name"        : "...",
            "cnic"        : "...",
            "email"       : "...",
            "gender"      : "...",
            "age"         : 25,
            "address"     : "...",
            "hasVoted"    : true/false,
            "voted_at"    : "...",
            "vote_location": { "city": "...", "area": "..." }
          }, ...
        ],
        "total"    : 100,
        "voted"    : 45,
        "not_voted": 55
      }
    """
    # Query filters
    query  = {}
    voted_filter = request.args.get("voted")
    search_q     = request.args.get("q", "").strip()

    if voted_filter == "true":
        query["hasVoted"] = True
    elif voted_filter == "false":
        query["hasVoted"] = False

    if search_q:
        query["$or"] = [
            {"name": {"$regex": search_q, "$options": "i"}},
            {"cnic": {"$regex": search_q, "$options": "i"}},
            {"email": {"$regex": search_q, "$options": "i"}},
        ]

    # Password aur fp_template exclude karo
    projection = {"password": 0, "fp_template": 0}
    docs       = list(voters_col.find(query, projection))

    voters = []
    for v in docs:
        voted_at = v.get("voted_at")
        voters.append({
            "id"           : str(v["_id"]),
            "name"         : v.get("name", ""),
            "cnic"         : v.get("cnic", ""),
            "email"        : v.get("email", ""),
            "gender"       : v.get("gender", ""),
            "age"          : v.get("age"),
            "address"      : v.get("address", ""),
            "hasVoted"     : v.get("hasVoted", False),
            "voted_at"     : voted_at.isoformat() if voted_at else None,
            "vote_location": v.get("vote_location"),
        })

    total_all  = voters_col.count_documents({})
    total_voted = voters_col.count_documents({"hasVoted": True})

    return jsonify({
        "voters"   : voters,
        "total"    : total_all,
        "voted"    : total_voted,
        "not_voted": total_all - total_voted,
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Reset Votes
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/reset", methods=["POST"])
@admin_required
def reset_votes():
    """
    Sab votes reset karo — voters ka hasVoted False, candidates ke votes 0.

    Request JSON:
      { "confirm": "RESET" }    -- typo se bachne ke liye

    Response:
      {
        "success"         : true,
        "voters_reset"    : 100,
        "candidates_reset": 5,
        "message"         : "..."
      }
    """
    data = request.get_json(silent=True)
    if not data or data.get("confirm") != "RESET":
        return jsonify({
            "error": "Reset confirm nahi hua — { \"confirm\": \"RESET\" } bhejo"
        }), 400

    # Voters reset
    v_result = voters_col.update_many(
        {},
        {"$set": {
            "hasVoted"     : False,
            "voted_at"     : None,
            "vote_location": None,
        }}
    )

    # Candidates votes reset
    c_result = candidates_col.update_many(
        {},
        {"$set": {"votes": 0}}
    )

    return jsonify({
        "success"         : True,
        "voters_reset"    : v_result.modified_count,
        "candidates_reset": c_result.modified_count,
        "message"         : "Sab votes reset ho gaye — system naye election ke liye tayyar hai"
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Dashboard Stats
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    """
    Admin dashboard ke liye summary stats.

    Response:
      {
        "total_voters"    : 100,
        "total_voted"     : 45,
        "turnout_percent" : 45.0,
        "total_candidates": 5,
        "voting_active"   : true/false,
        "schedule"        : { ... } / null,
        "top_candidate"   : { "name": "...", "party": "...", "votes": 42 } / null
      }
    """
    total_voters    = voters_col.count_documents({})
    total_voted     = voters_col.count_documents({"hasVoted": True})
    total_candidates = candidates_col.count_documents({})

    turnout = round((total_voted / total_voters * 100), 1) if total_voters > 0 else 0.0

    # Top candidate
    top = candidates_col.find_one({}, sort=[("votes", -1)])
    top_candidate = None
    if top and top.get("votes", 0) > 0:
        top_candidate = {
            "name" : top["name"],
            "party": top["party"],
            "votes": top["votes"],
        }

    # Schedule
    schedule_doc = schedule_col.find_one({})
    schedule_info = None
    is_active     = False
    if schedule_doc:
        now      = datetime.utcnow()
        start_dt = schedule_doc["start"]
        end_dt   = schedule_doc["end"]
        is_active = start_dt <= now <= end_dt
        schedule_info = {
            "start"    : start_dt.isoformat(),
            "end"      : end_dt.isoformat(),
            "is_active": is_active,
            "is_past"  : now > end_dt,
        }

    return jsonify({
        "total_voters"    : total_voters,
        "total_voted"     : total_voted,
        "not_voted"       : total_voters - total_voted,
        "turnout_percent" : turnout,
        "total_candidates": total_candidates,
        "voting_active"   : is_active,
        "schedule"        : schedule_info,
        "top_candidate"   : top_candidate,
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Internal Helper
# ══════════════════════════════════════════════════════════════════════════════

def _is_voting_active() -> bool:
    """Check karo ke voting abhi chal rahi hai ya nahi."""
    doc = schedule_col.find_one({})
    if not doc:
        return False
    now = datetime.utcnow()
    return doc["start"] <= now <= doc["end"]