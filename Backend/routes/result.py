from flask import Blueprint, jsonify
from config import candidates

result = Blueprint("result", __name__)

@result.route("/results", methods=["GET"])
def get_results():
    data = []

    for c in candidates.find():
        data.append({
            "name": c["name"],
            "votes": c["votes"]
        })

    return jsonify(data)
