"""
fingerprint.py — Module 2: Fingerprint Engine
SecuGen HU20 + SGI BWAPI based fingerprint matching

Architecture:
  - Templates ISO 19794-2 format mein store hote hain (base64 encoded)
  - Matching server-side hoti hai — client pe KABHI nahi
  - Score threshold: 40+ = match (configurable)
"""

import base64
import hashlib
import hmac
import os
from typing import Optional
from config import voters_col

# ─── Constants ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD = int(os.getenv("FP_MATCH_THRESHOLD", "40"))
BWAPI_URL       = os.getenv("BWAPI_URL", "http://localhost:9734")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Template Storage
# ══════════════════════════════════════════════════════════════════════════════

def store_template(voter_id: str, base64_template: str) -> bool:
    """
    Voter ka fingerprint template MongoDB mein store karo.

    Args:
        voter_id       : voter ka _id (string)
        base64_template: ISO template, base64 encoded

    Returns:
        True  — successfully stored
        False — kuch error aaya
    """
    try:
        _validate_b64(base64_template)

        from bson import ObjectId
        result = voters_col.update_one(
            {"_id": ObjectId(voter_id)},
            {"$set": {"fp_template": base64_template}}
        )
        return result.modified_count > 0

    except Exception as e:
        print(f"[FP] store_template error: {e}")
        return False


def get_template(voter_id: str) -> Optional[str]:
    """
    DB se voter ka stored template nikalo.

    Returns:
        base64 string ya None
    """
    try:
        from bson import ObjectId
        voter = voters_col.find_one(
            {"_id": ObjectId(voter_id)},
            {"fp_template": 1}
        )
        return voter.get("fp_template") if voter else None
    except Exception as e:
        print(f"[FP] get_template error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Template Matching
# ══════════════════════════════════════════════════════════════════════════════

def match_template(incoming_b64: str, stored_b64: str,
                   threshold: int = MATCH_THRESHOLD) -> bool:
    """
    Do fingerprint templates match karte hain ya nahi.

    Priority:
      1. SecuGen BWAPI server available hai → SDK matching (accurate)
      2. Fallback → byte-similarity score (demo/dev mode)

    Args:
        incoming_b64: naya scan, base64
        stored_b64  : DB mein stored template, base64
        threshold   : minimum score for match (default 40)

    Returns:
        True  — match confirmed
        False — no match
    """
    try:
        _validate_b64(incoming_b64)
        _validate_b64(stored_b64)

        # Try BWAPI SDK match first
        score = _bwapi_match(incoming_b64, stored_b64)

        if score is None:
            # Fallback: byte similarity (dev/demo only)
            print("[FP] BWAPI unavailable — byte similarity fallback use ho raha hai")
            score = _byte_similarity_score(incoming_b64, stored_b64)

        print(f"[FP] Match score: {score} | Threshold: {threshold} | "
              f"Result: {'MATCH' if score >= threshold else 'NO MATCH'}")

        return score >= threshold

    except Exception as e:
        print(f"[FP] match_template error: {e}")
        return False


def match_by_voter_id(voter_id: str, incoming_b64: str) -> bool:
    """
    Convenience: voter ID se stored template fetch karo aur match karo.

    Args:
        voter_id    : MongoDB voter _id
        incoming_b64: naya fingerprint scan, base64

    Returns:
        True = verified, False = mismatch ya error
    """
    stored = get_template(voter_id)
    if not stored:
        print(f"[FP] Voter {voter_id} ka template DB mein nahi mila")
        return False
    return match_template(incoming_b64, stored)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — BWAPI Integration (SecuGen SDK)
# ══════════════════════════════════════════════════════════════════════════════

def _bwapi_match(t1_b64: str, t2_b64: str) -> Optional[int]:
    """
    SecuGen BWAPI /SGIFPCapture/MatchScore endpoint call karo.

    BWAPI local service (FPWebHost.exe) port 9734 pe hoti hai.
    Ye endpoint do templates leta hai aur match score return karta hai.

    Returns:
        int score (0-200) ya None agar BWAPI unavailable ho
    """
    import urllib.request
    import urllib.error
    import json

    payload = json.dumps({
        "Template1": t1_b64,
        "Template2": t2_b64
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url    = f"{BWAPI_URL}/SGIFPCapture/MatchScore",
            data   = payload,
            method = "POST",
            headers= {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data  = json.loads(resp.read().decode())
            score = int(data.get("MatchingScore", 0))
            return score

    except urllib.error.URLError:
        # BWAPI chal nahi rahi — fallback pe chale jaenge
        return None
    except Exception as e:
        print(f"[FP] BWAPI match error: {e}")
        return None


def _byte_similarity_score(t1_b64: str, t2_b64: str) -> int:
    """
    DEV/DEMO ONLY — PRODUCTION MEIN USE MAT KARO.

    Byte-level comparison se ek rough similarity score nikalta hai.
    Sirf tab use hota hai jab BWAPI available na ho.

    Real hardware pe hamesha _bwapi_match use hoti hai.

    Score range: 0–100
    """
    b1 = base64.b64decode(t1_b64)
    b2 = base64.b64decode(t2_b64)

    # Same template = instant 100
    if hmac.compare_digest(b1, b2):
        return 100

    # Shorter length tak compare karo
    min_len     = min(len(b1), len(b2))
    max_len     = max(len(b1), len(b2))
    match_bytes = sum(1 for a, b in zip(b1[:min_len], b2[:min_len]) if a == b)

    raw_score   = (match_bytes / max_len) * 100
    return int(raw_score)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _validate_b64(data: str) -> None:
    """Base64 valid hai ya nahi — exception raise karo agar nahi."""
    try:
        decoded = base64.b64decode(data, validate=True)
        if len(decoded) < 10:
            raise ValueError("Template bohot chota hai — valid fingerprint template nahi lagta")
    except Exception as e:
        raise ValueError(f"Invalid base64 fingerprint template: {e}")


def is_bwapi_alive() -> bool:
    """BWAPI service ping karo — True agar available ho."""
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen(BWAPI_URL, timeout=2)
        return True
    except:
        return False