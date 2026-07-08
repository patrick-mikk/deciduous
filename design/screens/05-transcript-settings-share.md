# Screens — Transcript, Settings, Share, Help

## Transcript (`/transcript`)
```
PageHeader: "Transcript"   [ Import ] [ + Add course ] [ Export ▾ ]
┌ GPA summary (StatTile row) ──────────────────────────────────────┐
│ CGPA 2.70 │ This session 2.33 │ Credits earned 13.5 │ Trend ▁▂▃▂▄  │
└───────────────────────────────────────────────────────────────────┘
DataTable (grouped by session, newest first):
  Session         Course     Title                 Cr   Mark  Grade
  ── Fall 2024 ──────────────────────  Sessional GPA 2.33 · Cum 2.70
     POL208H1   Intro to IR            0.5   78    B+
     STA220H1   The Practice of Stats  0.5   65    C+   (Extra)
  ── Winter 2025 ─────────────────────  Sessional GPA 3.42 · Cum 2.77
     …
Row actions: edit (mark/grade/status), remove. Special grades (CR/NCR/P/LWD/…)
render as chips, excluded from GPA.
GPA projector (panel): enter target grades for in-progress/planned → projected CGPA.
```
Data: `GET /api/me/transcript` (TranscriptCourse[] with per-session GPA); import
merges from Degree Explorer (PDF/bookmarklet). Sensitive → encrypted at rest.

## Settings (`/settings`) — tabbed
```
Tabs: [ Profile ] [ Security ] [ Data ] [ Appearance ] [ Notifications ]
Profile:   name, email, current session, expected graduation.
Security:  change password · RecoveryCodeCard (encryption recovery) · sessions.
Data:      re-import · DataExportMenu (CSV/JSON/plan PDF/ICS) · DangerZone (delete).
Appearance: ThemeToggle (system/light/dark) · DensityToggle · leaf-motion on/off.
Notifications: toggles for deadlines, prereq breaks, seat-opened alerts.
```
- **RecoveryCodeCard** explains why it matters (password reset re-encrypts data)
  with a copy button and "regenerate" (warns it invalidates the old code).

## Shared plan (`/share/:token`) — public, read-only
A stripped shell (no SideNav edit affordances): DegreeProgressCard, BreadthTracker,
read-only PlanBoard, RequirementProgressList. Banner: "Read-only shared view."
Owner can revoke via ShareLinkDialog in Settings/Plan.

## Help (`/help`)
Accordion FAQ + step-by-step import guides (PDF & bookmarklet with the exact
`<degree-explorer-capture>` instructions) + a "what the statuses mean" legend.

## Global: Command palette (⌘K)
```
┌ ⌘K ────────────────────────────────────────┐
│ 🔍 type a course, program, or action…       │
│  Courses    POL208H1 · Intro to IR          │
│  Programs   ASMAJ2660 · Public Policy Major │
│  Actions    ▸ Add course to plan            │
│             ▸ Optimize timetable            │
│             ▸ Import record                 │
└─────────────────────────────────────────────┘
```

## Global: Notifications (bell → NotificationPanel)
List of AlertRow: type icon (deadline/prereq/seat), message, time, read state;
"mark all read"; click routes to the relevant screen.
