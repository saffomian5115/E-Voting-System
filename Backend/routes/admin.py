from flask import Blueprint, jsonify
from config import voters, candidates

admin = Blueprint("admin", __name__)

# Get all voters
@admin.route("/admin/voters", methods=["GET"])
def get_voters():
    data = []
    for v in voters.find():
        data.append({
            "name": v["name"],
            "email": v["email"],
            "hasVoted": v["hasVoted"]
        })
    return jsonify(data)

# Reset votes
@admin.route("/admin/reset", methods=["POST"])
def reset_votes():
    candidates.update_many({}, {"$set": {"votes": 0}})
    voters.update_many({}, {"$set": {"hasVoted": False}})
    return jsonify({"message": "All votes reset"})
