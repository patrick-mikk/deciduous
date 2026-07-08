# Deciduous

A degree & timetable planner for **University of Toronto Arts & Science** students. 
Plan your whole degree by the seasons: enrolled programs, what each still requires,
which courses satisfy what, prerequisite/exclusion checks, GPA tracking, and a
conflict-free timetable from live UofT data.

> Unofficial student tool; Not affiliated with or endorsed by the University of Toronto.

## Architecture

```
React + TypeScript SPA (Vite)            →  Flask API (app-factory, Passenger/cPanel)
  Claude Design system (87 components)        auth · Fernet field encryption · SQLAlchemy/MySQL
  18 screens · typed API client + mock        planner engine (degree rules, GPA, prereqs)
                                              data layer: Timetable Builder API · Academic
                                              Calendar (courses + programs) · Gemini requirement
                                              grouper · Degree Explorer import · SQLite cache
```

Data sources are consumed over plain HTTP (no Selenium — see
[docs/decisions/0003](docs/decisions/0003-no-selenium-http-data-layer.md)). Sensitive
academic data (transcripts, plans) is encrypted at rest
([ADR-0005](docs/decisions/0005-fernet-per-user-encryption.md)). Degree rules are captured
in [design/09-uoft-degree-rules.md](design/09-uoft-degree-rules.md) and implemented in
`backend/planner/`.

## Run it locally

**Backend** (Python 3.12; SQLite fallback when no `DB_*` env is set):
```bash
pip install -r backend/requirements.txt
python -m flask --app backend.app run          # http://127.0.0.1:5000
PYTHONUTF8=1 python -m pytest backend/tests -q  # 238 passing
```

**Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev            # Vite dev server; renders against a mock adapter out of the box
npm run build          # production build
```
Point the SPA at the live API with `VITE_API_BASE=http://127.0.0.1:5000` in `frontend/.env`.

## Configuration

Secrets load from a **git-ignored `.env`** at the repo root (see `.env.example`) via
`backend/config.py`:
- `GEMINI_API_KEY` — Google Gemini, for on-demand requirement grouping (get one free at
  [aistudio.google.com](https://aistudio.google.com/apikey)).
- `DB_*` — cPanel MySQL (optional locally; SQLite is used otherwise).

## Docs

- [AGENTS.md](AGENTS.md) — project structure, commands, conventions (for AI agents + humans)
- [docs/architecture.md](docs/architecture.md) · [docs/roadmap.md](docs/roadmap.md) ·
  [docs/decisions/](docs/decisions/) (ADRs)
- [design/](design/) — the full design package (product, IA, flows, tokens, components, screens)
- [backend/docs/TTB_API_REFERENCE.md](backend/docs/TTB_API_REFERENCE.md) — the Timetable Builder API contract
