# Screens — Programs & Courses

## Program search / browse (`/programs`)
```
PageHeader: "Programs"   Tabs: [ Browse ] [ My programs ]
FilterBar: [🔍 search]  Type ▾(Specialist/Major/Minor/Certificate/Focus)
           Subject ▾   [ clear ]
┌ ProgramCard ───────────────────────────────────────────────────┐
│ Geographic Data Science Major        [ Major ]                  │
│ ASMAJ1305A · Geography & Planning · 7.5 credits                 │
│                              [ View ]   [ + Add ]               │
└─────────────────────────────────────────────────────────────────┘
… (list; infinite scroll)
```
Data: `GET /api/programs?q=&type=&subject=&page=`.

## Program detail (`/programs/:code`)
```
ProgramHeader: Geographic Data Science Major (ASMAJ1305A) · Major
  Geography & Planning · 7.5 credits            [ + Add to my programs ]
Enrolment requirements (Callout):
  "Limited enrolment. Complete 4.0 credits incl. GGR172H1; min grade varies."
[ Load full requirements (Gemini) ]  ← if not yet parsed
Requirement groups (RequirementGroupCard list, read-only preview):
  • Core Geography Courses  0.5 cr
  • Methods Courses  1.5 cr
  • Core Geographic Data Science Courses  2.0 cr  …
POStCombinationValidator (if enrolled): "Valid with your Major + 2 Minors ✓"
```

## My programs (`/programs/mine`)
Drag-to-reorder priority; each row = ProgramCard + remove. Shows combination
validity banner (POStCombinationValidator) across all enrolled programs.

## Course search (`/courses`)
```
PageHeader: "Courses"
FilterBar: [🔍 code or title]  Level ▾  Breadth ▾(BR1–5)  Credit ▾  Term ▾
           Days ▾  [ has seats ] [ clear ]
┌ CourseCard (row) ──────────────────────────────────────────────┐
│ POL208H1  Introduction to International Relations   0.5   [BR3] │
│ Fall ● Winter ○   ·  seats 162/185   ·   ▸ Details   + Plan     │
└─────────────────────────────────────────────────────────────────┘
```
Typeahead (SearchTypeahead) suggests as you type. Data: `GET /api/courses?...`
(cache-backed local search over the synced session — code-prefix ranked).

## Course detail (`/courses/:code`) — drawer on mobile, page on desktop
```
Header: POL208H1 · Introduction to International Relations · 0.5 · St. George
Tabs: [ Overview ] [ Sections ] [ Satisfies ]
── Overview ──────────────────────────────────────────────────────
 Description (body-serif)…
 Prerequisites: 4.0 credits, or 1.0 in POL/JPA/…    (PrereqTree ▸)
 Exclusions: POL208Y1 / POL208Y5 …
 Breadth: [BR3 Society & its Institutions]   Hours: 24L/12T
── Sections (SectionList) ────────────────────────────────────────
 LEC0101  [LEC]  Tue 18:00–20:00, Thu 18:00–19:00  Krannich  162/185  ⚠wl
 TUT0101  [TUT]  Wed 09:00–10:00                    —          19/40
 …                                     [ Add selected to timetable ]
── Satisfies (RequirementMappingList) ────────────────────────────
 Public Policy Major → "Methods" group   ·   HBA degree → "BR3"
Footer: [ + Add to plan ]   [ + Add to timetable ]
```
Data: `GET /api/courses/:code` (catalog + live sections from TTB), `PrereqTree`
from parsed prerequisite text, `Satisfies` computed against enrolled programs.
```
