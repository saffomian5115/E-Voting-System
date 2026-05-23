"""
routes/result.py — Module 6: Results & Stats Routes

GET /api/results        — Sab candidates ke vote counts
GET /api/results/stats  — Voting turnout aur detailed stats
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
from config import voters_col, candidates_col, schedule_col

result_bp = Blueprint("result", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Results
# ══════════════════════════════════════════════════════════════════════════════

@result_bp.route("/results", methods=["GET"])
def get_results():
    """
    Sab candidates ke results — sorted by votes (highest first).

    Visibility rules:
      - Agar voting khatam ho gayi ho   → results public hain
      - Agar voting chal rahi ho        → results public hain (live count)
      - Agar admin logged in ho         → hamesha results dikho
      - Agar voting shuru nahi hui      → results chupaao (candidates dikhao, votes nahi)

    Response:
      {
        "results": [
          {
            "id"         : "...",
            "name"       : "Imran Khan",
            "party"      : "PTI",
            "symbol"     : "bat",
            "votes"      : 42,
            "percentage" : 35.0
          }, ...
        ],
        "total_votes"   : 120,
        "winner"        : { "id": "...", "name": "...", "party": "...", "votes": 42 },
        "results_public": true/false,
        "schedule"      : { ... }
      }
    """
    # Schedule check
    schedule    = schedule_col.find_one({})
    now         = datetime.utcnow()
    is_admin    = session.get("is_admin", False)
    is_active   = False
    is_past     = False
    schedule_info = None

    if schedule:
        is_active = schedule["start"] <= now <= schedule["end"]
        is_past   = now > schedule["end"]
        schedule_info = {
            "start"    : schedule["start"].isoformat(),
            "end"      : schedule["end"].isoformat(),
            "is_active": is_active,
            "is_past"  : is_past,
        }

    # Results public hain ya nahi
    results_public = is_admin or is_active or is_past

    # Candidates fetch — votes ke saath ya baghair
    docs = list(candidates_col.find({}, sort=[("votes", -1)]))

    total_votes = sum(c.get("votes", 0) for c in docs)

    results = []
    for c in docs:
        votes = c.get("votes", 0) if results_public else None
        pct   = round((votes / total_votes * 100), 1) if (results_public and total_votes > 0 and votes is not None) else None
        results.append({
            "id"        : str(c["_id"]),
            "name"      : c.get("name", ""),
            "party"     : c.get("party", ""),
            "symbol"    : c.get("symbol", ""),
            "votes"     : votes,
            "percentage": pct,
        })

    # Winner (sirf agar results public hain aur koi vote hai)
    winner = None
    if results_public and results and total_votes > 0:
        top = results[0]  # already sorted by votes desc
        winner = {
            "id"        : top["id"],
            "name"      : top["name"],
            "party"     : top["party"],
            "votes"     : top["votes"],
            "percentage": top["percentage"],
        }

    return jsonify({
        "results"       : results,
        "total_votes"   : total_votes if results_public else None,
        "winner"        : winner,
        "results_public": results_public,
        "schedule"      : schedule_info,
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Stats
# ══════════════════════════════════════════════════════════════════════════════

@result_bp.route("/results/stats", methods=["GET"])
def get_stats():
    """
    Detailed voting statistics — results page ke liye.

    Response:
      {
        "total_voters"   : 100,
        "total_voted"    : 45,
        "not_voted"      : 55,
        "turnout_percent": 45.0,
        "male_voted"     : 30,
        "female_voted"   : 15,
        "schedule"       : { ... },
        "voting_active"  : true/false
      }
    """
    total_voters = voters_col.count_documents({})
    total_voted  = voters_col.count_documents({"hasVoted": True})
    not_voted    = total_voters - total_voted
    turnout      = round((total_voted / total_voters * 100), 1) if total_voters > 0 else 0.0

    # Gender breakdown (voted voters mein)
    male_voted   = voters_col.count_documents({"hasVoted": True, "gender": "male"})
    female_voted = voters_col.count_documents({"hasVoted": True, "gender": "female"})

    # Schedule
    schedule    = schedule_col.find_one({})
    now         = datetime.utcnow()
    is_active   = False
    schedule_info = None

    if schedule:
        is_active = schedule["start"] <= now <= schedule["end"]
        schedule_info = {
            "start"    : schedule["start"].isoformat(),
            "end"      : schedule["end"].isoformat(),
            "is_active": is_active,
            "is_past"  : now > schedule["end"],
        }

    return jsonify({
        "total_voters"   : total_voters,
        "total_voted"    : total_voted,
        "not_voted"      : not_voted,
        "turnout_percent": turnout,
        "male_voted"     : male_voted,
        "female_voted"   : female_voted,
        "schedule"       : schedule_info,
        "voting_active"  : is_active,
    }), 200