# 01 — Information Architecture

## Sitemap

```
Public
├── / (Landing / marketing)
├── /signin
├── /signup
├── /reset-password  (request + set-new via token)
└── /share/:token    (read-only shared plan, no auth)

Authenticated (App shell)
├── /onboarding            (first-run wizard; import + program select)
├── /dashboard             (home: progress overview, alerts, next actions)
├── /programs
│   ├── /programs                (search / browse programs)
│   ├── /programs/:code          (program detail + requirements)
│   └── /programs/mine           (enrolled programs manager)
├── /requirements
│   ├── /requirements            (degree + program progress overview)
│   └── /requirements/:code      (one program's requirement groups + progress)
├── /plan                  (term-by-term plan board)
├── /courses
│   ├── /courses                 (course search)
│   └── /courses/:code           (course detail: catalog + live sections)
├── /transcript            (transcript view + import + edit)
├── /timetable
│   ├── /timetable               (weekly builder)
│   └── /timetable/optimize      (optimizer results)
├── /settings              (account, data, appearance)
└── /help                  (guides, import instructions, FAQ)
```

## App shell (authenticated layout)

```
┌───────────────────────────────────────────────────────────────────────────┐
│ TopBar:  [☰]  Deciduous        ⌘K Search      🔔  ◐ theme  ▾Avatar │
├──────────────┬────────────────────────────────────────────────────────────┤
│ SideNav      │  PageHeader: Title · breadcrumbs · primary actions          │
│ (icons+text) │  ────────────────────────────────────────────────────────  │
│  ▸ Dashboard │                                                            │
│  ▸ Programs  │   PAGE CONTENT (scrolls; max-width container, responsive)   │
│  ▸ Require.. │                                                            │
│  ▸ Plan      │                                                            │
│  ▸ Courses   │                                                            │
│  ▸ Transcript│                                                            │
│  ▸ Timetable │                                                            │
│  ─────────   │                                                            │
│  ▸ Settings  │                                                            │
│  ▸ Help      │                                                            │
├──────────────┴────────────────────────────────────────────────────────────┤
│ ProgressStrip (persistent, collapsible): Credits 13.5/20 · Breadth 4/5 ·   │
│                CGPA 2.70 · Degree 68%                              [details]│
└───────────────────────────────────────────────────────────────────────────┘
```

- **SideNav** collapses to icon-rail on tablet, becomes a bottom tab bar / drawer on mobile.
- **ProgressStrip** is the signature persistent element — degree/credits/breadth/GPA
  always visible; expands to a popover with per-program mini-bars.
- **⌘K command palette** — global: jump to a course/program, add a course, run optimizer.

## Navigation model
- Primary nav = the 8 sections in SideNav.
- Secondary nav = tabs within a section (e.g. Programs: Browse / My Programs).
- Contextual nav = breadcrumbs in PageHeader + back affordances in detail panels.
- Deep entities (course, program) open as **routed detail pages** on desktop and
  as **bottom sheets / full-screen drawers** on mobile.

## Global surfaces
- **Toasts** (bottom-right) for async results (import complete, schedule optimized).
- **Command palette** (⌘K / Ctrl-K).
- **Notification center** (bell → dropdown panel).
- **Account menu** (avatar → profile, settings, sign out).
