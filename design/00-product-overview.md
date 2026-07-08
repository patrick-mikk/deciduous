# 00 — Product Overview

## Vision

A web app that lets a University of Toronto (Arts & Science) student see their
**entire degree at a glance** and plan it with confidence: which programs they're
in, what each program still requires, which courses satisfy what, whether they
meet prerequisites, how their GPA is tracking, and a conflict-free timetable for
next term — all from live UofT data.

## Primary persona

**Priya, 2nd-year ArtSci student.** Enrolled in a Major + two Minors. Juggling
breadth requirements, prerequisites, and limited-enrolment programs. Wants to
answer, in under a minute: *"What do I take next term to stay on track, and does
it fit in my schedule?"* Comfortable on mobile and laptop. Stressed near
enrolment windows.

### Secondary personas
- **Academic advisor** — reviews a student's plan (read-only share link).
- **Prospective/incoming student** — explores programs and courses before ACORN access.

## Core jobs-to-be-done

1. **Know where I stand** — degree/program completion %, credits, breadth, CGPA.
2. **Plan forward** — assign courses to future terms; validate prereqs/exclusions.
3. **Understand requirements** — see each program's requirement groups and which
   courses satisfy them, with progress.
4. **Find courses** — search catalog + live offerings (sections, seats, times).
5. **Build a timetable** — pick sections, detect conflicts, optimize.
6. **Import my record** — pull transcript + progress from Degree Explorer.

## Feature scope

### Must-have (v1)
- Account: sign up / sign in / password reset (encrypted academic data at rest).
- Onboarding: import Degree Explorer record (PDF or bookmarklet), pick programs.
- Dashboard: degree progress, program cards, alerts, next actions.
- Programs: search/browse, program detail with requirement groups, enroll/manage.
- Requirements & progress: per-program requirement view, breadth tracker, "what's left".
- Course planning: term-by-term plan board, course search, course detail, add/move,
  prereq/exclusion validation, requirement mapping.
- Transcript: view, import, manual edit, GPA/CGPA.
- Timetable builder: weekly grid, section picking, conflict detection.
- Settings: account, data export, theme, sign out.

### Should-have (v1.x)
- Timetable **optimizer** (generate ranked conflict-free schedules by preferences).
- Auto-plan (suggest a term-by-term sequence satisfying requirements).
- Share plan (read-only link for advisors).
- Notifications (enrolment deadlines, prereq breaks, seat opening).

### Nice-to-have (later)
- Multiple "what-if" plan scenarios; program-swap comparison.
- Command palette (⌘K) global search/actions.
- Calendar export (ICS), degree-plan PDF export.
- Grade projection / GPA goal calculator.

## Non-goals (v1)
- Actual course **enrolment** (that's ACORN); we plan, not register.
- Non-ArtSci faculties (architecture supports it; content starts with ARTSC).
- Social features.

## Success signals
- A student can go from sign-up → imported record → a validated next-term plan
  with a conflict-free timetable in one sitting.
- "What do I have left?" is answerable in ≤2 clicks from anywhere.
