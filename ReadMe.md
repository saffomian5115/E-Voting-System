# E-Voting System

A fingerprint-based secure electronic voting system built with Flask and MongoDB.

**Stack:** Python · Flask · MongoDB · HTML/CSS/JS · SecuGen HU20

---

## Quick Start

```bash
cd Backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

Or just run `setup.bat` on Windows — it handles everything automatically.

> **Requires:** Python 3.10+, MongoDB 7.x (running locally), SecuGen FPWebHost on port 8443

Verify: `http://localhost:5000/api/ping` → `{"status":"ok"}`

---

## Project Structure

```
project/
├── Backend/
│   ├── app.py              # Flask entry point
│   ├── config.py           # DB connection & admin seed
│   ├── fingerprint.py      # SecuGen BWAPI integration
│   ├── requirements.txt
│   ├── setup.bat           # One-click Windows setup
│   └── routes/
│       ├── auth.py         # Register / Login / Profile
│       ├── fp.py           # Fingerprint capture & verify
│       ├── vote.py         # Cast vote
│       ├── result.py       # Results & stats
│       └── admin.py        # Admin panel API
└── Frontend/
    ├── index.html
    ├── register.html
    ├── login.html
    ├── vote.html
    ├── result.html
    ├── profile.html
    └── admin/
        ├── index.html      # Dashboard
        ├── candidates.html
        ├── voters.html
        └── schedule.html
```

---

## Features

| Feature | Detail |
|---|---|
| **Registration** | Name, CNIC, email, photo, fingerprint scan |
| **Login** | CNIC + fingerprint only — no password needed |
| **Voting** | Schedule-locked, double-vote prevented, GPS location recorded |
| **Results** | Live charts, turnout stats, winner highlight |
| **Admin Panel** | Manage candidates, voters, schedule; reset votes |
| **Fingerprint** | SecuGen HU20 via BWAPI — falls back to byte-similarity in dev |

---

## Environment Variables

Create `Backend/.env`:

```env
SECRET_KEY=your-secret-key
MONGO_URI=mongodb://localhost:27017/
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
BWAPI_URL=https://localhost:8443
BWAPI_ORIGIN=http://localhost:5000
FP_MATCH_THRESHOLD=40
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Register new voter |
| POST | `/api/login` | Login with CNIC + fingerprint |
| GET | `/api/me` | Current session info |
| GET | `/api/profile` | Full voter profile |
| POST | `/api/vote` | Cast vote |
| GET | `/api/vote/status` | Check eligibility |
| GET | `/api/results` | Live vote counts |
| GET | `/api/results/stats` | Turnout & breakdown |
| POST | `/api/fp/capture` | Capture fingerprint (proxy) |
| POST | `/api/fp/verify` | Verify fingerprint |
| POST | `/api/admin/login` | Admin login |
| GET | `/api/admin/stats` | Dashboard stats |
| GET/POST | `/api/admin/candidates` | List / add candidates |
| DELETE | `/api/admin/candidates/<id>` | Remove candidate |
| GET/POST | `/api/admin/schedule` | Get / set voting schedule |
| GET | `/api/admin/voters` | All registered voters |
| POST | `/api/admin/reset` | Reset all votes |

---

## Security

- Fingerprint verification required for both registration and login
- Passwords hashed with bcrypt (registration still accepts password for backup)
- Voting only possible within admin-set schedule window
- Server-side double-vote prevention — no client bypass possible
- Separate session scopes for voters and admin
- GPS location recorded per vote via OpenStreetMap Nominatim

---

## Default Admin

Username: `admin` · Password: `admin123`  
Change via `.env` before deployment.