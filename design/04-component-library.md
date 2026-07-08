# 04 — Component Library

Every component below is named so screens (05) can reference them and Claude
Design reuses rather than reinvents. Format: **Component** — variants · key props
· states. All components consume tokens from `03`; none hard-code colour.

## A. Primitives

- **Button** — variants: `primary` (U of T Blue fill), `accent` (Boundless), `secondary`
  (outline), `ghost`, `danger`, `link`. Sizes `sm/md/lg`. Props: `icon` (lead/trail),
  `loading`, `fullWidth`, `disabled`. States: hover, active, focus-visible (2px accent
  ring), loading (spinner + label), disabled.
- **IconButton** — square, `sm/md`. Tooltip on hover. Same variants.
- **Input** — text/number/email/password. Slots: label, `hint`, `error`, lead/trail
  icon, `prefix/suffix`. Password has reveal toggle + strength meter variant. States:
  default, focus (accent ring), error (danger border + message), disabled, readonly.
- **Textarea** — auto-grow, char counter optional.
- **Select** / **Combobox** — single/multi, searchable, async options, clearable, groups.
- **Checkbox**, **Radio**, **RadioGroup**, **Switch** — with label + description.
- **Slider** / **RangeSlider** — used for time-of-day preferences in the optimizer.
- **Chip / Tag** — variants: `neutral`, `breadth-BR1..BR5`, `status-*`, `removable`.
  Small pill; optional lead dot/icon. Used for breadth, requirement mapping, filters.
- **Badge** — count/status dot; `success/warning/danger/info/neutral`; `dot` or `label`.
- **Avatar** — image/initials, `sm/md/lg`, status ring.
- **Tooltip** — dark surface, 200ms delay, arrow. Keyboard accessible.
- **Spinner** / **Skeleton** — skeleton blocks for cards, rows, grid cells.
- **ProgressBar** — linear; `value/max`, label, `segmented` (multi-segment for breadth).
- **ProgressRing** — circular %, center label (e.g. "68%"); size `sm/md/lg`; color by status.
- **Meter / CreditMeter** — "13.5 / 20.0 credits" with a filled bar + tick at target.
- **Divider**, **Kbd** (keyboard hint), **Callout** (info/warning/success banner).

## B. Layout & navigation

- **AppShell** — composes TopBar + SideNav + PageContainer + ProgressStrip. Handles
  responsive collapse (rail → drawer → bottom-tabs).
- **TopBar** — wordmark, ⌘K search trigger, notifications bell, theme toggle, account menu.
- **SideNav** — item = icon + label + optional badge; `active` state (U of T Blue left
  bar + tinted bg). Collapsible to icon-rail.
- **BottomTabBar** (mobile) — 5 primary destinations.
- **ProgressStrip** — persistent bottom strip: Credits meter · Breadth n/5 · CGPA · Degree
  ring. Click → **ProgressPopover** with per-program mini-bars. Collapsible.
- **PageHeader** — title (Archivo h1), breadcrumbs, subtitle, right-aligned actions.
- **Card** / **Panel** — elevation e1, radius lg. Slots: header (title + actions), body, footer.
- **Tabs** — underline style; scrollable on overflow.
- **Accordion** — used for requirement groups & FAQ; chevron, animated height.
- **Table / DataTable** — sortable headers, sticky header, zebra (surface-sunken),
  row hover, selectable, `compact` density, empty state, pagination/infinite scroll.
- **Modal / Dialog** — e3, xl radius, scrim, focus-trap, `sm/md/lg`. Confirm variant.
- **Drawer / BottomSheet** — right drawer (desktop) / bottom sheet (mobile) for detail panels.
- **Popover / DropdownMenu** — e2; menu items with icons, dividers, destructive style.
- **Toast / Toaster** — bottom-right stack; `success/error/info/loading`; action link; auto-dismiss.
- **CommandPalette** (⌘K) — fuzzy search across courses/programs/actions; grouped results;
  keyboard nav; recent items.
- **EmptyState** — icon, headline, supportive line, primary action (e.g. "Import your record").
- **Stepper** — onboarding wizard; numbered steps with done/active/upcoming states.
- **FilterBar** — chips + selects for course/program filters; "clear all".
- **SearchTypeahead** — debounced input with async dropdown results (course/program).

## C. Domain components

### Courses
- **CourseCard** — code (mono) · title (serif-title small) · credit · breadth chip(s) ·
  term availability dot · status (planned/completed/available) · quick actions
  (Add to plan, Details). Compact row variant for lists.
- **CourseDetailPanel** — header (code + title + credit + campus), tabs or sections:
  *Overview* (description in body-serif, prereqs, coreqs, exclusions, breadth,
  distribution, hours), *Sections* (SectionList), *Requirements it satisfies*
  (RequirementMappingList). Footer actions: Add to plan, Add to timetable.
- **PrereqTree** — visualizes the prerequisite boolean logic (AND/OR groups, credit
  thresholds); met parts = success, unmet = tertiary, blocking = danger.
- **SectionList** — one **SectionRow** per LEC/TUT/PRA: name (mono), teach method chip,
  meeting times (mono, day + HH:MM), instructor, **SeatMeter** (current/max), waitlist
  badge, delivery mode. Radio/checkbox to select into timetable.
- **SeatMeter** — mini bar current/max; full = danger, near-full = warning; "12/60".

### Programs & requirements
- **ProgramCard** — code · name (serif-title small) · type badge (Specialist/Major/Minor) ·
  department · completion ring · "credits x/y" · actions (View, Add/Remove).
- **ProgramHeader** — name, code, type, department link, total credits, enrolment
  requirements callout, completion ring, "Load full requirements" (Gemini) action.
- **RequirementGroupCard** — heading · required credits · **ProgressBar** (earned/required)
  · course list where each = **RequirementCourseChip** (code, credits, status ✔/◐/○,
  per-course note tooltip) · group note · collapsible. "Only what's left" filter aware.
- **RequirementCourseChip** — code (mono) + credit + status icon; breadth-tinted or
  status-tinted; click → CourseDetailPanel.
- **BreadthTracker** — 5 segments (BR1–BR5) with earned/required per category + overall
  "n of 5 satisfied"; each segment uses its breadth colour; click filters courses by category.
- **RequirementMappingList** — for a course, the requirement groups (across enrolled
  programs) it can satisfy; shows program code + group heading chips.
- **POStCombinationValidator** — inline result when adding a program: valid/invalid
  combination, distinct-credit warnings, overlap notes.

### Progress & analytics
- **DegreeProgressCard** — big ProgressRing (degree %), credits meter, "on track" state,
  expected graduation.
- **GPAChip / GPACard** — CGPA (tabular), sessional/annual breakdown; trend **Sparkline**.
- **Sparkline / MiniAreaChart** — GPA-by-session; faint grid, area fill in accent,
  emphasized endpoint dot. (Charts follow a data-viz treatment: axis, subtle grid,
  endpoint emphasis — not raw lines.)
- **StatTile** — label + big number + delta; used in a KPI row (credits, GPA, courses, breadth).
- **RequirementProgressList** — per-program rows: name + ring + x/y credits + "view".

### Planning
- **PlanBoard** — horizontal scroll of **TermColumn**s (grouped by year). Drag-drop courses
  between terms. Header shows term credits + breadth added.
- **TermColumn** — session label (Fall 2026), credit subtotal, list of **PlanCourseCard**s,
  "+ add course" drop zone.
- **PlanCourseCard** — draggable; code + title + credit + status; validation badges
  (⚠ prereq, exclusion, not-offered) + requirement-satisfied tags (breadth/group colored).
- **CourseRail** — side panel: searchable course source to drag from; filter by "satisfies
  a remaining requirement".
- **AutoPlanPanel** — preferences + "Generate plan"; result = proposed term assignments with
  a **DiffPreview** (added/moved) to accept or edit.
- **ValidationSummary** — collapsible list of all plan issues (prereqs, exclusions,
  offerings) with jump-to links.

### Timetable
- **TimetableGrid** — weekly Mon–Fri (Sat optional) × time-of-day; **SectionBlock**s placed
  by day + start/end minutes; overlap = **ConflictBadge** + red hatch. Current-time line optional.
- **SectionBlock** — course code (mono) + section + room; colored per course; `locked` pin;
  hover shows instructor/seats; click to swap section.
- **CourseTray** — the term's planned courses with their selectable sections (grouped by
  teach method); "auto-pick" per course.
- **ScenarioTabs** — "Plan A / Plan B / +"; save/duplicate/delete schedule scenarios.
- **OptimizerPanel** — preference controls (days on campus, gap tolerance, earliest/latest
  time via RangeSlider, avoid days, allow-full toggle, keep-locked). "Generate".
- **ScheduleCandidateList** — ranked candidates: score, summary (days, gaps, first/last),
  mini grid preview; "Preview" / "Use this".

### Account & data
- **AuthCard** — centered card for sign in / sign up / reset; brand mark; form; alt-action link.
- **PasswordField** — reveal + **StrengthMeter**.
- **ImportPanel** — tabs: *Upload PDF* (Dropzone), *Bookmarklet* (steps + copy + paste
  JSON), *Manual*. Shows **ImportPreview** (detected programs + transcript diff) before apply.
- **Dropzone** — drag-drop file with progress.
- **RecoveryCodeCard** — shows/regenerates the encryption recovery code with copy + warning.
- **DataExportMenu** — CSV / JSON / plan PDF / ICS.
- **DangerZone** — delete account (double confirm with typed confirmation).
- **ShareLinkDialog** — generate/copy/revoke read-only link.
- **NotificationPanel** — list of alerts (deadline, prereq break, seat opened) with read state.
- **ThemeToggle**, **DensityToggle**.

## Component states (apply to all interactive components)
default · hover · focus-visible (2px `accent` ring, 2px offset) · active/pressed ·
selected · disabled · loading · error · empty. Every state must be visible in both themes.
