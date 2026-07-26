"""Passkey (WebAuthn) blueprint: register, list, delete, and sign in.

Flow
----
Registration (signed-in users only):
    POST /api/auth/passkeys/register/options  -> creation options (challenge
        stashed in the signed cookie session)
    POST /api/auth/passkeys/register/verify   -> verifies the attestation,
        stores a `PasskeyCredential` row, and (first passkey only) writes
        `User.server_wrapped_data_key` so future passkey sign-ins can unlock
        encrypted fields without a password (ADR-0006).

Sign-in (no prior auth; discoverable/resident credentials):
    POST /api/auth/passkeys/authenticate/options -> request options with an
        empty allowCredentials list, so the browser offers whatever passkeys
        it holds for this RP ID.
    POST /api/auth/passkeys/authenticate/verify  -> verifies the assertion,
        unwraps the data key from `server_wrapped_data_key`, and starts a
        session exactly like a password signin (honouring `rememberMe`).

Key model note (ADR-0006): a WebAuthn assertion proves possession of the
authenticator but carries no secret to derive the per-user KEK from, so
passkey users get an additional wrap of their data key under a KEK derived
from the server-side `DATA_KEY_PEPPER`. A DB dump alone still can't unwrap it;
the trade-off (a fully-compromised server could) applies only to accounts
that registered a passkey.

CSRF: these are all POST /api/* routes, so the global double-submit guard in
`backend.app` applies — the SPA fetches `GET /api/auth/csrf` first, same as
for password signin.
"""

from __future__ import annotations

import datetime as dt
import json

from flask import Blueprint, current_app, jsonify, request, session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from backend.api import current_data_key, current_user, db_session, json_error, require_auth
from backend.api.auth import _start_session
from backend.models_db import PasskeyCredential, User
from backend.security.crypto import server_unwrap_data_key, server_wrap_data_key

bp = Blueprint("passkeys", __name__, url_prefix="/api/auth/passkeys")

_REG_CHALLENGE_KEY = "passkey_reg_challenge"
_AUTH_CHALLENGE_KEY = "passkey_auth_challenge"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _rp() -> tuple[str, str, str]:
    cfg = current_app.config
    return cfg["PASSKEY_RP_ID"], cfg["PASSKEY_RP_NAME"], cfg["PASSKEY_ORIGIN"]


def _options_response(options) -> tuple:
    """`options_to_json` produces the exact wire JSON the browser API expects
    (base64url-encoded buffers) — round-trip through `json.loads` so Flask
    serves it as a JSON object, not a double-encoded string."""
    return jsonify(json.loads(options_to_json(options)))


def _credential_public(row: PasskeyCredential) -> dict:
    return {
        "id": row.id,
        "label": row.label,
        "createdAt": row.created_at.isoformat() + "Z",
        "lastUsedAt": row.last_used_at.isoformat() + "Z" if row.last_used_at else None,
    }


# ------------------------------------------------------------- registration
@bp.route("/register/options", methods=["POST"])
@require_auth
def register_options():
    db = db_session()
    user = current_user()
    rp_id, rp_name, _origin = _rp()

    existing = db.query(PasskeyCredential).filter_by(user_id=user.id).all()
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=str(user.id).encode("utf-8"),
        user_name=user.email,
        user_display_name=user.display_name or user.email,
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing
        ],
        authenticator_selection=AuthenticatorSelectionCriteria(
            # Resident (discoverable) credentials, so sign-in needs no email
            # prompt first; user verification preferred, not required, to keep
            # older security keys usable.
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    session[_REG_CHALLENGE_KEY] = bytes_to_base64url(options.challenge)
    return _options_response(options)


@bp.route("/register/verify", methods=["POST"])
@require_auth
def register_verify():
    data = request.get_json(silent=True) or {}
    credential = data.get("credential")
    label = (data.get("label") or "").strip()[:120] or "Passkey"

    challenge_b64 = session.pop(_REG_CHALLENGE_KEY, None)
    if not challenge_b64:
        return json_error("No registration in progress — request options first.", 400)
    if not credential:
        return json_error("Missing credential.", 422)

    data_key = current_data_key()
    if data_key is None:
        return json_error("Session is missing its data key — sign in again.", 401)

    rp_id, _rp_name, origin = _rp()
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=rp_id,
            expected_origin=origin,
        )
    except InvalidRegistrationResponse:
        return json_error("Passkey registration could not be verified.", 400)

    db = db_session()
    user = current_user()
    credential_id = bytes_to_base64url(verified.credential_id)
    if db.query(PasskeyCredential).filter_by(credential_id=credential_id).first() is not None:
        return json_error("That passkey is already registered.", 409)

    transports = data.get("transports")
    row = PasskeyCredential(
        user_id=user.id,
        credential_id=credential_id,
        public_key=bytes_to_base64url(verified.credential_public_key),
        sign_count=verified.sign_count,
        transports=",".join(transports)[:255] if isinstance(transports, list) else None,
        label=label,
    )
    db.add(row)

    # First passkey: store the server-wrapped copy of the data key that a
    # passwordless sign-in will unwrap (ADR-0006). The live session always
    # holds the unwrapped key at this point.
    if not user.server_wrapped_data_key:
        user.server_wrapped_data_key = server_wrap_data_key(
            data_key, current_app.config["DATA_KEY_PEPPER"]
        )
    db.commit()
    return jsonify({"passkey": _credential_public(row)}), 201


# -------------------------------------------------------------- management
@bp.route("", methods=["GET"])
@require_auth
def list_passkeys():
    db = db_session()
    user = current_user()
    rows = (
        db.query(PasskeyCredential)
        .filter_by(user_id=user.id)
        .order_by(PasskeyCredential.created_at.desc())
        .all()
    )
    return jsonify({"passkeys": [_credential_public(r) for r in rows]})


@bp.route("/<int:passkey_id>", methods=["DELETE"])
@require_auth
def delete_passkey(passkey_id: int):
    db = db_session()
    user = current_user()
    row = db.get(PasskeyCredential, passkey_id)
    if row is None or row.user_id != user.id:
        return json_error("No such passkey.", 404)
    db.delete(row)

    # Last passkey removed: drop the server-wrapped key too, restoring the
    # stricter password-only key model for this account.
    remaining = (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.user_id == user.id, PasskeyCredential.id != passkey_id)
        .count()
    )
    if remaining == 0:
        user.server_wrapped_data_key = None
    db.commit()
    return jsonify({"ok": True})


# ------------------------------------------------------------------ signin
@bp.route("/authenticate/options", methods=["POST"])
def authenticate_options():
    rp_id, _rp_name, _origin = _rp()
    options = generate_authentication_options(
        rp_id=rp_id,
        # Empty allowCredentials => the browser offers any discoverable
        # passkey it holds for this RP (usernameless sign-in).
        allow_credentials=[],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    session[_AUTH_CHALLENGE_KEY] = bytes_to_base64url(options.challenge)
    return _options_response(options)


@bp.route("/authenticate/verify", methods=["POST"])
def authenticate_verify():
    data = request.get_json(silent=True) or {}
    credential = data.get("credential")

    challenge_b64 = session.pop(_AUTH_CHALLENGE_KEY, None)
    if not challenge_b64:
        return json_error("No sign-in in progress — request options first.", 400)
    if not credential or not isinstance(credential, dict) or not credential.get("rawId"):
        return json_error("Missing credential.", 422)

    generic_error = "Passkey sign-in failed."
    db = db_session()
    row = db.query(PasskeyCredential).filter_by(credential_id=credential["rawId"]).first()
    if row is None:
        return json_error(generic_error, 401)

    rp_id, _rp_name, origin = _rp()
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=base64url_to_bytes(row.public_key),
            credential_current_sign_count=row.sign_count,
            require_user_verification=False,
        )
    except InvalidAuthenticationResponse:
        return json_error(generic_error, 401)

    user = db.get(User, row.user_id)
    if user is None or not user.server_wrapped_data_key:
        return json_error(generic_error, 401)

    data_key = server_unwrap_data_key(
        user.server_wrapped_data_key, current_app.config["DATA_KEY_PEPPER"]
    )
    if data_key is None:
        current_app.logger.error(
            "server_wrapped_data_key for user %s failed to unwrap — DATA_KEY_PEPPER changed?",
            user.id,
        )
        return json_error(generic_error, 401)

    row.sign_count = verified.new_sign_count
    row.last_used_at = _now()
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    _start_session(user, data_key, remember=bool(data.get("rememberMe")))
    return jsonify({"user": {"id": user.id, "email": user.email}})
