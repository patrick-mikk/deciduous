# 02 — User Flows

Notation: **→** step, **⟳** async, **⚠** validation/error branch.

## F1. Create account & onboard
1. Landing → "Get started" → **/signup**.
2. Enter email + password (strength meter) → agree to terms → Create account.
   - ⚠ Weak password / email taken → inline error.
3. ⟳ Email verification sent → verify (or "skip for now", limited).
4. **/onboarding** wizard (stepper, 3 steps):
   1. **Import your record** — three options:
      - Upload **Degree Explorer PDF** (drag-drop) → ⟳ parse → preview transcript+programs.
      - Run **bookmarklet** on Degree Explorer (instructions + copy button) → paste JSON.
      - **Start blank** (enter later).
   2. **Confirm programs** — detected programs shown as cards; add/remove; search to add more.
   3. **Set your term** — current session (e.g. Fall 2026) + expected graduation.
5. → Land on **/dashboard** with progress populated.

## F2. Sign in
1. **/signin** → email + password → Sign in.
   - ⚠ Wrong creds → error; rate-limited after N tries.
   - Password unlocks the **encryption key** for academic data (see 06 / ADR-0005).
2. "Forgot password" → **/reset-password** → email link → set new password.
   - ⚠ Note: password reset requires the recovery code (data-key rewrap) — warn if absent.

## F3. Add / manage a program (POSt)
1. **/programs** → search "geographic" or filter by type (Specialist/Major/Minor) & subject.
2. Result list of **ProgramCard**s → open **/programs/:code**.
3. Program detail: overview, enrolment requirements, **requirement groups** (with a
   "Load full requirements" action that runs the Gemini grouper if not cached ⟳).
4. "Add to my programs" → ⟳ validates POSt combination (e.g. valid Major+Minor+Minor).
   - ⚠ Invalid combination or credit-overlap warning → explain, allow override.
5. **/programs/mine** manages enrolled programs (reorder priority, remove).

## F4. Understand requirements & progress
1. **/requirements** → degree-level requirements + a card per enrolled program with a
   completion ring and credits x/y.
2. Open a program → **/requirements/:code**: list of **RequirementGroupCard**s, each:
   heading, required credits, progress bar, and the courses that satisfy it
   (✔ completed / �course planned / ○ available), plus per-course credits + notes.
3. Toggle "Show only what's left" → hides satisfied groups/courses.
4. Any course chip → opens **CourseDetailPanel**; "Add to plan" from there.

## F5. Plan courses (term-by-term)
1. **/plan** → board with columns per session (Fall / Winter / Summer) across years.
2. Search or drag a course from the **Course rail** into a term.
   - ⟳ On drop: validate prereqs (met by earlier-term/completed courses),
     exclusions (conflict with another planned/completed course), offering
     availability (is it offered that session?), and requirement mapping.
   - ⚠ Prereq unmet → warning badge on the card + tooltip listing the missing prereq.
   - ⚠ Exclusion → red badge; ⚠ not offered that term → amber badge.
3. Card shows which requirement group(s) it satisfies (colored tags).
4. "Auto-plan" (should-have) → ⟳ proposes a sequence to fill remaining requirements →
   preview diff → accept/adjust.
5. Plan autosaves; "term summary" shows credits + breadth added per term.

## F6. Find a course
1. **/courses** → typeahead search (code or title). Filters: level, breadth, credit,
   term, day/time, has-seats.
2. **CourseCard** results → open **/courses/:code**.
3. Detail: description, prerequisites, corequisites, exclusions, breadth,
   distribution, and **live sections** (LEC/TUT/PRA) with instructor, meeting times,
   seats (current/max), waitlist. Actions: Add to plan, Add to timetable.

## F7. Build a timetable
1. **/timetable** → choose term → the planned courses for that term appear as a
   **course tray** with their sections.
2. Select one section per required teach-method (LEC/TUT/PRA); blocks render on the
   **weekly grid**. ⚠ Conflicts highlighted (overlapping blocks) with a conflict list.
3. Seat/waitlist indicators per section; "locked" sections stay fixed.
4. Save multiple **scenarios** (e.g. "Plan A", "Plan B").

## F8. Optimize a timetable
1. From /timetable → "Optimize" → **/timetable/optimize**.
2. Set preferences: preferred days/times, minimize gaps / days on campus, avoid early
   mornings, keep locked sections, allow-full toggle.
3. ⟳ Generate → ranked list of conflict-free schedule candidates (score + summary).
4. Preview each on the grid → "Use this" → returns to builder with sections applied.

## F9. Transcript & GPA
1. **/transcript** → table of courses (code, title, credits, mark, grade, session, GPA).
2. Import (PDF/bookmarklet) merges/updates; manual add/edit a course.
3. Sessional / annual / cumulative GPA shown; "GPA projector" lets you enter target
   grades for in-progress/planned courses to see resulting CGPA.

## F10. Share with an advisor
1. Settings or plan → "Share read-only" → ⟳ generate **/share/:token** link.
2. Advisor opens link (no auth) → read-only dashboard + plan + requirements.
3. Revoke link anytime.

## F11. Settings & data
1. **/settings**: profile (name/email), password, **encryption/recovery code**,
   appearance (theme, density), notifications.
2. Data: export (CSV / JSON / plan PDF / ICS), re-import, **delete account** (double-confirm).
