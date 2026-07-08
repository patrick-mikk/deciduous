"""Liveness check. Also doubles as the reference example of the `bp` contract
(see `backend/api/__init__.py`) — no auth, no DB, just proves the app booted.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})
