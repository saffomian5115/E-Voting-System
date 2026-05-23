import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    # ─── CORS (localhost only) ────────────────────────────────────────────────
    CORS(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",   # Live Server (VS Code)
        "http://127.0.0.1:5500",
    ])

    # ─── DB init ─────────────────────────────────────────────────────────────
    from config import init_indexes, seed_admin
    init_indexes()
    seed_admin()

    # ─── Blueprints ───────────────────────────────────────────────────────────
    from routes.auth   import auth_bp
    from routes.fp     import fp_bp
    from routes.vote   import vote_bp
    from routes.result import result_bp
    from routes.admin  import admin_bp

    app.register_blueprint(auth_bp,   url_prefix="/api")
    app.register_blueprint(fp_bp,     url_prefix="/api/fp")
    app.register_blueprint(vote_bp,   url_prefix="/api")
    app.register_blueprint(result_bp, url_prefix="/api")
    app.register_blueprint(admin_bp,  url_prefix="/api/admin")

    # ─── Health check ─────────────────────────────────────────────────────────
    @app.route("/api/ping")
    def ping():
        return {"status": "ok", "message": "E-Voting backend is running."}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)