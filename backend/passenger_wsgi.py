"""cPanel Passenger WSGI entry point ("Setup Python App" looks for `application`
in this file). All real setup lives in `backend.app.create_app` -- keep this
file minimal.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app import create_app  # noqa: E402

application = create_app()
