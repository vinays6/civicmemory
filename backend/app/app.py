from pathlib import Path

from flask import Flask
from dotenv import load_dotenv

from db import init_db


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

from app.routes.api import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    init_db()
    app.register_blueprint(api_bp)

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app
