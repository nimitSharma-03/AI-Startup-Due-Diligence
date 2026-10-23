"""AI Startup Due Diligence Platform - Flask application factory."""

from __future__ import annotations

import logging
import secrets
import time
from pathlib import Path

from flask import Flask, g, request, send_from_directory
from flask_cors import CORS

from diligence.config import Config
from diligence.errors import register_error_handlers

LOGGER = logging.getLogger("diligence")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    "frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
)


def create_app(config: Config | None = None) -> Flask:
    config = config or Config()
    logging.basicConfig(level=config.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    # Imported here so configuration and logging are in place first.
    from diligence.api import api
    from diligence.data.store import DatasetStore
    from diligence.insights import ReferenceStats
    from diligence.ml.model import ModelService

    app = Flask(__name__, static_folder=None)
    app.config.update(
        MAX_CONTENT_LENGTH=config.max_content_length,
        JSON_SORT_KEYS=False,
        DILIGENCE=config,
    )
    app.json.sort_keys = False

    model = ModelService(config.model_dir)
    store = DatasetStore(model, config.reference_csv, config.upload_ttl_seconds, config.max_uploads)
    stats = ReferenceStats(store.reference, model.classes)
    app.extensions["diligence"] = {"model": model, "store": store, "stats": stats}
    LOGGER.info("Loaded model %s and %d reference startups", model.metadata["trained_at"], len(store.reference.records))

    if config.cors_origins:
        CORS(app, resources={r"/api/*": {"origins": config.cors_origins}}, expose_headers=["Content-Disposition"])

    register_error_handlers(app)
    app.register_blueprint(api)

    @app.before_request
    def _start() -> None:
        g.request_id = request.headers.get("X-Request-ID", "")[:64] or secrets.token_hex(8)
        g.started = time.perf_counter()

    @app.after_request
    def _finish(response):
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", CSP)
        if request.path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")
            elapsed = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
            LOGGER.info("%s %s %s %.0fms id=%s", request.method, request.path, response.status_code, elapsed, g.get("request_id"))
        return response

    register_frontend(app, config.frontend_dist)
    return app


def register_frontend(app: Flask, dist: Path) -> None:
    """Serve the built React app and fall back to index.html for client routes."""

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if path.startswith("api/") or path == "api":
            from diligence.errors import error_response

            return error_response(404, "not_found", "Unknown API endpoint.")
        index = dist / "index.html"
        if not index.is_file():
            return {"service": "AI Startup Due Diligence API", "docs": "/api/health"}, 200
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            response = send_from_directory(dist, path)
            if path.startswith("assets/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return response
        response = send_from_directory(dist, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response
