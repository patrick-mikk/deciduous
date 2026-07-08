# Conventions

## Python

- Python **3.12.13** (matches cPanel). PEP 8, 4-space indent, type hints on public functions.
- Prefer small **pure functions**; keep network/DB I/O at the edges so the planner and
  parsers are unit-testable without external services.
- Data layer depends only on `requests` (or stdlib `urllib`) + `beautifulsoup4`/`lxml`.
  **No Selenium / headless browser** — see [ADR-0003](decisions/0003-no-selenium-http-data-layer.md).
- Pin dependencies in `backend/requirements.txt`; keep it installable on cPanel (no
  packages needing a compiler/Chrome).

## Configuration & secrets

- **Never commit secrets.** MySQL creds, Flask secret key, and encryption keys come from
  **environment variables** (cPanel env vars, or a `.env` outside `public_html`, git-ignored).
- No hard-coded session codes, URLs-with-keys, or absolute local paths in committed code.

## External APIs

- Treat TTB and the Academic Calendar as **undocumented public read-only** services:
  set a descriptive `User-Agent`, cache results, throttle bulk pulls, never write.
- Handle the TTB quirk: a **no-match search returns HTTP 404** with `payload: null` —
  map that to "empty result", not an exception.
- Fetch valid sessions/divisions from `/reference-data` at runtime, not from constants.

## Errors & logging

- Fail loudly in the data layer with actionable messages; degrade gracefully in the API
  (return a clean JSON error, don't 500 with a stack trace to the client).
- Log at WARNING+ by default; never log decrypted transcript data or secrets.

## Testing

- Unit tests must not hit the network. Live-service checks live in `backend/tests/*smoke*`
  and are run deliberately, not in the default unit run.
- Add a regression test with each bug fix.

## Docs

- Pointers over copies: reference `path:line`, don't paste code that will drift.
- A significant or hard-to-reverse decision gets an ADR ([decisions/](decisions/)).
- Update the affected doc in the same change that makes it stale.

## Git

- Feature branches off `main`; don't commit generated `dist/`, `__pycache__/`, `.env`,
  or local DB files (add to `.gitignore`).
