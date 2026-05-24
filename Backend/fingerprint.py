"""
fingerprint.py — Module 2: Fingerprint Engine
SecuGen HU20 + SgiBioSrv (HTTPS on port 8443)
"""

import base64, hmac, os, json, ssl, urllib.request, urllib.error
from typing import Optional
from config import voters_col

MATCH_THRESHOLD = int(os.getenv("FP_MATCH_THRESHOLD", "40"))
BWAPI_URL       = os.getenv("BWAPI_URL", "https://localhost:8443")
BWAPI_ORIGIN    = os.getenv("BWAPI_ORIGIN", "https://localhost:8443")


def _ssl_ctx():
    """Self-signed cert — skip verification."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def _bwapi_post(endpoint: str, payload: dict) -> Optional[dict]:
    """Generic HTTPS POST to SgiBioSrv. Returns parsed JSON or None."""
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url    = f"{BWAPI_URL}/{endpoint}",
        data   = data,
        method = "POST",
        headers= {
            "Content-Type": "application/json",
            "Origin"      : BWAPI_ORIGIN,
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=5, context=_ssl_ctx()) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError:
        return None
    except Exception as e:
        print(f"[FP] BWAPI post error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Template Storage
# ══════════════════════════════════════════════════════════════════════════════

def store_template(voter_id: str, base64_template: str) -> bool:
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
    try:
        _validate_b64(incoming_b64)
        _validate_b64(stored_b64)

        score = _bwapi_match(incoming_b64, stored_b64)

        if score is None:
            print("[FP] BWAPI unavailable — byte similarity fallback")
            score = _byte_similarity_score(incoming_b64, stored_b64)

        print(f"[FP] Score: {score} | Threshold: {threshold} | "
              f"{'MATCH' if score >= threshold else 'NO MATCH'}")

        return score >= threshold

    except Exception as e:
        print(f"[FP] match_template error: {e}")
        return False


def match_by_voter_id(voter_id: str, incoming_b64: str) -> bool:
    stored = get_template(voter_id)
    if not stored:
        print(f"[FP] No template found for voter {voter_id}")
        return False
    return match_template(incoming_b64, stored)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — BWAPI Calls
# ══════════════════════════════════════════════════════════════════════════════

def _bwapi_match(t1_b64: str, t2_b64: str) -> Optional[int]:
    """
    POST to /SGIMatchScore — returns 0-199 score or None if unavailable.
    """
    data = _bwapi_post("SGIMatchScore", {
        "Template1"     : t1_b64,
        "Template2"     : t2_b64,
        "TemplateFormat": "ISO",
    })

    if data is None:
        return None

    if data.get("ErrorCode", -1) != 0:
        print(f"[FP] SGIMatchScore ErrorCode: {data.get('ErrorCode')}")
        return None

    return int(data.get("MatchingScore", 0))


def _byte_similarity_score(t1_b64: str, t2_b64: str) -> int:
    """DEV ONLY — rough byte comparison fallback."""
    b1 = base64.b64decode(t1_b64)
    b2 = base64.b64decode(t2_b64)

    if hmac.compare_digest(b1, b2):
        return 100

    min_len     = min(len(b1), len(b2))
    max_len     = max(len(b1), len(b2))
    match_bytes = sum(1 for a, b in zip(b1[:min_len], b2[:min_len]) if a == b)
    return int((match_bytes / max_len) * 100)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _validate_b64(data: str) -> None:
    try:
        decoded = base64.b64decode(data, validate=True)
        if len(decoded) < 10:
            raise ValueError("Template too small")
    except Exception as e:
        raise ValueError(f"Invalid base64 fingerprint template: {e}")


def is_bwapi_alive() -> bool:
    """Ping SgiBioSrv — ErrorCode 0 or 54 both mean service is running."""
    data = _bwapi_post("SGIFPCapture", {
        "Timeout"       : 100,
        "TemplateFormat": "ISO",
    })
    if data is None:
        return False
    return data.get("ErrorCode") in [0, 54, 55, 59]