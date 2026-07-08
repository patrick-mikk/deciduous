# Architecture

## Overview

```
Browser (React SPA)
   │  HTTPS  /api/*   httpOnly session cookie
Flask API  (cPanel "Setup Python App", Passenger WSGI, Python 3.12.13)
   ├─ auth            login/register · bcrypt · server-side sessions   → ADR-0004
   ├─ security        Fernet field encryption · per-user data key      → ADR-0005
   ├─ planner         prereq parser · validator · auto-plan
   └─ data service    cache-first ─────────────┐
        │                                       │ on cache miss / nightly cron
   cPanel MySQL (SQLAlchemy)          External read-only sources (no Selenium → ADR-0003)
   users · transcripts(enc) ·          A. Academic Calendar (Drupal HTML)  — programs
   plans(enc) · *_cache                B. Timetable Builder JSON API        — courses+schedule
```

## Layers

| Layer | Responsibility | Notes |
|-------|----------------|-------|
| **Data clients** | Talk to TTB + Calendar, normalize to internal models | `requests`/`urllib`; tolerate TTB 404-means-empty |
| **Cache** | Persist fetched courses/offerings/programs with `fetched_at` TTL | offerings ~24h, catalog ~7d |
| **Planner** | Prereq tree parse · validate a plan · propose a sequence | pure functions, unit-testable without network |
| **API** | Flask blueprints under `/api/*` | auth-gated; JSON in/out |
| **Auth + crypto** | Sessions, password hashing, at-rest encryption | see ADR-0004, ADR-0005 |
| **Persistence** | MySQL via SQLAlchemy | ADR-0002 |

## Primary data source: Timetable Builder

One session-scoped `POST /getPageableCourses` returns **catalog data**
(`cmCourseInfo`: description, prerequisitesText, exclusionsText, breadth) **and**
live sections (LEC/TUT/PRA, meeting times, enrolment, instructors) together. Full
contract: [../backend/docs/TTB_API_REFERENCE.md](../backend/docs/TTB_API_REFERENCE.md).
The Academic Calendar is used mainly for **program/certificate requirements**.

## Data flow (course search)

1. API receives a search → data service checks MySQL cache.
2. On miss/expiry → data client pulls from TTB (paged), normalizes, upserts cache.
3. Planner/validator reads from cache only (no network in hot path).

## Deployment shape

cPanel Passenger loads `passenger_wsgi.py` → `application = Flask app`. React build
is uploaded as static assets served same-origin (simplifies cookie auth). Secrets
via environment variables. HTTPS via AutoSSL. Nightly cache refresh via cPanel Cron.
See [roadmap.md](roadmap.md) for build order.
