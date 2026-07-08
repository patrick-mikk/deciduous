# Screens — Dashboard & Progress

## Dashboard (`/dashboard`) — the home
The summary-before-detail view. Answers "where am I and what's next?"
```
PageHeader: "Welcome back, Priya"            [ Plan next term ▸ ]
┌ KPI row (StatTile ×4) ───────────────────────────────────────────┐
│ Credits 13.5/20 │ CGPA 2.70 ▲ │ Breadth 4/5 │ Degree 68% (ring)  │
└───────────────────────────────────────────────────────────────────┘
┌ Left (2fr) ───────────────────────────┐ ┌ Right (1fr) ───────────┐
│ My programs (ProgramCard list)         │ │ Alerts (Notification.. )│
│  • HBA (degree)            ring 68%    │ │ ⚠ POL208 prereq unmet   │
│  • Major: Public Policy    ring 60%    │ │ 📅 Enrolment opens Jul 21│
│  • Minor: American Studies ring 75%    │ │ ○ Seat opened: PPG301   │
│  • Minor: GIS              ring 40%    │ ├─────────────────────────┤
│           [ View requirements ▸ ]      │ │ Next actions (checklist)│
├────────────────────────────────────────┤ │ ☐ Add 0.5 cr at 300+    │
│ This term (planned) — TermColumn peek   │ │ ☐ Pick a BR2 course     │
│  PPG301H1 · URB335H1 · …    12.0 cr     │ │ ☐ Resolve 1 conflict    │
│           [ Open plan ▸ ]  [ Timetable ▸]│ │        [ Auto-plan ]    │
└────────────────────────────────────────┘ └─────────────────────────┘
Breadth spectrum (BreadthTracker, full width):
[BR1 ██ 0.5] [BR2 ─ 0] [BR3 ███ 1.0] [BR4 ██ 0.5] [BR5 ███ 1.5]  4/5 satisfied
```
Components: PageHeader, StatTile×4, ProgramCard, DegreeProgressCard, TermColumn
(peek), NotificationPanel, checklist, BreadthTracker. Empty state (no import yet):
big EmptyState → "Import your record".

Data: `GET /api/me/summary`, `/api/me/programs`, `/api/me/alerts`, `/api/plan/current`.

## Requirements overview (`/requirements`)
```
PageHeader: "Requirements"      [ Only what's left ⌄ ] [ Export ]
┌ Degree: Honours BA (ASPRGHBA) ───────────────────────────────────┐
│ ProgressRing 68% · 13.5/20 credits · 8 requirements · 3 incomplete│
│ RequirementProgressList (degree-level Req 1..11 with bars)        │
└───────────────────────────────────────────────────────────────────┘
Per-program cards (grid):
┌ Major: Public Policy 60% ┐ ┌ Minor: American 75% ┐ ┌ Minor: GIS 40% ┐
│ 4.2/7.0 cr  ▸view        │ │ 3.0/4.0 cr ▸view    │ │ 1.6/4.0 cr ▸view│
└──────────────────────────┘ └─────────────────────┘ └────────────────┘
```

## Program requirements detail (`/requirements/:code`)
The heart of progress tracking. Uses RequirementGroupCard per group.
```
ProgramHeader: Public Policy Major (ASMAJ2660) · Major · 7.0 credits
  completion ring 60%   [ Reload requirements (Gemini) ]  [ Add to plan ]
Toggle: [● Only what's left]     Legend: ✔ done ◐ planned ○ available ⚠ blocked
┌ RequirementGroupCard ─────────────────────────────────────────────┐
│ First Year                                          1.0 / 1.0  ✔    │
│ ProgressBar ████████████████████  100%                             │
│  ✔ ECO101H1 (0.5)  ✔ ECO102H1 (0.5)          «note: intro econ»    │
├────────────────────────────────────────────────────────────────────┤
│ Methods                                             0.5 / 1.0  ◐    │
│ ProgressBar ██████████░░░░░░░░░░  50%                               │
│  ✔ STA220H1 (0.5)  ○ POL222H1 (0.5)  ○ POL232H1 (0.5)              │
├────────────────────────────────────────────────────────────────────┤
│ Higher Years — Electives                            1.5 / 2.0  ◐    │
│  ○ PPG310H1 (0.5) ◐ PPG301H1(0.5,planned) … [ show 18 more ⌄ ]     │
└────────────────────────────────────────────────────────────────────┘
```
- Each **RequirementCourseChip**: code (mono) + credit + status icon; hover → note;
  click → CourseDetailPanel drawer; "Add to plan" inline.
- "Reload requirements (Gemini)" = the on-demand grouper (async, spinner, toast).
- "Only what's left" hides ✔ groups/courses.

Data: `GET /api/programs/:code/requirements` (RequirementGroup[] with per-course
credits + notes), cross-referenced with the student's transcript/plan for status.
```
