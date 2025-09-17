from pathlib import Path
from flask import Flask
from .helpers import secure_headers, add_noindex_header
from .routes import bp as main_bp

def create_app():
    app = Flask(__name__)

    # TEMP: dev secret (replace with env var on the Pi)
    app.secret_key = "dev-woofdog-secret-12345"

    # blueprints
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_asset_ver():
        try:
            css = Path(app.static_folder) / "style.css"
            ver = int(css.stat().st_mtime)
        except Exception:
            ver = 0
        return {"ASSET_VER": ver}

    # security headers
    app.after_request(secure_headers)
    app.after_request(add_noindex_header)
    # client side cache
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 7  # 7 days

    return app

# optional: allow `flask --app woof_site run` in dev
app = create_app()