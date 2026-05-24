import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(
        __name__,
        static_folder  = os.path.join(os.path.dirname(__file__), "../Frontend"),
        static_url_path= "/static"
    )
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS(app, supports_credentials=True, origins=[
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ])

    # ─── DB init ──────────────────────────────────────────────────────────────
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

    # ─── Frontend routes ──────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:filename>")
    def frontend(filename):
        # API routes already handled above — only serve static files here
        if filename.startswith("api/"):
            from flask import abort
            abort(404)
        try:
            return send_from_directory(app.static_folder, filename)
        except:
            # fallback to index.html for SPA routing
            return send_from_directory(app.static_folder, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)