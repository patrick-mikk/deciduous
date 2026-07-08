# 0001. Flask (not FastAPI) for the backend

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The app is hosted on cPanel via "Setup Python App", which runs Python under
**Passenger WSGI**. FastAPI is ASGI and needs an ASGI server (uvicorn) or an
adapter to run under Passenger — extra moving parts on shared hosting we don't control.

## Decision

Use **Flask** (WSGI) with a `passenger_wsgi.py` exposing `application`.

## Consequences

- Runs natively on cPanel Passenger with no adapter.
- Lose FastAPI's async and automatic OpenAPI/validation; acceptable — our workload is
  cache-backed and modest, and we can add `pydantic`/marshmallow for validation if needed.
- Reversing means introducing an ASGI stack and confirming cPanel can run it.
