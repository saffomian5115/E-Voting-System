import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ─── MongoDB Connection ───────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["evoting"]

# ─── Collections ─────────────────────────────────────────────────────────────
voters_col      = db["voters"]
candidates_col  = db["candidates"]
admin_col       = db["admin"]
schedule_col    = db["voting_schedule"]

# ─── Indexes (run once on startup) ───────────────────────────────────────────
def init_indexes():
    voters_col.create_index("cnic",  unique=True)
    voters_col.create_index("email", unique=True)
    print("[DB] Indexes ensured.")

# ─── Seed Admin (run once) ────────────────────────────────────────────────────
def seed_admin():
    import bcrypt
    username = os.getenv("ADMIN_USERNAME", "admin")
    raw_pw   = os.getenv("ADMIN_PASSWORD", "admin123")
    hashed   = bcrypt.hashpw(raw_pw.encode(), bcrypt.gensalt()).decode()

    existing = admin_col.find_one({"username": username})
    if not existing:
        admin_col.insert_one({
            "username": username,
            "password": hashed
        })
        print(f"[SEED] Admin '{username}' created.")
    else:
        print(f"[SEED] Admin '{username}' already exists — skipping.")