# 08 — Claude Design Brief (paste this first)

> Paste this whole file into Claude Design to establish the product and design
> system, then feed the component library (`04`) and screens (`05/`) in order.

## Product
**Deciduous** — a web app that helps University of Toronto (Arts & Science)
students plan their whole degree: enrolled programs, what each program still
requires, which courses satisfy what, prerequisite/exclusion validation, GPA
tracking, and a conflict-free timetable — from live UofT data. *Tagline: "Plan
your degree by the seasons."* Unofficial; not affiliated with U of T.

## Concept
Deciduous = seasonal + branching, mirroring a degree. **Terms are seasons**
(Fall/Winter/Summer), **the degree is a tree** (trunk = degree, branches =
requirement groups, leaves = courses that leaf-in as you complete them). The
dashboard's degree-progress hero is a **growth tree**. Calm, academic, precise.

## Visual system (use exactly)
- **Primary:** U of T Blue `#1E3765` (hover `#16294C`). **Accent:** Boundless Blue
  `#007FA3` (links/selection/focus). Neutrals are cool, blue-biased (canvas
  `#FBFCFE`, surface `#FFFFFF`, light grey `#F2F4F7`, ink `#101B30`). Semantic:
  success `#1E7A47`, warning `#A96A00`, danger `#BC3A2E` — state only, not a brand.
- **Breadth spectrum** (the one bold moment — encodes the 5 ArtSci categories):
  BR1 `#7A4FB5` · BR2 `#B26A12` · BR3 `#1E6FA8` · BR4 `#2E7D46` · BR5 `#0E7E92`.
- **Seasonal accent** (brand/illustration ONLY, never UI state): leaf-green
  `#3E8E5A`, amber `#C7861F`, rust `#B4542B`.
- **Type:** **Archivo** (grotesque; UI + headings, evokes UofT's Trade Gothic),
  **Source Serif 4** (old-style serif; hero/program/course titles + editorial,
  evokes Bembo, used sparingly), **IBM Plex Mono** (course codes, times, seats).
- **Radius:** cards 14, inputs/buttons 10, chips 999. **Elevation:** soft, cool.
  **Full light + dark** parity (token-level; dark lightens the blues for contrast).
- Course codes always mono; all comparable numbers use tabular figures.

## Design principles
Summary before detail (it's a tool, not a document). State encoded in form as well
as number (pill/chip/severity stripe). One persistent element: a **ProgressStrip**
(credits · breadth · CGPA · degree %) always visible. Accessible (WCAG AA), keyboard-
complete, reduced-motion aware. Voice: plain, calm, encouraging — every screen
answers "what do I still need, and can I take it?"

## Build order
1. **Design system** — tokens (colour light/dark, type scale, spacing, radius,
   elevation) + the wordmark (Archivo + leaf/branch mark).
2. **Primitives & layout** (`04.A/B`): Button, Input, Select, Chip, Badge,
   ProgressBar/Ring, Meter, Card, Tabs, Table, Modal, Drawer, Toast, CommandPalette,
   AppShell (TopBar + SideNav + ProgressStrip).
3. **Domain components** (`04.C`): CourseCard, CourseDetailPanel, SectionList,
   ProgramCard, RequirementGroupCard, RequirementCourseChip, BreadthTracker,
   DegreeProgressCard (growth tree), PlanBoard/TermColumn/PlanCourseCard,
   TimetableGrid/SectionBlock, OptimizerPanel, ImportPanel, GPACard/Sparkline.
4. **Screens** (`05/`): Auth & Onboarding → Dashboard → Requirements → Programs &
   Courses → Plan → Timetable → Transcript/Settings/Share. Each screen names the
   components it composes — reuse, don't reinvent.

## The 6 flagship screens (make these sing)
1. **Dashboard** — KPI row + program cards + breadth spectrum + "next actions".
2. **Program requirements** (`/requirements/:code`) — RequirementGroupCards with
   progress bars, per-course credits + notes, "only what's left", Gemini reload.
3. **Plan board** (`/plan`) — seasonal term columns, drag-drop, prereq/exclusion
   badges, requirement-satisfied tags.
4. **Timetable builder + optimizer** — weekly grid, conflict detection, ranked
   optimized candidates.
5. **Course detail** — overview (serif) + live sections (seats/times/instructor) +
   "requirements it satisfies".
6. **Onboarding import** — PDF/bookmarklet → preview → confirm programs → set term.

## Non-negotiables
- Design **empty / loading / error / success** for every data surface.
- Never encode status by colour alone (pair icon + text).
- Heavy actions (Gemini reparse, optimize, import) are explicit, async, cancellable.
- Don't reproduce the official U of T crest/wordmark; use the Deciduous mark.
- Don't default to Inter/cream-terracotta/gradient-hero — this identity is UofT
  blue + grotesque/serif academic + a seasonal tree.
