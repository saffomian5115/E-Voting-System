"""
routes/auth.py — Module 3: Authentication Routes
POST /api/register  — Voter registration with fingerprint
POST /api/login     — Login with email + password + fingerprint
GET  /api/logout    — Session clear
GET  /api/me        — Current session voter info
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
    Naya voter register karo.

    Request JSON:
      {
        "name"        : "Muhammad Ali",
        "age"         : 25,
        "gender"      : "male",
        "cnic"        : "12345-1234567-1",
        "email"       : "voter@example.com",
        "password"    : "securepass123",
        "address"     : "Ghar 5, Lahore",
        "fp_template" : "<base64>"
      }

    Response:
      { "success": true, "voter_id": "<id>" }
      { "error": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    # ── Required fields check ─────────────────────────────────────────────────
    required = ["name", "age", "gender", "cnic", "email", "password", "address", "fp_template"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' field missing hai"}), 422

    name        = data["name"].strip()
    age         = int(data["age"])
    gender      = data["gender"].strip().lower()
    cnic        = data["cnic"].strip()
    email       = data["email"].strip().lower()
    password    = data["password"]
    address     = data["address"].strip()
    fp_template = data["fp_template"].strip()

    # ── Validation ────────────────────────────────────────────────────────────
    import re
    CNIC_RE = r"^\d{5}-\d{7}-\d{1}$"
    if not re.match(CNIC_RE, cnic):
        return jsonify({"error": "CNIC format galat hai — sahi format: 12345-1234567-1"}), 422

    if age < 18:
        return jsonify({"error": "Umar 18 saal se zyada honi chahiye"}), 422

    if "@" not in email:
        return jsonify({"error": "Valid email address chahiye"}), 422

    if len(password) < 8:
        return jsonify({"error": "Password kam az kam 8 characters ka hona chahiye"}), 422

    if gender not in ["male", "female", "other"]:
        return jsonify({"error": "Jins: male, female, ya other honi chahiye"}), 422

    # FP template validate
    try:
        _validate_b64(fp_template)
    except ValueError as e:
        return jsonify({"error": f"Fingerprint template invalid: {e}"}), 422

    # ── Uniqueness checks ─────────────────────────────────────────────────────
    if voters_col.find_one({"cnic": cnic}):
        return jsonify({"error": "Ye CNIC pehle se registered hai"}), 409

    if voters_col.find_one({"email": email}):
        return jsonify({"error": "Ye email pehle se registered hai"}), 409

    # ── Hash password ─────────────────────────────────────────────────────────
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # ── Insert voter ──────────────────────────────────────────────────────────
    voter_doc = {
        "name"       : name,
        "age"        : age,
        "gender"     : gender,
        "cnic"       : cnic,
        "email"      : email,
        "password"   : hashed_pw,
        "address"    : address,
        "fp_template": fp_template,
        "hasVoted"   : False,
        "voted_at"   : None,
        "vote_location": None,
        "created_at" : __import__("datetime").datetime.utcnow(),
    }

    result   = voters_col.insert_one(voter_doc)
    voter_id = str(result.inserted_id)

    return jsonify({
        "success" : True,
        "voter_id": voter_id,
        "message" : "Registration kamyab ho gayi! Ab login karo."
    }), 201


# ─── POST /api/login ──────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Voter login — email + password + fingerprint teeno zaroori hain.

    Request JSON:
      {
        "email"      : "voter@example.com",
        "password"   : "securepass123",
        "fp_template": "<base64>"
      }

    Response:
      { "success": true, "voter": { "id", "name", "hasVoted" } }
      { "error": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body chahiye"}), 400

    email       = data.get("email", "").strip().lower()
    password    = data.get("password", "")
    fp_template = data.get("fp_template", "").strip()

    if not email or not password or not fp_template:
        return jsonify({"error": "Email, password aur fingerprint teeno zaroori hain"}), 422

    # FP validate
    try:
        _validate_b64(fp_template)
    except ValueError as e:
        return jsonify({"error": f"Fingerprint template invalid: {e}"}), 422

    # ── Find voter ────────────────────────────────────────────────────────────
    voter = voters_col.find_one({"email": email})
    if not voter:
        return jsonify({"error": "Email ya password galat hai"}), 401

    # ── Password check ────────────────────────────────────────────────────────
    stored_pw = voter.get("password", "")
    pw_ok = bcrypt.checkpw(password.encode("utf-8"), stored_pw.encode("utf-8"))
    if not pw_ok:
        return jsonify({"error": "Email ya password galat hai"}), 401

    # ── Fingerprint check ─────────────────────────────────────────────────────
    stored_fp = voter.get("fp_template", "")
    if not stored_fp:
        return jsonify({"error": "Voter ka fingerprint registered nahi hai — admin se rabta karo"}), 403

    fp_match = match_template(fp_template, stored_fp)
    if not fp_match:
        return jsonify({"error": "Fingerprint match nahi hua — sahi ungli rakho ya dobara try karo"}), 401

    # ── Set session ───────────────────────────────────────────────────────────
    voter_id = str(voter["_id"])
    session["voter_id"]   = voter_id
    session["voter_name"] = voter["name"]
    session["is_voter"]   = True

    return jsonify({
        "success": True,
        "voter"  : {
            "id"      : voter_id,
            "name"    : voter["name"],
            "email"   : voter["email"],
            "hasVoted": voter.get("hasVoted", False),
        },
        "message": f"Khush amdeed, {voter['name']}!"
    }), 200


# ─── GET /api/logout ──────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["GET"])
def logout():
    """Session clear karo."""
    session.clear()
    return jsonify({"success": True, "message": "Logout ho gaye"}), 200


# ─── GET /api/me ──────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
def me():
    """
    Current logged-in voter ki info — vote page ke liye session check.
    """
    voter_id = session.get("voter_id")
    if not voter_id:
        return jsonify({"error": "Login nahi hua", "logged_in": False}), 401

    voter = voters_col.find_one({"_id": ObjectId(voter_id)}, {"password": 0, "fp_template": 0})
    if not voter:
        session.clear()
        return jsonify({"error": "Voter nahi mila", "logged_in": False}), 401

    return jsonify({
        "logged_in": True,
        "voter": {
            "id"      : voter_id,
            "name"    : voter["name"],
            "email"   : voter["email"],
            "hasVoted": voter.get("hasVoted", False),
            "gender"  : voter.get("gender"),
        }
    }), 200