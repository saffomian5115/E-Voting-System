import urllib.request, json, ssl

BWAPI_URL = "https://localhost:8443"

def test_bwapi():
    print(f"[TEST] Pinging SgiBioSrv: {BWAPI_URL}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    payload = json.dumps({
        "Timeout": 100, "TemplateFormat": "ISO"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url    = f"{BWAPI_URL}/SGIFPCapture",
            data   = payload,
            method = "POST",
            headers= {
                "Content-Type": "application/json",
                "Origin"      : "https://localhost:8443",
            }
        )
        with urllib.request.urlopen(req, timeout=3, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            code = data.get("ErrorCode")
            # 54=timeout/no finger, 55=device not found, 0=success
            if code in [0, 54]:
                print(f"[OK]   SgiBioSrv alive! ErrorCode={code} (0=captured, 54=no finger placed)")
            elif code == 55:
                print(f"[WARN] SgiBioSrv running but device not connected (ErrorCode=55)")
            else:
                print(f"[INFO] SgiBioSrv responded with ErrorCode={code}")
            return True

    except Exception as e:
        print(f"[FAIL] {e}")
        return False

if __name__ == "__main__":
    test_bwapi()