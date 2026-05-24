"""
routes/auth.py — Updated Authentication Routes
POST /api/register  — Voter registration with fingerprint + photo
POST /api/login     — Login with CNIC + fingerprint (no password)
GET  /api/logout    — Session clear
GET  /api/me        — Current session voter info
GET  /api/profile   — Full voter profile (for profile page)
"""

from flask import Blueprint, request, jsonify, session
import bcrypt
from bson import ObjectId
from config import voters_col
from fingerprint import match_template, _validate_b64

auth_bp = Blueprint("auth", __name__)


# ─── POST /api/register ───────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new voter.

    Request JSON:
      {
        "name"        : "Muhammad Ali",
        "age"         : 25,
        "gender"      : "male",
        "cnic"        : "12345-1234567-1",
        "email"       : "voter@example.com",
        "password"    : "securepass123",
        "address"     : "House 5, Lahore",
        "fp_template" : "<base64>",
        "photo"       : "<base64 data URL>"    -- optional
      }

    Response:
      { "success": true, "voter_id": "<id>" }
      { "error": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    # Required fields
    required = ["name", "age", "gender", "cnic", "email", "password", "address", "fp_template"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' field is missing"}), 422

    name        = data["name"].strip()
    age         = int(data["age"])
    gender      = data["gender"].strip().lower()
    cnic        = data["cnic"].strip()
    email       = data["email"].strip().lower()
    password    = data["password"]
    address     = data["address"].strip()
    fp_template = data["fp_template"].strip()
    photo       = data.get("photo", "").strip()  # optional base64 data URL

    # Validation
    import re
    CNIC_RE = r"^\d{5}-\d{7}-\d{1}$"
    if not re.match(CNIC_RE, cnic):
        return jsonify({"error": "CNIC format invalid — correct format: 12345-1234567-1"}), 422
    if age < 18:
        return jsonify({"error": "Age must be 18 or older"}), 422
    if "@" not in email:
        return jsonify({"error": "Valid email address required"}), 422
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 422
    if gender not in ["male", "female", "other"]:
        return jsonify({"error": "Gender must be: male, female, or other"}), 422

    # Validate photo if provided
    if photo:
        # Accept data URL format (data:image/...;base64,...)
        if not photo.startswith("data:image/"):
            return jsonify({"error": "Photo must be a valid image data URL"}), 422

    # FP template validate
    try:
        _validate_b64(fp_template)
    except ValueError as e:
        return jsonify({"error": f"Fingerprint template invalid: {e}"}), 422

    # Uniqueness checks
    if voters_col.find_one({"cnic": cnic}):
        return jsonify({"error": "This CNIC is already registered"}), 409
    if voters_col.find_one({"email": email}):
        return jsonify({"error": "This email is already registered"}), 409

    # Hash password
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Insert voter
    voter_doc = {
        "name"         : name,
        "age"          : age,
        "gender"       : gender,
        "cnic"         : cnic,
        "email"        : email,
        "password"     : hashed_pw,
        "address"      : address,
        "fp_template"  : fp_template,
        "photo"        : photo if photo else None,
        "hasVoted"     : False,
        "voted_at"     : None,
        "vote_location": None,
        "created_at"   : __import__("datetime").datetime.utcnow(),
    }

    result   = voters_col.insert_one(voter_doc)
    voter_id = str(result.inserted_id)

    return jsonify({
        "success" : True,
        "voter_id": voter_id,
        "message" : "Registration successful! Please login."
    }), 201


# ─── POST /api/login ──────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Voter login — CNIC + fingerprint only (no password required).

    Request JSON:
      {
        "cnic"       : "12345-1234567-1",
        "fp_template": "<base64>"
      }

    Response:
      { "success": true, "voter": { "id", "name", "hasVoted" } }
      { "error": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    cnic        = data.get("cnic", "").strip()
    fp_template = data.get("fp_template", "").strip()

    if not cnic or not fp_template:
        return jsonify({"error": "CNIC and fingerprint are both required"}), 422

    # Validate CNIC format
    import re
    CNIC_RE = r"^\d{5}-\d{7}-\d{1}$"
    if not re.match(CNIC_RE, cnic):
        return jsonify({"error": "CNIC format invalid — correct format: 12345-1234567-1"}), 422

    # FP validate
    try:
        _validate_b64(fp_template)
    except ValueError as e:
        return jsonify({"error": f"Fingerprint template invalid: {e}"}), 422

    # Find voter by CNIC
    voter = voters_col.find_one({"cnic": cnic})
    if not voter:
        return jsonify({"error": "CNIC not registered — please register first"}), 401

    # Fingerprint check
    stored_fp = voter.get("fp_template", "")
    if not stored_fp:
        return jsonify({"error": "Voter fingerprint not registered — contact admin"}), 403

    fp_match = match_template(fp_template, stored_fp)
    if not fp_match:
        return jsonify({"error": "Fingerprint does not match — use the same finger as registration"}), 401

    # Set session
    voter_id = str(voter["_id"])
    session["voter_id"]   = voter_id
    session["voter_name"] = voter["name"]
    session["is_voter"]   = True

    return jsonify({
        "success": True,
        "voter"  : {
            "id"      : voter_id,
            "name"    : voter["name"],
            "cnic"    : voter["cnic"],
            "email"   : voter["email"],
            "hasVoted": voter.get("hasVoted", False),
        },
        "message": f"Welcome, {voter['name']}!"
    }), 200


# ─── GET /api/logout ──────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["GET"])
def logout():
    """Clear session."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out"}), 200


# ─── GET /api/me ──────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
def me():
    """Current logged-in voter info."""
    voter_id = session.get("voter_id")
    if not voter_id:
        return jsonify({"error": "Not logged in", "logged_in": False}), 401

    voter = voters_col.find_one(
        {"_id": ObjectId(voter_id)},
        {"password": 0, "fp_template": 0}
    )
    if not voter:
        session.clear()
        return jsonify({"error": "Voter not found", "logged_in": False}), 401

    return jsonify({
        "logged_in": True,
        "voter": {
            "id"      : voter_id,
            "name"    : voter["name"],
            "cnic"    : voter.get("cnic", ""),
            "email"   : voter["email"],
            "hasVoted": voter.get("hasVoted", False),
            "gender"  : voter.get("gender"),
            "photo"   : voter.get("photo"),  # include photo for navbar avatar
        }
    }), 200


# ─── GET /api/profile ─────────────────────────────────────────────────────────
@auth_bp.route("/profile", methods=["GET"])
def profile():
    """
    Full voter profile — for profile page.
    Requires active session.
    """
    voter_id = session.get("voter_id")
    if not voter_id:
        return jsonify({"error": "Not logged in", "logged_in": False}), 401

    voter = voters_col.find_one(
        {"_id": ObjectId(voter_id)},
        {"password": 0, "fp_template": 0}
    )
    if not voter:
        session.clear()
        return jsonify({"error": "Voter not found", "logged_in": False}), 401

    voted_at = voter.get("voted_at")
    return jsonify({
        "logged_in": True,
        "voter": {
            "id"           : voter_id,
            "name"         : voter["name"],
            "cnic"         : voter.get("cnic", ""),
            "email"        : voter["email"],
            "gender"       : voter.get("gender", ""),
            "age"          : voter.get("age"),
            "address"      : voter.get("address", ""),
            "photo"        : voter.get("photo"),
            "hasVoted"     : voter.get("hasVoted", False),
            "voted_at"     : voted_at.isoformat() if voted_at else None,
            "vote_location": voter.get("vote_location"),
            "created_at"   : voter["created_at"].isoformat() if voter.get("created_at") else None,
        }
    }), 200