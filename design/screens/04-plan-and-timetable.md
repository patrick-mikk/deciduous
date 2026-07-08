# Screens — Course Planning & Timetable

## Plan board (`/plan`)
Wide board; horizontal scroll; the planning workhorse.
```
PageHeader: "Plan"   [ Auto-plan ] [ Validate ] [ 3 issues ⚠ ]  Year ▾
┌ CourseRail ─┐ ┌ Year 2 ───────────────┐ ┌ Year 3 ───────────────┐
│ 🔍 search   │ │ Fall 2026    12.0 cr  │ │ Fall 2027     ── cr   │
│ [only fills │ │ ┌ PlanCourseCard ────┐ │ │ (drop zone)           │
│  a remaining│ │ │ PPG301H1  0.5      │ │ │                       │
│  req]       │ │ │ ✔prereq [Methods]  │ │ │ + add course          │
│             │ │ ├────────────────────┤ │ │                       │
│ CourseCard  │ │ │ POL208H1  0.5      │ │ ├───────────────────────┤
│ (draggable) │ │ │ ⚠ prereq unmet [BR3]│ │ │ Winter 2028   ── cr   │
│ …           │ │ └────────────────────┘ │ │                       │
│             │ │ + add course           │ │                       │
│             │ ├────────────────────────┤ │                       │
│             │ │ Winter 2027   10.0 cr  │ │                       │
└─────────────┘ └────────────────────────┘ └───────────────────────┘
```
- Drag CourseCard → TermColumn drop zone → optimistic add + async validate.
- **PlanCourseCard** badges: ⚠ prereq unmet (tooltip lists missing), ⛔ exclusion,
  ⏳ not offered that term; requirement-satisfied tags are breadth/group-colored.
- **ValidationSummary** (from "3 issues") lists all problems with jump links.
- **AutoPlanPanel** (drawer): preferences → Generate → DiffPreview (added/moved) → Apply.
- Autosaves; per-term credit + breadth subtotals in the column header.

Data: `GET/PUT /api/plan`, `POST /api/plan/validate`, `POST /api/plan/autoplan`.
Validation uses parsed prerequisites, exclusions, TTB offering availability.

## Timetable builder (`/timetable`)
```
PageHeader: "Timetable"  Term ▾ Fall 2026   ScenarioTabs: [Plan A][Plan B][+]
                                            [ Optimize ▸ ]  [ Export ICS ]
┌ CourseTray ─────────────┐ ┌ TimetableGrid (Mon–Fri × 8:00–22:00) ──────┐
│ POL208H1                │ │      Mon    Tue    Wed    Thu    Fri        │
│  ◉ LEC0101  ○ LEC5101   │ │ 9  │      │      │[TUT ]│      │            │
│  ◉ TUT0101              │ │10  │      │      │POL208│      │            │
│ URB335H1                │ │…   │      │      │      │      │            │
│  ◉ LEC0101 🔒           │ │18  │      │[LEC ]│      │[LEC ]│            │
│ + add course            │ │19  │      │POL208│      │POL208│            │
│ [ auto-pick all ]       │ │20  │      │      │      │      │            │
└─────────────────────────┘ └─────────────────────────────────────────────┘
ConflictBadge: "1 conflict: URB335 LEC overlaps POL208 LEC (Tue 18–20)"  ⚠
```
- **SectionBlock**s colored per course; `locked` 🔒 stays through swaps; overlaps
  render a red hatch + ConflictBadge; click a block → swap section popover.
- **SeatMeter**/waitlist shown per section in the tray.

Data: sections + meeting times from TTB (`day` 1–7, minutes-since-midnight);
conflict = interval overlap on the same day. Scenarios persisted per user+term.

## Timetable optimizer (`/timetable/optimize`)
```
┌ OptimizerPanel ─────────────┐ ┌ ScheduleCandidateList ────────────────┐
│ Days on campus: ◉ minimize  │ │ #1  score 92  · 3 days · 0 gaps       │
│ Earliest [09:00]──[18:00]   │ │     mini-grid preview   [ Preview ][Use]│
│ Latest end  ▮────────       │ │ #2  score 88  · 4 days · 1 gap (60m)  │
│ Avoid: ☑ Fri  ☐ mornings    │ │ #3  score 85  · 4 days · early Mon    │
│ ☑ Keep locked sections      │ │ …                                     │
│ ☐ Allow full/waitlisted     │ │                                       │
│        [ Generate ]         │ │                                       │
└─────────────────────────────┘ └───────────────────────────────────────┘
```
- Generate (async, spinner) → ranked conflict-free candidates scored by the
  preferences; "Preview" renders on the grid; "Use this" applies sections back
  to the builder. Honours locked sections.
```
