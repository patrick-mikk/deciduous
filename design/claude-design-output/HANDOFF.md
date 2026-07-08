# Handoff: Deciduous Design System → Claude Code

## Overview

**Deciduous** is a University of Toronto Arts & Science degree & timetable planner
(unofficial student tool). This package is the **complete design system** — design
tokens, a 87-export component library, foundation specimen cards, and full
click-through screen recreations of the product — plus the source design brief and
the real backend data model.

Use it to implement Deciduous (or any Deciduous feature) in a real codebase.

## About the design files

The files in this bundle are **design references authored in HTML/JSX** — prototypes
that show the intended look, behaviour, and component API. They are **not** production
code to ship verbatim. The task is to **recreate these designs in your target
environment** (React, Next, Vue, SwiftUI, native, …) using its established patterns,
router, data layer, and build system. If no front-end exists yet, the design package
(`uploads/Deciduous-Claude-Design-Package/`) proposes a React client bound to an
existing Python/Flask backend — a sensible default, but choose what fits.

The React components under `components/**/*.jsx` are intentionally framework-light
(React + inline styles reading CSS custom properties, no UI libs). You can port them
almost directly, or lift their exact values into your own component system. The
`.d.ts` beside each component is the prop contract; the `.prompt.md` is a one-line
"what & when" + usage example.

## Fidelity

**High-fidelity.** Final colours, typography, spacing, radii, elevation, motion, and
interactions are all specified as design tokens and implemented in the components.
Recreate pixel-for-pixel using your codebase's libraries, but keep the exact token
values below.

## How the design system is structured

- `styles.css` — the single global entry point (imports the token files only).
- `tokens/` — `colors.css` (light + dark themes, brand, semantic, breadth spectrum,
  seasonal accents), `typography.css`, `spacing.css` (spacing + radius + elevation +
  motion), `fonts.css` (webfont `@import`).
- `components/<group>/<Name>.jsx` + `<Name>.d.ts` + `<Name>.prompt.md` — the library.
- `guidelines/*.card.html` — foundation specimens (colour, type, spacing, brand).
- `ui_kits/deciduous/` — the flagship screens assembled from the components.
- `ui_kits/planner/` — an earlier, simpler click-through (kept for reference).
- `uploads/Deciduous-Claude-Design-Package/` — the authoritative brief: product
  overview (`00`), IA (`01`), user flows (`02`), design tokens (`03`), component
  library (`04`), data model + API map (`06`), states/interactions/a11y (`07`),
  the paste-first brief (`08`).
- `uploads/09-uoft-degree-rules.md` — the real degree rules (breadth, distinct-credits,
  level distribution, GPA/standing) behind the validators.

## Design tokens (exact values — light theme)

Neutrals: `--bg #FBFCFE` · `--surface #FFFFFF` · `--surface-sunken #F2F4F7` ·
`--surface-hover #EAEEF4` · `--border #D8DFE9` · `--border-strong #BEC8D6` ·
`--overlay rgba(16,27,48,.48)`.
Text: `--text #101B30` · `--text-secondary #45536B` · `--text-tertiary #6B7890` ·
`--text-on-primary #FFFFFF`.
Brand: `--primary #1E3765` (hover `#16294C`, tint `#E5E9F1`) — U of T Blue;
`--accent #007FA3` (hover `#006A88`) — Boundless Blue.
Semantic: `--success #1E7A47` · `--warning #A96A00` · `--danger #BC3A2E` ·
`--info #255F9C` (each with a `-bg` tint).
Breadth spectrum (5 ArtSci categories): BR1 `#7A4FB5` · BR2 `#B26A12` · BR3 `#1E6FA8`
· BR4 `#2E7D46` · BR5 `#0E7E92` (each with a `-bg` tint).
Seasonal (brand/illustration ONLY, never UI state): leaf-green `#3E8E5A` ·
leaf-amber `#C7861F` · leaf-rust `#B4542B`.

Dark theme overrides live under `:root[data-theme="dark"]` in `tokens/colors.css`
(brand blues lighten: `--primary #5E8FD1`, `--accent #33A8C9`; bg `#0B1220`,
surface `#121B2B`). Theme is toggled by writing `data-theme` on `<html>`; wire OS
preference via a `matchMedia('(prefers-color-scheme: dark)')` listener in the app.

Type: `--font-sans` **Archivo** (UI/headings; stands in for U of T's Trade Gothic),
`--font-serif` **Source Serif 4** (editorial + program/course titles; stands in for
Bembo), `--font-mono` **IBM Plex Mono** (course codes, times, seats). Scale:
display 40 / serif-title 30 / h1 28 / h2 22 / h3 18 / body 16 / body-serif 17 /
body-sm 14 / code 14 / label 12. All comparable numbers use `tabular-nums`; course
codes are mono with `letter-spacing .02em`.

Spacing: 8px base — `0 4 8 12 16 20 24 32 40 48 64`; page gutter 24/16 (mobile);
card padding 20; grid gap 16. Radius: sm 6 / md 10 (inputs, buttons) / lg 14 (cards)
/ xl 20 (modals, drawers) / pill 999 (chips). Elevation: e1 `0 1px 2px rgba(16,27,48,.06)`
· e2 `0 4px 14px rgba(16,27,48,.10)` · e3 `0 16px 40px rgba(16,27,48,.18)`. Motion:
120/200/320ms, ease `cubic-bezier(.2,.8,.2,1)`; honour `prefers-reduced-motion`.

## Component inventory

Ported one-to-one from `04-component-library.md` (see that file for variants/states):

- **forms/** Button (primary/accent/secondary/ghost/danger/link · sm/md/lg · icon/loading/fullWidth),
  IconButton, Input, Textarea, Select, Combobox, Checkbox, Radio, Switch, Slider,
  RangeSlider, PasswordField (+ StrengthMeter)
- **feedback/** Badge, Tag, Chip (breadth + status), Callout, Toast, Tooltip, Dialog, EmptyState
- **display/** Avatar, Spinner, Skeleton, Divider, Kbd
- **navigation/** Tabs, Accordion, Stepper, FilterBar, BottomTabBar
- **overlay/** Drawer (right / bottom-sheet), DropdownMenu, CommandPalette (⌘K)
- **progress/** ProgressBar (+ segmented), ProgressRing, CreditMeter, StatTile, Sparkline,
  GPACard, **DegreeProgressCard** (Canvas growth tree — leafs out by completion %)
- **layout/** Wordmark (Deciduous's own leaf mark — NOT the U of T crest), TopBar, SideNav,
  ProgressStrip (the persistent credits · breadth · CGPA · degree strip), PageHeader, AppShell
- **data/** Card, CourseCard, TimetableGrid (day 1–5 + minutes model; conflict hatch; locked pin), DataTable
- **courses/** SeatMeter, SectionList (+ SectionRow), PrereqTree, RequirementMappingList, CourseDetailPanel
- **programs/** ProgramCard, ProgramHeader (with on-demand "Load requirements (Gemini)"), POStCombinationValidator
- **requirements/** RequirementCourseChip, RequirementGroupCard, BreadthTracker (+ `evaluateBreadth`), RequirementProgressList, DegreeAudit
- **plan/** PlanCourseCard, TermColumn, PlanBoard (HTML5 drag-drop), CourseRail, ValidationSummary, AutoPlanPanel
- **timetable/** SectionBlock, CourseTray, ScenarioTabs, OptimizerPanel, ScheduleCandidateList
- **account/** AuthCard, Dropzone, ImportPanel (+ ImportPreview), RecoveryCodeCard, DataExportMenu, DangerZone, ShareLinkDialog, NotificationPanel, ThemeToggle, DensityToggle

## Screens / views (recreate these)

All live in `ui_kits/deciduous/`. `index.html` is the authenticated app (AppShell +
SideNav routing); `auth.html` is the pre-auth flow. `data.js` holds the sample record.

1. **Auth** (`auth.html`) — centered AuthCard: email + PasswordField, "or", UTORid CTA;
   sign-up adds StrengthMeter + encryption note; reset warns it needs the recovery code.
2. **Onboarding** (`auth.html`) — 3-step Stepper: (1) ImportPanel (Upload PDF /
   Bookmarklet / Start blank) → ImportPreview; (2) confirm detected ProgramCards +
   POStCombinationValidator; (3) session + expected-grad Selects → Finish.
3. **Dashboard** (`screens/Dashboard.jsx`) — PageHeader; StatTile ×4 (credits, CGPA,
   breadth, degree); DegreeProgressCard growth tree; ProgramCard list; NotificationPanel;
   next-actions checklist; GPACard; full-width BreadthTracker.
4. **Requirements** (`screens/Requirements.jsx`) — ProgramHeader with "Load requirements
   (Gemini)" (async, ~10–20s, spinner+toast); "Only what's left" Switch; legend;
   RequirementGroupCards; DegreeAudit; per-program RequirementProgressList.
5. **Courses** (`screens/Courses.jsx`) — FilterBar (search + breadth Combobox + term);
   CourseCard grid; EmptyState; course opens a CourseDetailPanel in a right Drawer
   (Overview / Sections / Satisfies).
6. **Plan** (`screens/Plan.jsx`) — CourseRail (draggable) + PlanBoard of seasonal
   TermColumns (drag-drop, optimistic add + validate); ValidationSummary; AutoPlanPanel
   drawer → DiffPreview.
7. **Timetable** (`screens/Timetable.jsx`) — ScenarioTabs; CourseTray (one section per
   teach method, lockable); TimetableGrid (conflict = red hatch); Optimizer drawer
   (OptimizerPanel + ScheduleCandidateList).
8. **Settings** (`screens/Settings.jsx`) — ThemeToggle, DensityToggle, DataExportMenu,
   ShareLinkDialog, RecoveryCodeCard, DangerZone (typed-confirm).

## Interactions & behaviour

- **Theme** written to `data-theme` on `<html>`; all tokens flip; no per-component dark CSS.
- **⌘K / Ctrl-K** opens CommandPalette from anywhere (↑↓ navigate, Enter run, Esc close).
- **Drag-drop** on the plan board via HTML5 DnD (course code in `dataTransfer`); keep an
  accessible "Move to…" alternative; instant reflow under reduced motion.
- **Heavy async actions** (Gemini requirement reparse, optimize, import) are explicit,
  show loading, keep the UI interactive, and confirm via toast.
- **Timetable conflict** = interval overlap on the same day between two selected sections.
- Never encode status by colour alone — always pair icon + text (✔/◐/○/⚠).
- Every data surface needs loading (Skeleton) / empty (EmptyState) / error (Callout/Toast)
  / partial-stale / success states — see `07-states-interactions-a11y.md`.

## State & data

Bind screens to the real shapes and endpoints in `06-data-model-and-api.md`
(Course/Section/Program/RequirementGroup/StudentRecord; TTB + Academic Calendar +
Degree Explorer clients; Gemini requirement grouper). Credits derive from the code
suffix (H = 0.5, Y = 1.0). Sessions are fetched, never hard-coded (term digit: 1=Winter,
5=Summer, 9=Fall). Transcript/marks/plan are sensitive → encrypted at rest.
Validators must implement the rules in `09-uoft-degree-rules.md`
(20.0 total, ArtSci ≥10.0, 200+ ≥13.0, 300+ ≥6.0, ≤15.0 same-subject, ≥12.0 distinct
credits across programs, one-type-per-subject, breadth 4-of-5 / 3+2, CGPA ≥1.85).

## Assets & substitutions

- **Icons: Lucide** (CDN, 1.75px stroke, `currentColor`). Replace with your icon system;
  names used are Lucide names.
- **Fonts:** Archivo / Source Serif 4 / IBM Plex Mono are free stand-ins for U of T's
  commercial Trade Gothic + Bembo. If you license the originals, swap `tokens/fonts.css`
  and the `--font-*` stacks.
- **Logo:** Deciduous's own **leaf Wordmark** (drawn in `components/layout/Wordmark.jsx`).
  Do **not** reproduce the official U of T crest/wordmark. `assets/logo/uoft-crest.png`
  is the user-provided crest used only where the earlier `ui_kits/planner/` kit shows it.

## Files

- Tokens: `styles.css`, `tokens/*.css`
- Components: `components/<group>/*.{jsx,d.ts,prompt.md}`
- Screens: `ui_kits/deciduous/{index.html,auth.html,data.js,screens/*.jsx}`
- Specs (authoritative): `uploads/Deciduous-Claude-Design-Package/*.md`, `uploads/09-uoft-degree-rules.md`
- Design guide / index: `readme.md`; portable skill: `SKILL.md`
