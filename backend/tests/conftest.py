"""Shared test helpers: locate the fixtures directory."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    """Return the text content of a fixture file under backend/tests/fixtures."""
    return (FIXTURES / name).read_text(encoding="utf-8")
