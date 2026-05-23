# E-Voting System

Fingerprint-based secure electronic voting system.
**Stack:** Flask · MongoDB · HTML/CSS/JS · SecuGen HU20 · SGI BWAPI

---

## Module 1 — Setup (Quick Start)

### Prerequisites
| Tool | Version |
|------|---------|
| Python | 3.10+ |
| MongoDB | 7.x (local) |
| SecuGen FPWebHost | Latest (port 9734) |

### Steps

```bash
# 1. Backend folder mein jao
cd Backend

# 2. .env file check karo / edit karo
notepad .env

# 3. Setup run karo (Windows)
setup.bat

# 4. Ya manually:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 5. Server start karo
python app.py
```

### Verify karo
- Backend: http://localhost:5000/api/ping → `{"status":"ok"}`
- BWAPI:   http://localhost:9734 → SecuGen service response

---

## Folder Structure

```
project/
├── Backend/
│   ├── app.py              ← Flask entry point
│   ├── config.py           ← DB connection + seed
│   ├── fingerprint.py      ← FP engine (M2)
│   ├── .env                ← Secrets
│   ├── requirements.txt
│   ├── setup.bat           ← One-click setup (Windows)
│   ├── test_bwapi.py       ← BWAPI ping test
│   └── routes/
│       ├── auth.py         ← M3: register/login
│       ├── fp.py           ← M2: fingerprint verify
│       ├── vote.py         ← M5: cast vote
│       ├── result.py       ← M6: results/stats
│       └── admin.py        ← M4: admin panel
└── Frontend/
    └── admin/
```

---

