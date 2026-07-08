"""UofT Timetable Builder (TTB) client.

See backend/docs/TTB_API_REFERENCE.md for the API contract and
backend/data_sources/timetable/client.py for the implementation.
"""

from backend.data_sources.timetable.client import TTBClient, normalize_course

__all__ = ["TTBClient", "normalize_course"]
