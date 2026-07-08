# 07 — States, Interactions, Accessibility, Responsive

## Universal states (every data surface must design all five)
1. **Loading** — skeletons that match final layout (CourseCard rows, grid cells,
   rings). Never a bare spinner for full pages.
2. **Empty** — EmptyState with the Deciduous bare-branch motif, a one-line reason,
   and the primary next action ("Import your record", "Add a program").
3. **Error** — inline, human: what failed + how to fix + retry. Never a raw stack
   trace or an apology. Toast for transient; Callout for persistent.
4. **Partial / stale** — cached data shown with a subtle "updated 2h ago · refresh".
5. **Success** — optimistic update + confirming toast ("Added POL208H1 to Fall 2026").

## Key interactions
- **Drag & drop (plan board):** grab handle on PlanCourseCard; drop zones highlight;
  invalid drops (exclusion) show a red drop preview + reason; keyboard alternative
  (select card → "Move to…" menu). Reduced-motion: instant reflow.
- **Async heavy actions** (Gemini reparse, optimize, import): button → loading state,
  progress toast, result toast; UI stays interactive; cancellable where possible.
- **Selection (timetable):** one section per teach-method; picking a new LEC deselects
  the old; locked sections excluded from auto-pick/optimize.
- **Inline validation:** prereq/exclusion/offering badges appear on the card the
  moment it enters a term; tooltip explains and links to the blocker.
- **Command palette (⌘K):** open from anywhere; Esc closes; ↑↓ navigate; Enter runs.

## Accessibility (WCAG 2.1 AA)
- **Contrast:** all text ≥ 4.5:1 (≥3:1 for ≥18px bold); status never encoded by
  colour alone — pair with icon/label (✔/◐/○/⚠) and text.
- **Keyboard:** every action reachable; visible focus ring (2px `accent`, 2px offset);
  logical tab order; focus trap in modals/drawers; Esc closes overlays.
- **Screen readers:** semantic landmarks (nav/main/aside), labelled controls,
  `aria-live=polite` for search results and async toasts, progress bars expose
  `aria-valuenow/max`. Course codes read naturally ("P O L 208 H 1" via aria-label).
- **Motion:** honour `prefers-reduced-motion` — disable leaf animations, drag reflow
  transitions, ring fills.
- **Targets:** ≥44×44px touch targets; adequate spacing on the plan board and grid.
- **Forms:** labels always visible (not placeholder-only); errors tied to inputs via
  `aria-describedby`.

## Responsive behaviour
| Breakpoint | Shell | Notable adaptations |
|-----------|-------|---------------------|
| `≥1280 xl` | SideNav expanded + ProgressStrip | Plan board & timetable full multi-column |
| `1024 lg` | SideNav icon-rail | Detail opens as right Drawer |
| `768 md` | Drawer nav | Plan board = 1–2 terms visible, horizontal scroll; timetable scrolls |
| `<640 sm` | BottomTabBar (5 dests) | Course/program detail = full-screen sheet; tables → stacked cards; timetable = day-at-a-time swipe; ProgressStrip collapses to a single tappable summary |

- Tables reflow to stacked key/value cards on mobile.
- The plan board and timetable grid always keep their own `overflow-x: auto` container
  so the page body never scrolls sideways.
- Charts/sparklines scale down but keep endpoint emphasis + axis labels.

## Performance & feel
- Optimistic UI for add/move/remove; reconcile on server response.
- Skeleton-first; cache-backed lists render instantly then refresh.
- Debounce typeahead (200ms); virtualize long course lists.
- The one-time session course-sync and the Gemini reparse are the only "slow"
  operations — always explicit, async, and cancellable, never blocking the shell.
