"""Pure-function degree-planning engine: validators, prerequisite/exclusion
satisfaction, and GPA/standing math for UofT Arts & Science.

Everything in this package is a pure function over plain dataclasses/dicts —
no I/O, no DB, no network. Callers (the Flask API layer) are responsible for
fetching Course/Program data and decrypted transcript rows and adapting them
into the shapes these functions expect (see `planner.types`).

Rules implemented here mirror `design/09-uoft-degree-rules.md` exactly; that
document is the source of truth if this code and it ever disagree.
"""

from __future__ import annotations
