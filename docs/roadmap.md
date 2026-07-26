# Roadmap

Build order for the degree planner. Backend first; React after the API is stable.

| Phase | Deliverable | Status |
|------|-------------|--------|
| **0** | Repo + docs scaffolding, `requirements.txt`, `.gitignore` | done ✅ |
| **1** | Data layer: 3 source clients + SQLite cache + Gemini grouper, with tests | done ✅ |
| **2** | Flask API (`app.py`/`passenger_wsgi.py`) + auth + Fernet encryption + endpoints | done ✅ |
| **3** | Prerequisite parser + plan validator + degree-rules engine (`planner/`) | done ✅ |
| **4** | Program-requirement tracker + auto-plan + Degree Explorer import | done ✅ |
| **5** | React + TS SPA (Vite) on the Claude Design system, 18 screens | done ✅ |
| **6** | cPanel deploy to `deciduous.mikkelsen.ca`, AutoSSL, nightly cron, hardening | in progress — code-side done, see [docs/deploy-cpanel.md](deploy-cpanel.md) |

## Done

- **Data layer** — TTB API, Academic Calendar course + program clients, Gemini requirement
  grouper (on-demand), thread-safe SQLite cache. Contract: [../backend/docs/TTB_API_REFERENCE.md](../backend/docs/TTB_API_REFERENCE.md).
- **Backend API** — Flask app-factory with auto-registered blueprints (auth, programs,
  courses, plan, timetable, me, import, share), per-user Fernet encryption, and the pure
  `backend/planner` degree-rules engine ([09-uoft-degree-rules.md](../design/09-uoft-degree-rules.md)).
  238 tests passing.
- **Frontend** — Vite + React + TypeScript SPA using the Claude Design system (87 components,
  light/dark tokens); 18 routed screens; typed API client with a mock adapter. `npm run build` green.

## Remaining (Phase 6)

- **cPanel deploy**: MySQL provisioning, Passenger WSGI, React static build served at
  `deciduous.mikkelsen.ca`, AutoSSL, env vars, nightly cache-refresh cron.
- Timetable **optimizer** polish.
- ~~Auth hardening~~ shipped: remember-me (30-day) sessions, passkey (WebAuthn) sign-in,
  session management, password change with key re-wrap, recovery-code reset, account
  deletion, profile endpoints. Remaining production items: [production-hardening.md](production-hardening.md).
- Breadth data completeness for past (uncached) sessions; wire the frontend off mock to the live API.

## Scope notes

- Start with **Arts & Science (`ARTSC`)**; other divisions later via the `divisions` param.
- Fall–Winter offerings appear in TTB only once published; sessions are fetched at runtime.
