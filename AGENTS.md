# AGENTS.md — UofT Degree Planner

Context for AI coding agents (and humans). Canonical agent instructions live here;
`CLAUDE.md` imports this file. Keep it concise and **link to `docs/` rather than
copying detail** — pointers stay current, copies rot.

## What this is

A web app that helps University of Toronto (Arts & Science) students plan their
degree: search courses, track a transcript, build a term-by-term plan, and
validate it against prerequisites, exclusions, breadth requirements, program
requirements, and timetable conflicts — using live data from the UofT **Timetable
Builder** API and the **Academic Calendar**.

Target deployment: `deciduous.mikkelsen.ca`, a **cPanel Python app** (Passenger WSGI),
Python **3.12.13**, cPanel **MySQL**. React SPA frontend (built later).

## Why (design intent)

- Sensitive academic records → user login + **encryption at rest** of transcript/plan data.
- Shared cPanel hosting can't run headless Chrome → the data layer uses plain HTTP
  (`requests`), **no Selenium**. See [ADR-0003](docs/decisions/0003-no-selenium-http-data-layer.md).
- One session-scoped Timetable Builder pull returns catalog **and** live schedule +
  enrolment together, so it is the primary data source.

The product is branded **Deciduous** (terms = seasons, degree = a branching tree).

## Project structure

```
backend/                 Flask API (app-factory, Passenger WSGI for cPanel)
  app.py                 create_app() — auto-registers every backend/api/*.py `bp`
  passenger_wsgi.py      cPanel entry point
  models_db.py           SQLAlchemy: User, Session, TranscriptEntry(enc), Plan/PlanItem(enc),
                         ProgramEnrolment, Share
  security/crypto.py     Fernet per-user field encryption (ADR-0005)
  api/                   one blueprint per resource: auth, health, programs, courses, plan,
                         timetable, me, import_, share  (+ _audit helper)
  planner/               pure engine — validators, gpa, prereqs, course_code, types
                         (implements design/09-uoft-degree-rules.md)
  data_sources/          TTBClient, CalendarCourseClient, ProgramClient (+ Gemini llm_grouper),
                         SqliteCache, models.py, http.py, config.py
  ingest/                degree_explorer.py — Degree Explorer PDF + bookmarklet parser
  tui/                   dev TUI + SearchService facade (not shipped to the web app)
  tests/                 pytest suite (238+ passing) + *smoke* live checks
  docs/                  TTB_API_REFERENCE.md
frontend/                React + TypeScript SPA (Vite) — the Deciduous UI
  src/ds/                the Claude Design system (87 components) + tokens
  src/screens/           18 routed screens; src/api/ typed client + mock adapter
docs/                    project-level structured docs (architecture, conventions, ADRs, roadmap)
design/                  the design package (00-09 + screens/) and Claude Design output
```

Current state: **full stack built** — data layer + Flask API + validators + React frontend.
Remaining: cPanel deploy, timetable-optimizer polish, auth hardening (see docs/roadmap.md).

## Commands

| Task | Command |
|------|---------|
| Backend tests | `PYTHONUTF8=1 python -m pytest backend/tests -q` |
| Run backend (dev) | `python -m flask --app backend.app run` (SQLite fallback if no `DB_*` env) |
| TTB API smoke test | `python backend/tests/ttb_smoke_test.py` (stdlib only) |
| Frontend dev | `cd frontend && npm run dev` |
| Frontend typecheck + build | `cd frontend && npm run typecheck && npm run build` |
| Install backend deps | `pip install -r backend/requirements.txt` |

> On Windows, force UTF-8 for scripts that print Unicode: `PYTHONUTF8=1 python …`.
> Secrets (`GEMINI_API_KEY`, DB creds) load from a git-ignored `.env` via `backend/config.py`.

## Conventions (summary — full list in [docs/conventions.md](docs/conventions.md))

- Python: PEP 8, type hints, small pure functions; stdlib/`requests` in the data layer.
- Never commit secrets. DB creds and encryption keys come from **environment variables**
  (cPanel env / a `.env` outside the webroot).
- Prefer `file:line` pointers over pasted code in docs.
- Data-layer code must tolerate the TTB quirk that a **no-match search returns HTTP 404**.

## Boundaries / safety

- Do **not** add Selenium/Chrome dependencies (see ADR-0003).
- Do **not** hard-code session codes; fetch them from `/reference-data` at runtime.
- Treat the TTB and Calendar endpoints as **undocumented public read-only** APIs:
  cache aggressively, throttle bulk pulls, never write.
- Don't hit external UofT services in unit tests except the dedicated smoke tests.

## Domain glossary

- **Session code** `2YYY?`: `20265`=Summer 2026 (Y), `20269`=Fall 2026 (F),
  `20271`=Winter 2027 (S), `20269-20271`=Fall–Winter full-year.
- **H / Y course**: 0.5-credit half / 1.0-credit full-year course (last letters of code, e.g. `POL208H1`).
- **Breadth requirement**: ArtSci category (1–5) a course satisfies; degrees need coverage across categories.
- **Teach method**: `LEC` (lecture) / `TUT` (tutorial) / `PRA` (practical) — a section type.
- **POSt / program**: a specialist/major/minor with completion & enrolment requirements.
- **Division**: faculty (`ARTSC`, `APSC`, …); we start with `ARTSC`.

## Key references

- Data sources & endpoints: [backend/docs/TTB_API_REFERENCE.md](backend/docs/TTB_API_REFERENCE.md)
- Architecture: [docs/architecture.md](docs/architecture.md)
- Decisions (ADRs): [docs/decisions/](docs/decisions/)
- Roadmap / phases: [docs/roadmap.md](docs/roadmap.md)
- cPanel deploy runbook: [docs/deploy-cpanel.md](docs/deploy-cpanel.md)
