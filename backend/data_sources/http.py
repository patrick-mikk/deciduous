"""Shared HTTP helper for the external data-source clients (TTB, Academic Calendar).

A single `requests.Session` with a descriptive User-Agent, small retry logic for
transient failures, and thin `get_html` / `get_json` / `post_json` wrappers that
encode the project-wide conventions:

- Treat TTB and the Academic Calendar as undocumented public read-only services
  (see docs/conventions.md): descriptive User-Agent, sane default timeout.
- TTB's "no results" quirk: a search with zero matches returns HTTP 404 with
  `payload: null` rather than an empty result. `get_json`/`post_json` surface
  that as `None` so callers can treat it as "empty result", not an exception.
- Retry only on connection errors / timeouts / 5xx - a 4xx (including the 404
  above) is a real, non-transient response and is returned/handled as-is.
"""

from __future__ import annotations

import html
import re
import time
from typing import Any

import requests

USER_AGENT = "uoft-degree-planner (+https://planner.mikkelsen.ca)"
DEFAULT_TIMEOUT = 30  # seconds
TTB_ORIGIN = "https://ttb.utoronto.ca"

_MAX_RETRIES = 2  # additional attempts after the first (3 tries total)
_BACKOFF_SECONDS = 0.5  # multiplied by attempt number for a small linear backoff

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def _request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """Perform an HTTP request with a small retry on connection errors / 5xx.

    4xx responses (including TTB's "no results" 404) are not retried - they are
    returned as-is for the caller to interpret.
    """
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    last_exc: requests.exceptions.RequestException | None = None
    response: requests.Response | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = SESSION.request(method, url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            response = None
        else:
            if response.status_code < 500:
                return response
            last_exc = None
        if attempt < _MAX_RETRIES:
            time.sleep(_BACKOFF_SECONDS * (attempt + 1))
    if response is not None:
        return response
    assert last_exc is not None  # only reachable via the exception branch
    raise last_exc


def get_html(url: str, params: dict[str, Any] | None = None) -> str:
    """GET a URL and return the response body as text. Raises on non-2xx status."""
    response = _request("GET", url, params=params)
    response.raise_for_status()
    return response.text


def get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """GET a URL and parse the JSON body.

    Returns None on HTTP 404 (TTB's "no results" quirk) instead of raising.
    """
    response = _request("GET", url, params=params, headers={"Accept": "application/json"})
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def post_json(
    url: str,
    json_body: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """POST a JSON body and parse the JSON response.

    Sends the headers TTB expects (Accept, Content-Type, Origin); merge in
    `extra_headers` on top if given. Returns None on HTTP 404 (TTB's "no
    results" quirk) instead of raising.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": TTB_ORIGIN,
    }
    if extra_headers:
        headers.update(extra_headers)
    response = _request("POST", url, json=json_body, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
# html.unescape() already turns entities like &nbsp; / &lsquo; / &rdquo; into
# their literal Unicode characters; normalize those specific characters here
# so downstream parsing (e.g. prerequisite text) can rely on plain ASCII.
# Keys are written as \u escapes (not literal glyphs) to avoid any source-file
# encoding ambiguity on Windows checkouts.
_CHAR_REPLACEMENTS = {
    " ": " ",  # non-breaking space
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark
    "“": '"',  # left double quotation mark
    "”": '"',  # right double quotation mark
}


def strip_html(text: str | None) -> str:
    """Strip HTML tags, decode entities, normalize whitespace/curly quotes.

    Returns "" for falsy input (None, "").
    """
    if not text:
        return ""
    without_tags = _TAG_RE.sub(" ", text)
    decoded = html.unescape(without_tags)
    for original, replacement in _CHAR_REPLACEMENTS.items():
        decoded = decoded.replace(original, replacement)
    return _WHITESPACE_RE.sub(" ", decoded).strip()
