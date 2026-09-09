"""Normalizers that turn a UofT Academic History PDF (from ACORN) into a `StudentRecordDraft`.

See `backend/ingest/degree_explorer.py`. Everything here is pure (no I/O, no
DB, no Flask) so it's unit-testable with synthetic fixtures; `backend/api/
import_.py` is the only caller and owns persistence + auth.
"""

from __future__ import annotations
