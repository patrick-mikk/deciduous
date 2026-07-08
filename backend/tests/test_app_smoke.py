"""Smoke test: the app factory builds and /api/health responds. Uses an
isolated in-memory SQLite DB (never the dev fallback file, never MySQL) so
this test has no side effects and doesn't touch the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402


class _TestConfig(Config):
    def __init__(self) -> None:
        super().__init__()
        self.SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory, isolated per engine
        self.IS_SQLITE_FALLBACK = True
        self.TESTING = True
        self.SECRET_KEY = "test-secret-key"
        self.DATA_KEY_PEPPER = "test-pepper"
        self.SESSION_COOKIE_SECURE = False


@pytest.fixture()
def app():
    return create_app(config=_TestConfig())


@pytest.fixture()
def client(app):
    return app.test_client()


def test_create_app_builds(app):
    assert app is not None
    assert app.config["TESTING"] is True


def test_health_endpoint_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_auth_blueprint_auto_registered(app):
    # backend/api/auth.py defines `bp` -- create_app must have discovered and
    # registered it without any explicit wiring in backend/app.py.
    rules = {str(rule) for rule in app.url_map.iter_rules()}
    assert "/api/auth/signin" in rules
    assert "/api/auth/signup" in rules


def test_unknown_route_returns_json_error(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.get_json()
