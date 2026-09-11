"""Mailer delivery tests — the real SMTP path, with smtplib faked out.

The rest of the suite runs in TESTING mode, which short-circuits into
`mailer.outbox` before any delivery code runs, so nothing else exercises
`_deliver`. These pin the two properties production depends on:

- Delivery happens on the *calling* thread, before `send_email` returns. A
  background thread is killed with the worker under LiteSpeed's lswsgi (see the
  `backend/mailer.py` docstring), so "queued" was never the same as "sent".
- TLS is verified. smtplib's default context skips certificate checks, and this
  connection carries the mailbox password.
"""

from __future__ import annotations

import smtplib
import ssl
import sys
import threading
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402
from flask import Flask  # noqa: E402

from backend import mailer  # noqa: E402


class _FakeSMTP:
    """Stands in for smtplib.SMTP / SMTP_SSL and records what the mailer did."""

    instances: list[_FakeSMTP] = []
    fail_login = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.context = context
        self.sent: list = []
        self.sent_on_calling_thread: bool | None = None
        self.closed = False
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False

    def starttls(self, context=None):
        self.context = context

    def login(self, user, password):
        if _FakeSMTP.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    def send_message(self, msg):
        self.sent.append(msg)
        self.sent_on_calling_thread = threading.current_thread() is threading.main_thread()


@pytest.fixture()
def fake_smtp(monkeypatch):
    _FakeSMTP.instances.clear()
    _FakeSMTP.fail_login = False
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)
    return _FakeSMTP


def _app(port: int = 465) -> Flask:
    app = Flask(__name__)
    app.config.update(
        TESTING=False,
        SMTP_HOST="mail.example.test",
        SMTP_PORT=port,
        SMTP_USER="bot@example.test",
        SMTP_PASSWORD="pw",
        MAIL_FROM="bot@example.test",
        MAIL_FROM_NAME="Deciduous",
    )
    return app


def test_delivers_before_returning_on_the_calling_thread(fake_smtp):
    assert mailer.send_email("a@example.test", "Hi", "body", app=_app()) is True
    assert len(fake_smtp.instances) == 1, "send_email returned before connecting to the relay"
    server = fake_smtp.instances[0]
    assert len(server.sent) == 1
    assert server.sent_on_calling_thread is True


@pytest.mark.parametrize("port", [465, 587])
def test_tls_is_verified_on_both_paths(fake_smtp, port):
    mailer.send_email("a@example.test", "Hi", "body", app=_app(port))
    ctx = fake_smtp.instances[-1].context
    assert ctx is not None, "no SSL context passed; smtplib's default skips certificate checks"
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_delivery_failure_returns_false_and_does_not_raise(fake_smtp):
    fake_smtp.fail_login = True
    assert mailer.send_email("a@example.test", "Hi", "body", app=_app()) is False
    assert fake_smtp.instances[-1].closed, "socket left open on the failure path"


def test_unconfigured_smtp_is_a_logged_no_op(fake_smtp):
    app = _app()
    app.config["SMTP_HOST"] = None
    assert mailer.send_email("a@example.test", "Hi", "body", app=app) is False
    assert fake_smtp.instances == []
