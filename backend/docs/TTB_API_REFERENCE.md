# Timetable Builder (TTB) API — Verified Reference

Reverse-engineered from the TTB Angular client and confirmed against the live
service on 2026-07-07. This is an **undocumented, public, read-only** JSON API.
No auth, no cookies. Be a good citizen: cache aggressively, throttle bulk pulls.

- **Base URL:** `https://api.easi.utoronto.ca/ttb`
- **Send header** `Accept: application/json` (some endpoints default to XML).
- Also send `Content-Type: application/json` on POSTs and an `Origin` header.
- Smoke test: `python backend/tests/ttb_smoke_test.py` (stdlib only).

## Response envelope

All endpoints wrap results as:

```json
{ "payload": { ... }, "status": [ { "code": 4404, "message": "No results found..." } ] }
```

A search with no matches returns **HTTP 404** with `payload: null` — treat 404 on
`getPageableCourses` as "0 results", not a transport error.

---

## 1. `GET /reference-data`

Drives every dropdown. Key fields in `payload`:

| field | use |
|-------|-----|
| `currentSessions[]` | valid session codes (see below) |
| `divisions[]` | `ARTSC`, `APSC`, `ERIN`, `SCAR`, `MUSIC`, `ARCLA`, `FIS`, `FPEH` |
| `campuses[]` | `St. George`, `Scarborough`, `University of Toronto at Mississauga` |
| `requirements[]` | breadth/distribution requirement filter values |
| `courseLevels[]` | `100/A`, `200/B`, `300/C`, `400/D`, `5+` |
| `deliveryModes[]` | `In Person`, `Hybrid`, `Online Synchronous`, `Online Asynchronous`, ... |

### Session codes

`currentSessions[]` mixes UI group-headers (`header: true`, non-numeric `value`)
with selectable options. **Use only entries where `header` is false and `value`
is all digits.** Format `2` + `YYY` + term digit:

| value | meaning |
|-------|---------|
| `20265` | Summer Full Session 2026 (Y) |
| `20265F` / `20265S` | Summer first / second sub-session |
| `20269` | Fall 2026 (F) |
| `20271` | Winter 2027 (S) |
| `20269-20271` | Fall–Winter 2026-2027 full-year (Y) |

Only sessions currently loaded in TTB are returned — a future Fall/Winter appears
only once TTB publishes it. As of testing, **Summer 2026 (`20265`) is populated
(205 ARTSC courses); Fall–Winter 2026-27 is not yet.**

---

## 2. `POST /getPageableCourses`  — primary search

Request body (see `build_search_payload` in the smoke test):

```jsonc
{
  "courseCodeAndTitleProps": {
    "courseCode": "POL",            // prefix match on code, "" for all
    "courseTitle": "",
    "courseSectionCode": "",        // "F"|"S"|"Y" to filter term
    "searchCourseDescription": false
  },
  "departmentProps": [], "campuses": [], "requirementProps": [],
  "instructorProps": [], "courseLevels": [], "deliveryModes": [],
  "dayPreferences": [], "timePreferences": [], "creditWeights": [],
  "sessions": ["20265"],            // REQUIRED — one or more session codes
  "divisions": ["ARTSC"],           // REQUIRED
  "availableSpace": false, "waitListable": false,
  "page": 1, "pageSize": 20, "direction": "asc"
}
```

Response: `payload.pageableCourse.{ total, courses[] }`. Pagination is 1-indexed
and pages are disjoint. ~0.1s/page. Iterate `page` until `page*pageSize >= total`.

### Course object

Top level:

| field | notes |
|-------|-------|
| `code` | e.g. `APM462H1` (dept + number + H/Y + campus digit) |
| `name` | course title |
| `sectionCode` | `F` / `S` / `Y` (which term this offering is) |
| `sessions` | `["20265"]` |
| `minCredit` / `maxCredit` | `0.5` for H, `1.0` for Y |
| `campus` | `St. George` etc. |
| `primaryTeachMethod` | usually `LEC` |
| `cancelInd` | `"N"` normally |
| `sections[]` | see below |
| `breadths[]` | structured breadth (`code: "BR=5"`, `type`, `description`) |
| `cmCourseInfo` | **the calendar data — see below** |

### `cmCourseInfo` (catalog details, no separate calendar scrape needed)

| field | notes |
|-------|-------|
| `description` | full course description |
| `prerequisitesText` | **HTML string**, e.g. `"<p>(MAT223H1,MAT224H1)/ MAT247H1</p>"` — strip tags before parsing |
| `corequisitesText` | HTML |
| `exclusionsText` | HTML |
| `recommendedPreparation` | HTML |
| `breadthRequirements` | e.g. `["The Physical and Mathematical Universes (5)"]` |
| `distributionRequirements` | e.g. `["Science"]` |
| `levelOfInstruction` | `"undergraduate"` |
| `publicationSections` | department/section grouping |

> This is why the plan can lean on TTB for course details and use the Academic
> Calendar mainly for **program requirements** and as a cross-check.

### Section object (`sections[]`)

| field | notes |
|-------|-------|
| `name` | `LEC5101`, `TUT0102`, ... |
| `teachMethod` | `LEC` / `TUT` / `PRA` |
| `type` | `Lecture` / `Tutorial` / `Practical` |
| `sectionNumber` | `5101` |
| `currentEnrolment` / `maxEnrolment` | live counts |
| `currentWaitlist` / `waitlistInd` | waitlist state (`"Y"`/`"N"`) |
| `openLimitInd` / `cancelInd` / `tbaInd` | flags |
| `instructors[]` | `[{firstName, lastName}]` |
| `enrolmentControls[]` | who may enrol (year, subject/POSt, program type) |
| `meetingTimes[]` | see below |
| `linkedMeetingSections` | LEC⇄TUT linkage when present |

### Meeting time object (`meetingTimes[]`)

```json
{
  "start": { "day": 2, "millisofday": 64800000 },
  "end":   { "day": 2, "millisofday": 72000000 },
  "building": { "buildingCode": "", "buildingRoomNumber": "", "buildingName": null },
  "sessionCode": "20265",
  "repetition": "WEEKLY", "repetitionTime": "ONCE_A_WEEK"
}
```

- `day`: **1=Mon … 7=Sun** (ISO-8601, confirmed).
- `millisofday`: ms since midnight → `HH:MM = (ms/60000)//60 : (ms/60000)%60`.
  (`64800000` → 18:00, `72000000` → 20:00.)
- Two meeting-time entries = a section that meets twice a week.
- `tbaInd == "Y"` / empty `meetingTimes` = time not yet assigned.

Use start/end day+minutes to detect **timetable conflicts** between planned sections.

---

## 3. `GET /getCoursesByCodeAndSectionCode/<CODE>`

Single-course lookup (e.g. `/getCoursesByCodeAndSectionCode/APM462H1`) → HTTP 200
with the same `payload.pageableCourse.courses[]` envelope, including all sections.
Without a session filter it may return multiple term offerings (F/S/Y). Handy for
"refresh one course."

---

## Endpoints observed but not needed yet

`/current-session`, `/getCourses`, `/findById`, `/generate`, `/generateYear`
(auto-scheduler), `/getShareLink` (`/shorten`), `/retrieve`, `/getMatchingDivisions`,
`/getMatchingDepartments`.

**Typeahead:** `getMatchingCourseTitles?term=` returned 404 in isolation (likely
needs `divisions`/`sessions` params). For the planner, implement course typeahead
**client-side over the cached course list** instead of depending on it.

## Implications for the data layer

1. **No Selenium / Chrome.** Plain `requests` (or `urllib`) is enough — critical
   for shared cPanel hosting.
2. **One session-scoped bulk pull** (`getPageableCourses`, ~11 pages for 205
   ARTSC courses) yields catalog + live schedule + enrolment in one shot. Cache in
   MySQL with a `fetched_at` TTL (offerings ~24h, descriptions ~7d).
3. **Prerequisite parser** consumes `cmCourseInfo.prerequisitesText` (strip HTML).
4. Academic Calendar scrape is reserved for **program/certificate requirements**.
