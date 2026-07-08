"""Per-user field encryption at rest (ADR-0005: Fernet per-user encryption).

Design
------
Each user gets one random **data key** (a Fernet key) generated at signup.
Sensitive columns (`TranscriptEntry.grade`/`mark`, `PlanItem.notes`, ...) are
encrypted with that data key via `encrypt_field`/`decrypt_field`.

The data key itself is never stored in plaintext. It is **wrapped** (encrypted)
with a key-encryption-key (KEK) derived from the user's password (PBKDF2-HMAC
+ a per-user salt + a server-side pepper from the `DATA_KEY_PEPPER` env var)
and the wrapped bytes are what's persisted on `User.wrapped_data_key`.

At login, the plaintext password lets us re-derive the KEK and unwrap the data
key; the unwrapped key is held only in the signed session cookie for the
lifetime of that session (see `backend/api/auth.py`) — never written back to
the database. A DB dump alone can't decrypt transcripts; you'd also need a
live session or the user's password.

Consequence (documented in ADR-0005 and surfaced in the reset-password UI):
resetting a password without a recovery mechanism means the old data key
cannot be re-derived, so previously encrypted rows become unreadable. A
recovery-code flow is future work; `backend/api/auth.py`'s reset endpoint is a
stub that does not yet re-wrap the data key.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# NIST SP 800-132 recommends >= 210,000 iterations for PBKDF2-HMAC-SHA256 (2023+
# guidance); we're comfortably above that while staying fast enough for a login path.
PBKDF2_ITERATIONS = 390_000


def generate_salt() -> str:
    """A fresh per-user salt for KEK derivation, stored alongside the user (not secret)."""
    return base64.urlsafe_b64encode(os.urandom(16)).decode("ascii")


def generate_data_key() -> bytes:
    """A fresh random Fernet key — one per user, used to encrypt their sensitive fields."""
    return Fernet.generate_key()


def _derive_kek(password: str, salt_b64: str, pepper: str) -> bytes:
    """Derive a Fernet-compatible key-encryption-key from password + salt + server pepper.

    The pepper (`DATA_KEY_PEPPER`, an env var outside the webroot) means a
    stolen DB dump (which has the salt but not the pepper) is insufficient to
    brute-force the KEK offline from a guessed password alone.
    """
    salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    raw = kdf.derive(f"{password}\0{pepper}".encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def wrap_data_key(data_key: bytes, password: str, salt_b64: str, pepper: str) -> str:
    """Encrypt `data_key` with the password-derived KEK; returns a token string for storage."""
    kek = _derive_kek(password, salt_b64, pepper)
    return Fernet(kek).encrypt(data_key).decode("ascii")


def unwrap_data_key(wrapped: str, password: str, salt_b64: str, pepper: str) -> bytes | None:
    """Decrypt a wrapped data key; returns None if `password` is wrong (or data is corrupt)."""
    kek = _derive_kek(password, salt_b64, pepper)
    try:
        return Fernet(kek).decrypt(wrapped.encode("ascii"))
    except InvalidToken:
        return None


def encrypt_field(plaintext: str | None, data_key: bytes) -> str | None:
    """Encrypt one column value with a user's (already-unwrapped) data key."""
    if plaintext is None:
        return None
    return Fernet(data_key).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_field(token: str | None, data_key: bytes) -> str | None:
    """Decrypt one column value; returns None for a None/empty/corrupt token."""
    if not token:
        return None
    try:
        return Fernet(data_key).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None
