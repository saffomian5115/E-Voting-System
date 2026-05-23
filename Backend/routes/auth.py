from flask import Blueprint, request, jsonify
from config import voters

auth = Blueprint("auth", __name__)

@auth.route("/register", methods=["POST"])
def register():
    data = request.json

    name = data.get("name")
    cnic = data.get("cnic")
    email = data.get("email")
    password = data.get("password")

    # check if user already exists
    if voters.find_one({"email": email}):
        return jsonify({"message": "User already exists"}), 400

    # insert user
    voters.insert_one({
        "name": name,
        "cnic": cnic,
        "email": email,
        "password": password,
        "hasVoted": False
    })

    return jsonify({"message": "Registration Successful"})

@auth.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    user = voters.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    if user["password"] != password:
        return jsonify({"message": "Invalid password"}), 401

    return jsonify({"message": "Login Successful"})
