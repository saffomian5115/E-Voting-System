"""
test_bwapi.py — SGI BWAPI local service test
Run: python test_bwapi.py
Expected: SecuGen FPWebHost running on port 9734
"""
import urllib.request
import urllib.error

BWAPI_URL = "http://localhost:9734"

def test_bwapi():
    print(f"[TEST] SGI BWAPI ko ping kar raha hoon: {BWAPI_URL}")
    try:
        req = urllib.request.urlopen(BWAPI_URL, timeout=3)
        print(f"[OK]   Status: {req.status} — BWAPI service chal raha hai!")
        return True
    except urllib.error.URLError as e:
        print(f"[FAIL] BWAPI connect nahi hua: {e.reason}")
        print("       → Check karein: SecuGen FPWebHost.exe chal raha hai?")
        print("       → Default port 9734 pe listen ho raha hai?")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected: {e}")
        return False

if __name__ == "__main__":
    test_bwapi()