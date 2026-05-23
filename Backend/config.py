from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
print("MongoDB Connected ✅")

db = client["evoting"]

voters = db["voters"]
candidates = db["candidates"]

