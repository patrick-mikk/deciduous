"""Flask application factory.

`create_app()`:
1. Loads `.env` (`backend.config.load_env`) and resolves `Config` from the
   environment (`backend.config_app.Config`).
2. Wires up the SQLAlchemy engine/session (`backend.extensions.init_db`);
   auto-creates tables for the local SQLite dev fallback only (MySQL/ADR-0002
   is provisioned separately).
3. Auto-registers every `bp` Blueprint found in `backend/api/*.py` — see the
   contract documented in `backend/api/__init__.py`.
4. Installs same-origin-with-credentials CORS, a double-submit CSRF guard,
   the dev-only auto-login bypass (`backend.dev_auth` -- inert unless
   `FLASK_ENV=development` or `FLASK_SKIP_AUTH` is truthy, and never active in
   production), and JSON-only error handlers (never a stack trace to the
   client).

Run locally with `flask --app backend.app run` (from the repo root, with
`PYTHONUTF8=1` on Windows) or via `backend/passenger_wsgi.py` on cPanel.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import secrets
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException, NotFound

from backend.config import load_env
from backend.config_app import Config
from backend.dev_auth import register_dev_auth_bypass
from backend.extensions import create_all, init_db

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# /api/deploy/*: GitHub webhooks can't do the double-submit cookie dance;
# those routes authenticate with an HMAC signature / Bearer secret instead
# (backend/api/deploy.py) — strictly stronger than CSRF for a cookieless caller.
_CSRF_EXEMPT_PATHS = {"/api/auth/csrf", "/api/deploy/webhook", "/api/deploy/run"}

# `frontend/dist` is a filesystem concern of this entry point (where the
# built SPA lives on disk), not an app-behaviour setting, so it's read
# straight from `os.environ` here rather than added to `backend/config_app.py`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"


def create_app(config: Config | None = None) -> Flask:
    load_env()
    app = Flask(__name__)
    app.config.from_object(config or Config())

    init_db(app)
    if app.config.get("IS_SQLITE_FALLBACK"):
        create_all(app)

    registered = _register_blueprints(app)
    app.logger.info("Registered API blueprints: %s", ", ".join(registered) or "(none found)")

    _register_cors(app)
    _register_csrf_guard(app)
    register_dev_auth_bypass(app)
    _register_spa(app)
    _register_error_handlers(app)

    return app


# --------------------------------------------------------------- blueprints
def _register_blueprints(app: Flask) -> list[str]:
    """Import every `backend/api/<name>.py` module and register its `bp`
    Blueprint, if it defines one. See `backend/api/__init__.py` for the
    contract endpoint-adding agents follow -- no changes needed here to add
    a new resource module."""
    import backend.api as api_pkg

    registered: list[str] = []
    for module_info in pkgutil.iter_modules(api_pkg.__path__):
        name = module_info.name
        if module_info.ispkg or name.startswith("_"):
            continue
        module = importlib.import_module(f"backend.api.{name}")
        blueprint = getattr(module, "bp", None)
        if blueprint is not None:
            app.register_blueprint(blueprint)
            registered.append(blueprint.name)
    return registered


# ------------------------------------------------------------------- CORS
def _register_cors(app: Flask) -> None:
    """Same-origin-with-credentials CORS for the SPA (ADR-0004). Implemented
    directly (no flask-cors dependency) since there's exactly one allowed
    origin and it needs credentials support, which is a few lines either way.
    """
    origin = app.config["CORS_ORIGIN"]

    @app.before_request
    def _handle_preflight():
        if request.method == "OPTIONS":
            return app.make_default_options_response()
        return None

    @app.after_request
    def _add_cors_headers(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token"
        return response


# ------------------------------------------------------------------- CSRF
def _register_csrf_guard(app: Flask) -> None:
    """Double-submit CSRF check for every non-GET `/api/*` request. Endpoint
    modules don't opt in individually -- this is global so new blueprints get
    it for free. Get a token from `GET /api/auth/csrf` first."""

    @app.before_request
    def _enforce_csrf():
        if request.method in _SAFE_METHODS:
            return None
        if request.path in _CSRF_EXEMPT_PATHS or not request.path.startswith("/api/"):
            return None
        header = request.headers.get("X-CSRF-Token", "")
        cookie = request.cookies.get("csrf_token", "")
        if not header or not cookie or not secrets.compare_digest(header, cookie):
            return _json_error("Invalid or missing CSRF token.", 403)
        return None


# -------------------------------------------------------------------- SPA
def _register_spa(app: Flask) -> None:
    """Serve the built React SPA so one Flask process is the single origin
    cPanel's "Setup Python App" needs (no separate static vhost). `dist_dir`
    is a filesystem path this entry point cares about, not app behaviour, so
    it's read straight from `os.environ` rather than threaded through
    `backend/config_app.Config`.

    Only registered when a build is present at startup -- local API-only dev
    (no `frontend/dist` yet) keeps today's "nothing answers GET /" behaviour.
    """
    dist_dir = Path(os.environ.get("FRONTEND_DIST") or _DEFAULT_FRONTEND_DIST)
    if not dist_dir.is_dir():
        app.logger.info(
            "No frontend build at %s -- SPA serving disabled (API-only mode); "
            "set FRONTEND_DIST to override.",
            dist_dir,
        )
        return
    app.logger.info("Serving SPA from %s", dist_dir)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _serve_spa(path: str) -> Response:
        if path == "api" or path.startswith("api/"):
            # Unmatched /api/* -- shape it like the rest of the API instead
            # of falling through to the SPA's index.html.
            abort(404)

        try:
            response = send_from_directory(dist_dir, path or "index.html")
            served_exact_asset = bool(path)
        except NotFound:
            # Client-side route (e.g. /onboarding, /plan) -- let the SPA router handle it.
            response = send_from_directory(dist_dir, "index.html")
            served_exact_asset = False

        if served_exact_asset and path.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


# ---------------------------------------------------------- error handlers
def _json_error(message: str, status: int) -> Response:
    response = jsonify({"error": message})
    response.status_code = status
    return response


def _register_error_handlers(app: Flask) -> None:
    """Every error leaves this app as clean JSON -- never a stack trace
    (docs/conventions.md: "degrade gracefully in the API")."""

    @app.errorhandler(HTTPException)
    def _handle_http_exception(err: HTTPException):
        return _json_error(err.description or err.name or "Error", err.code or 500)

    @app.errorhandler(Exception)
    def _handle_unexpected_exception(err: Exception):
        app.logger.exception("Unhandled exception")
        return _json_error("Internal server error.", 500)
