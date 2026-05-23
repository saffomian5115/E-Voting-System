from flask import Blueprint, request, jsonify
from config import voters, candidates

vote = Blueprint("vote", __name__)

@vote.route("/vote", methods=["POST"])
def cast_vote():
    data = request.json

    email = data.get("email")
    candidate = data.get("candidate")

    user = voters.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    if user["hasVoted"]:
        return jsonify({"message": "You already voted"}), 400

    # increase vote
    candidates.update_one(
        {"name": candidate},
        {"$inc": {"votes": 1}}
    )

    # mark user voted
    voters.update_one(
        {"email": email},
        {"$set": {"hasVoted": True}}
    )

    return jsonify({"message": "Vote Cast Successfully"})
