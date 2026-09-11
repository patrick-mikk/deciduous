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
- **Configured**: delivered *synchronously*, inside the request, over
  verified TLS. Failures are logged and reported as False, never raised into
  the request.

Why not a background thread: this used to hand the message to a
`threading.Thread(daemon=True)` so the request wouldn't wait on SMTP. Under
LiteSpeed's `lswsgi` (the production host) the worker is reaped as soon as the
response is written, and a daemon thread is killed with it — the same mechanism
that silently broke the deploy webhook while it returned 202
(docs/auto-deploy.md, "Why the webhook alone isn't enough"). The relay is on the
same host, so the wait is short; `_SMTP_TIMEOUT` bounds the worst case.

Delivery is at-most-once and unacknowledged by design — anything critical
must also work without the email arriving (e.g. reset links can be re-requested).
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from flask import Flask, current_app

#: TESTING-mode capture: list of `EmailMessage`s "sent" since process start.
outbox: list[EmailMessage] = []

#: Seconds before giving up on the relay. Delivery now blocks the request, so
#: this is the ceiling on how long a stalled mail server can hold up a signup.
_SMTP_TIMEOUT = 10


def _build_message(cfg: dict, to: str, subject: str, text_body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((cfg["MAIL_FROM_NAME"], cfg["MAIL_FROM"]))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    return msg


def _deliver(cfg: dict, msg: EmailMessage, logger) -> bool:
    """Blocking SMTP delivery; True if the relay accepted the message.

    TLS is verified against the system CA store. smtplib's own default context
    does *not* check the certificate, and this connection carries the mailbox
    password — so pass an explicit `ssl.create_default_context()` on both the
    implicit-SSL (465) and STARTTLS paths.
    """
    host, port = cfg["SMTP_HOST"], int(cfg["SMTP_PORT"])
    context = ssl.create_default_context()
    try:
        if port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=_SMTP_TIMEOUT, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT)
        with server:  # closes the socket even if STARTTLS or login fails
            if port != 465:
                server.starttls(context=context)
            if cfg.get("SMTP_USER"):
                server.login(cfg["SMTP_USER"], cfg.get("SMTP_PASSWORD") or "")
            server.send_message(msg)
        logger.info("Sent email %r to %s", msg["Subject"], msg["To"])
        return True
    except Exception:  # noqa: BLE001 — best-effort: log, never crash the app
        logger.exception("Failed to send email %r to %s", msg["Subject"], msg["To"])
        return False


def send_email(to: str, subject: str, text_body: str, app: Flask | None = None) -> bool:
    """Send one plain-text email. Returns True if the relay accepted it (or it
    was captured in TESTING mode); False if SMTP isn't configured or delivery
    failed. Never raises."""
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

    return _deliver(cfg, _build_message(cfg, to, subject, text_body), app.logger)
