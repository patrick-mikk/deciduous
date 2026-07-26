"""Outbound email over plain SMTP — stdlib only (`smtplib` + `email.message`).

Configured entirely from environment variables (see `backend/config_app.py`:
`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`MAIL_FROM`/...), which on
cPanel points at the site mailbox (e.g. `deciduous@mikkelsen.ca` via
`mail.mikkelsen.ca`). Port 465 speaks implicit SSL; anything else (587)
upgrades with STARTTLS. No Flask-Mail dependency — the need is one function.

Behaviour by mode
-----------------
- **TESTING** (`app.config["TESTING"]`): nothing is sent; messages append to
  the module-level `outbox` list so tests assert on real rendered content.
- **SMTP unconfigured** (no `SMTP_HOST`): `send_email` logs a warning and
  returns False. Callers treat email as best-effort — signup/reset flows
  still succeed; only the email doesn't go out. This keeps local dev working
  with zero mail setup.
- **Configured**: the message is handed to a daemon thread so the request
  isn't blocked on the SMTP round-trip (~0.5–2s to a cPanel relay). Failures
  are logged, never raised into the request.

Delivery is at-most-once and unacknowledged by design — anything critical
must also work without the email arriving (e.g. reset links can be re-requested).
"""

from __future__ import annotations

import smtplib
import threading
from email.message import EmailMessage
from email.utils import formataddr

from flask import Flask, current_app

#: TESTING-mode capture: list of `EmailMessage`s "sent" since process start.
outbox: list[EmailMessage] = []


def _build_message(cfg: dict, to: str, subject: str, text_body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((cfg["MAIL_FROM_NAME"], cfg["MAIL_FROM"]))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    return msg


def _deliver(cfg: dict, msg: EmailMessage, logger) -> None:
    """Blocking SMTP delivery. Runs on a daemon thread — must not touch Flask
    request/app context (everything needed is in the plain `cfg` dict)."""
    try:
        if int(cfg["SMTP_PORT"]) == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(cfg["SMTP_HOST"], int(cfg["SMTP_PORT"]), timeout=20)
        else:
            server = smtplib.SMTP(cfg["SMTP_HOST"], int(cfg["SMTP_PORT"]), timeout=20)
            server.starttls()
        with server:
            if cfg.get("SMTP_USER"):
                server.login(cfg["SMTP_USER"], cfg.get("SMTP_PASSWORD") or "")
            server.send_message(msg)
        logger.info("Sent email %r to %s", msg["Subject"], msg["To"])
    except Exception:  # noqa: BLE001 — best-effort: log, never crash the app
        logger.exception("Failed to send email %r to %s", msg["Subject"], msg["To"])


def send_email(to: str, subject: str, text_body: str, app: Flask | None = None) -> bool:
    """Queue one plain-text email. Returns True if it was queued (or captured
    in TESTING mode), False if SMTP isn't configured. Never raises."""
    app = app or current_app
    cfg = {
        "SMTP_HOST": app.config.get("SMTP_HOST"),
        "SMTP_PORT": app.config.get("SMTP_PORT", 465),
        "SMTP_USER": app.config.get("SMTP_USER"),
        "SMTP_PASSWORD": app.config.get("SMTP_PASSWORD"),
        "MAIL_FROM": app.config.get("MAIL_FROM") or app.config.get("SMTP_USER") or "",
        "MAIL_FROM_NAME": app.config.get("MAIL_FROM_NAME", "Deciduous"),
    }

    if app.config.get("TESTING"):
        outbox.append(_build_message(cfg, to, subject, text_body))
        return True

    if not cfg["SMTP_HOST"] or not cfg["MAIL_FROM"]:
        app.logger.warning(
            "SMTP not configured (SMTP_HOST/MAIL_FROM unset) — email %r to %s NOT sent.",
            subject,
            to,
        )
        return False

    msg = _build_message(cfg, to, subject, text_body)
    threading.Thread(target=_deliver, args=(cfg, msg, app.logger), daemon=True).start()
    return True
