"""SQLAlchemy models for user accounts and their encrypted academic records.

Course/section/program *catalog* data is NOT modeled here — that's the
existing `SqliteCache` (`backend/data_sources/cache.py`), reused via
`backend.extensions.get_course_cache()`. This module only owns per-user state:
accounts, sessions, transcript entries, plans, and program enrolments.

Encrypted columns (`TranscriptEntry.grade`/`mark`, `PlanItem.notes`) store a
Fernet token string produced by `backend.security.crypto.encrypt_field`, never
plaintext — see ADR-0005 and `backend/security/crypto.py` for the key model.

All timestamps are stored as naive UTC `datetime`s (no tzinfo). SQLite doesn't
round-trip timezone-aware datetimes through `DateTime(timezone=True)`, so to
keep behaviour identical across the local SQLite fallback and MySQL, every
`datetime` in this module is naive-UTC by convention.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.extensions import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    """An account. `wrapped_data_key` is the Fernet key that encrypts this
    user's sensitive fields, itself encrypted with a password-derived key
    (see `backend/security/crypto.py`).

    Additional wraps of the SAME data key (each nullable, created lazily):
    - `server_wrapped_data_key` — wrapped with the server-side KEK derived
      from `DATA_KEY_PEPPER` (`crypto.server_wrap_data_key`). Written when the
      user registers their first passkey, because a passkey sign-in has no
      password to derive the KEK from (ADR-0006 documents the trade-off).
    - `recovery_wrapped_data_key` — wrapped with a KEK derived from the
      user's recovery code (`recovery_salt`), so a password reset with the
      code can re-wrap instead of losing data (`recovery_code_hash` verifies
      the code itself).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    pw_hash: Mapped[bytes] = mapped_column(LargeBinary(60), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    wrapped_data_key: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_code_hash: Mapped[bytes | None] = mapped_column(LargeBinary(60), nullable=True)
    recovery_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recovery_wrapped_data_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    server_wrapped_data_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Set when the user clicks the emailed verification link (backend/api/auth.py).
    verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(), nullable=True)

    # Profile (non-sensitive account data shown on Settings → Profile).
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_session: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "20269"
    expected_grad: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g. "2027-06"

    # Persistent (multi-process-safe) sign-in rate limiting.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime(), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    transcript_entries: Mapped[list["TranscriptEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    plans: Mapped[list["Plan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    program_enrolments: Mapped[list["ProgramEnrolment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    shares: Mapped[list["Share"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    passkeys: Mapped[list["PasskeyCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    """A signed-in session. The row is the source of truth for revocation
    (`revoked_at`) and expiry; the *unwrapped* per-user data key itself lives
    only in the client's signed session cookie (ADR-0005), never in this
    table."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > _utcnow()


class PasskeyCredential(Base):
    """A registered WebAuthn passkey (`backend/api/passkeys.py`).

    `credential_id` and `public_key` are stored base64url-encoded (the wire
    format the `webauthn` library and the browser both speak) rather than raw
    bytes, so no encode/decode round-trips through the DB driver are needed.
    The private key never leaves the user's authenticator; this row alone
    cannot sign anything.
    """

    __tablename__ = "passkey_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transports: Mapped[str | None] = mapped_column(String(255), nullable=True)  # comma-joined
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="Passkey")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="passkeys")


class TranscriptEntry(Base):
    """One transcript row (completed/in-progress/planned/extra course)."""

    __tablename__ = "transcript_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    term_session: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g. "20269"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    # completed | in_progress | planned | extra

    # Fernet tokens (backend.security.crypto.encrypt_field), not plaintext.
    grade_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    mark_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="transcript_entries")


class Plan(Base):
    """A term-by-term plan (a user may keep more than one, e.g. "what-if")."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="My Plan")
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="plans")
    items: Mapped[list["PlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.position"
    )


class PlanItem(Base):
    """One planned course placement within a `Plan`."""

    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False, index=True)
    course_code: Mapped[str] = mapped_column(String(20), nullable=False)
    term_session: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "20269"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Fernet token (backend.security.crypto.encrypt_field), not plaintext.
    notes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    plan: Mapped["Plan"] = relationship(back_populates="items")


class ProgramEnrolment(Base):
    """A program (specialist/major/minor) the user has declared or is targeting."""

    __tablename__ = "program_enrolments"
    __table_args__ = (UniqueConstraint("user_id", "program_code", name="uq_user_program"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    program_code: Mapped[str] = mapped_column(String(30), nullable=False)
    program_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_session: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # User-controlled "My programs" display/priority order (design/02-user-flows.md
    # "reorder priority"), same pattern as `PlanItem.position` above -- assigned on
    # insert (append-to-end) and rewritten wholesale by `PUT /api/me/programs/order`.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="program_enrolments")


class Share(Base):
    """A read-only public share link (`GET /api/share/:token`,
    `design/screens/05-transcript-settings-share.md`: "Shared plan").

    `token` is the primary key (an opaque URL-safe id, same shape as
    `Session.id`) -- there's no separate surrogate id because the token *is*
    the lookup key for the public, unauthenticated `GET /api/share/<token>`
    route. Revocation is a soft delete (`revoked_at`), same pattern as
    `Session.revoked_at`, so a stale link a student pasted somewhere fails
    closed rather than 404ing in a way that leaks "well it used to exist".

    Nothing here stores the owner's data key or any encrypted field directly:
    the public share view is built from plaintext-safe columns only (course
    code/credits/session/status, program codes) -- grades and marks stay
    inaccessible by construction, since the unwrapped Fernet data key only
    ever lives in the *owner's* signed session cookie (ADR-0005), never on
    this row or anywhere server-side.
    """

    __tablename__ = "shares"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # Whether the public view includes the read-only PlanBoard (course codes +
    # sessions + status only, never `PlanItem.notes_encrypted`) alongside the
    # always-included DegreeProgressCard/BreadthTracker/RequirementProgressList.
    include_plan: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="shares")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
