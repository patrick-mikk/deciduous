"""Minimal environment/config loading (no external dependency).

Secrets (e.g. GEMINI_API_KEY) live in a git-ignored `.env` at the repo root, or
in real environment variables (cPanel sets these in its UI). `load_env()` reads
`.env` and populates `os.environ` WITHOUT overriding variables already set — so a
real exported env var always wins over the file.

Call `load_env()` once at process startup (the TUI's `main()` and the LLM batch
runner do). It is intentionally NOT called inside library constructors, so unit
tests keep a clean environment.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_loaded = False


def load_env(path: str | Path | None = None, *, force: bool = False) -> None:
    """Load KEY=VALUE lines from `.env` into os.environ (idempotent).

    Existing environment variables are preserved (`setdefault` semantics).
    """
    global _loaded
    if _loaded and not force:
        return
    env_path = Path(path) if path is not None else _REPO_ROOT / ".env"
    _loaded = True
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
