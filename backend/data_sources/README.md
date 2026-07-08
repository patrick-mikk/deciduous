# backend/data_sources

Shared foundation imported by the three external data-source clients (TTB
timetable, Academic Calendar course pages, Academic Calendar program pages).
Client modules import from here instead of redefining HTTP or model logic.

## Modules

- **`http.py`** — one shared `requests.Session` with a descriptive
  `User-Agent` and a sane default timeout. Exposes `get_html`, `get_json`,
  `post_json` (all with 2-retry backoff on connection errors / 5xx only —
  4xx, including TTB's "no results" 404, is returned as `None`/raised
  as-is, never retried), and `strip_html` for cleaning calendar HTML
  fragments (tags, entities incl. `&nbsp;`/curly quotes, whitespace).
- **`models.py`** — frozen, source-agnostic dataclasses that clients parse
  *into*: `MeetingTime`, `Instructor`, `Section`, `Course`,
  `RequirementRule`, `Program`. Downstream code (cache, planner) works with
  these, not raw TTB JSON or Calendar HTML.

## Tests

Fixtures live in `backend/tests/fixtures/`; `backend/tests/conftest.py`
exposes the `FIXTURES` path and a `fixture(name)` loader. Unit tests must
not hit the network — use the saved fixtures. Live-service checks belong in
`backend/tests/*smoke*` only.

Run tests either way:

```
python -m pytest backend/tests
python backend/tests/some_test.py
```

On Windows, force UTF-8 when a script prints Unicode: `PYTHONUTF8=1 python ...`.
