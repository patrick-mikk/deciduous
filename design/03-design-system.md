# 03 — Design System (Tokens)

Grounded in the **University of Toronto brand** (this is an *unofficial* student
tool — see note at bottom). The look is academic and precise: U of T Blue as the
signature, a cool blue-biased neutral ramp, and one deliberately vivid moment —
the five Arts & Science **breadth categories** as a colour spectrum, because that
spectrum is real degree structure, not decoration.

## Design rationale (the plan)

- **Colour.** *U of T Blue `#1E3765`* (PMS 655) is the primary and the only place
  the identity shouts; *Boundless Blue `#007FA3`* (UofT's secondary) is the
  interactive accent for links/selection. Neutrals are biased cool toward the
  blue (never pure grey). Semantic colours (success/warning/danger) are kept
  slightly desaturated so they read as *state*, not as a second brand. The
  breadth 5-hue spectrum is the one bold flourish, and it encodes information.
- **Type.** UofT's brand pairs **Trade Gothic** (grotesque) with **Bembo**
  (old-style serif). Both require commercial licences, so we evoke them with
  free faces: **Archivo** (a grotesque with Trade-Gothic bones) for UI/headings,
  **Source Serif 4** (Bembo-adjacent old-style serif) for editorial moments and
  large program/course titles, and **IBM Plex Mono** for course codes and times.
  This pairing is specific to UofT — not the default Inter-everywhere look.
- **Layout.** An academic "ledger": a persistent **ProgressStrip** anchors the
  shell like a degree audit line; hairline cool-grey rules, generous whitespace,
  and tabular figures for all the numbers a student actually compares.

## Colour — Light theme

### Neutrals / surfaces (cool, blue-biased — chosen, not default grey)
| Token | Hex | Use |
|-------|-----|-----|
| `bg` | `#FBFCFE` | app canvas |
| `surface` | `#FFFFFF` | cards, panels |
| `surface-sunken` | `#F2F4F7` | UofT Light Grey — wells, inputs, table stripes |
| `surface-hover` | `#EAEEF4` | hover on neutral surfaces |
| `border` | `#D8DFE9` | default borders (cool) |
| `border-strong` | `#BEC8D6` | emphasized dividers |
| `overlay` | `rgba(16,27,48,0.48)` | modal scrim |

### Text (dark blue-black, not pure black)
| Token | Hex | Use |
|-------|-----|-----|
| `text` | `#101B30` | primary text |
| `text-secondary` | `#45536B` | secondary |
| `text-tertiary` | `#6B7890` | captions, placeholders |
| `text-on-primary` | `#FFFFFF` | text on primary/accent fills |

### Brand + semantic
| Token | Hex | Hover | Use |
|-------|-----|-------|-----|
| `primary` | `#1E3765` | `#16294C` | **U of T Blue** — primary actions, active nav, headers |
| `accent` | `#007FA3` | `#006A88` | **Boundless Blue** — links, selection, focus, secondary CTAs |
| `success` | `#1E7A47` | `#155E37` | completed, prereq met |
| `warning` | `#A96A00` | `#875400` | not offered this term, caution |
| `danger` | `#BC3A2E` | `#992D24` | exclusion conflict, destructive |
| `info` | `#255F9C` | `#1D4C7E` | neutral info |
| Tint bgs | `success-bg #E3F1E9` · `warning-bg #F8EEDB` · `danger-bg #FAE6E4` · `info-bg #E5EDF7` · `primary-bg #E5E9F1` | | soft status backgrounds |

### Breadth-category spectrum (the 5 ArtSci categories — the one bold moment)
Used in the breadth tracker, requirement tags, course badges, and charts.
| # | Category | Hex | Bg (light) |
|---|----------|-----|-----|
| BR1 | Creative & Cultural Representation | `#7A4FB5` | `#EEE7F7` |
| BR2 | Thought, Belief & Behaviour | `#B26A12` | `#F7EEDD` |
| BR3 | Society & its Institutions | `#1E6FA8` | `#E3EDF6` |
| BR4 | Living Things & Their Environment | `#2E7D46` | `#E4F0E8` |
| BR5 | The Physical & Mathematical Universes | `#0E7E92` | `#DCEEF1` |

### Status semantics (consistent everywhere)
Completed = `success` (✔) · Planned = `accent` (◐) · Available/unmet = `text-tertiary` (○)
· Blocked (prereq/exclusion) = `danger` (⚠) · Not offered = `warning`.

## Colour — Dark theme (same token names; lighten brand for contrast)
| Token | Hex |
|-------|-----|
| `bg` | `#0B1220` |
| `surface` | `#121B2B` |
| `surface-sunken` | `#0E1524` |
| `surface-hover` | `#1B2637` |
| `border` | `#26344A` |
| `border-strong` | `#38495F` |
| `text` | `#E9EEF7` |
| `text-secondary` | `#AEBACC` |
| `text-tertiary` | `#7E8CA1` |
| `primary` | `#5E8FD1` (hover `#7AA5DC`) — lightened U of T Blue for dark grounds |
| `accent` | `#33A8C9` (hover `#54B8D4`) — lightened Boundless Blue |
| `success` | `#46B074` · `warning` `#D19A3B` · `danger` `#E0685D` · `info` `#5B98D6` |
| Breadth (dark) | BR1 `#A98BDD` · BR2 `#DA9A46` · BR3 `#5F9BDD` · BR4 `#57BE7E` · BR5 `#3FB6CB` |

Theme is token-level: define on `:root`, override tokens under
`@media (prefers-color-scheme: dark)`, then `:root[data-theme="dark"]` /
`:root[data-theme="light"]` win in both directions. Never style inside the media query.

## Typography
- **Faces** (free stand-ins for UofT's Trade Gothic + Bembo):
  - **Archivo** — grotesque; UI, labels, headings. (Evokes Trade Gothic; use 600–800 for headlines, condensed optical for big titles.)
  - **Source Serif 4** — old-style serif; editorial/marketing copy, hero titles, large program & course names. (Evokes Bembo; used with restraint.)
  - **IBM Plex Mono** — course codes, session codes, meeting times, seat counts.
- **Scale** (size / line-height / weight / face):
  | Token | Size px | LH | Weight | Face | Use |
  |-------|---------|----|--------|------|-----|
  | `display` | 40 | 1.1 | 800 | Archivo | landing hero |
  | `serif-title` | 30 | 1.15 | 600 | Source Serif 4 | program/course hero titles |
  | `h1` | 28 | 1.2 | 700 | Archivo | page titles |
  | `h2` | 22 | 1.25 | 700 | Archivo | section headers |
  | `h3` | 18 | 1.3 | 600 | Archivo | card titles |
  | `body` | 16 | 1.55 | 400 | Archivo | default UI/body |
  | `body-serif` | 17 | 1.6 | 400 | Source Serif 4 | descriptions, editorial |
  | `body-sm` | 14 | 1.45 | 400 | Archivo | dense tables |
  | `label` | 12 | 1.35 | 600 | Archivo | uppercase labels, `letter-spacing .06em` |
  | `code` | 14 | 1.4 | 500 | IBM Plex Mono | codes/times |
- Course codes: **mono**, `text` colour, `letter-spacing .02em`. All aligned
  numerals use `font-variant-numeric: tabular-nums`.

## Spacing — 8px base
`0 · 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64`. Page gutter 24 / 16 (mobile);
card padding 20; grid gap 16.

## Radius
`sm 6 · md 10 · lg 14 · xl 20 · pill 999`. Cards `lg`, inputs/buttons `md`,
chips/badges `pill`, modals/drawers `xl`.

## Elevation
`e1 0 1px 2px rgba(16,27,48,.06)` (cards) · `e2 0 4px 14px rgba(16,27,48,.10)`
(popovers) · `e3 0 16px 40px rgba(16,27,48,.18)` (modals). Dark: `rgba(0,0,0,.5)`
+ 1px top inner-highlight.

## Motion
`fast 120 · base 200 · slow 320` ms, ease `cubic-bezier(.2,.8,.2,1)`. Progress
fills, drawer/modal enter, drag reflow. Honour `prefers-reduced-motion`.

## Iconography
Line icons, 1.75px stroke, 20px. Lucide-style. Domain glyphs: ✔ completed,
◐ planned, ○ available, ⚠ conflict, 🎓 degree, 📅 timetable, 🧭 breadth.

## Layout & breakpoints
Content max-width 1200 (dashboard) / 1440 (plan & timetable boards). Breakpoints
`sm 640 · md 768 · lg 1024 · xl 1280`. Grid 12/8/4 col. Density: comfortable / compact.

## Brand identity — Deciduous

The name is the concept. **Deciduous** trees are *seasonal* and *branching* —
which is exactly how a UofT degree works:

- **Seasons = terms.** Fall / Winter / Summer sessions are the deciduous cycle.
  The plan board's columns are literally seasons; term icons can carry a subtle
  seasonal leaf state (green Fall → bare Winter → new-growth Summer).
- **The tree = the degree.** Trunk = your degree, **branches = requirement
  groups / programs**, **leaves = courses** (a leaf fills in when a course is
  completed). This is the signature visual, not a decorative logo.
- **Growth = progress.** The **DegreeProgressCard** is a stylized tree that
  leafs out as credits/requirements complete — a memorable, information-bearing
  hero for the dashboard (Canvas-drawn, not hand-authored SVG).

### Wordmark & mark
- **Wordmark:** "Deciduous" set in **Archivo** (600), lowercase-friendly, with a
  small **leaf/branch mark** to its left in `primary` (U of T Blue). The mark
  doubles as the favicon and the collapsed-nav logo.
- Do **not** reproduce the official U of T coat of arms or wordmark. U of T Blue
  + academic type give institutional *affinity*; the tree mark makes it *Deciduous*.

### Seasonal accent (brand/illustration only — NOT UI semantics)
A warm **autumn** ramp is reserved for brand moments (empty-state trees, the
growth-tree leaves, onboarding art) so the blue UI stays calm:
`leaf-green #3E8E5A · leaf-amber #C7861F · leaf-rust #B4542B`. These never carry
UI state — status stays success/warning/danger; the accent stays Boundless Blue.

### Signature moments
- **Empty states** show a bare branch that leafs in once the student imports/plans.
- **Load/transition**: a few leaves settle (≤400ms, opt-out under
  `prefers-reduced-motion`); never gratuitous.
- **Voice:** calm, plain, encouraging — "what's left, and can you take it?" Never
  alarmist. Tagline candidates: *"Plan your degree by the seasons."*

### Brand honesty
Persistent quiet line in footer/settings: *"Deciduous is an unofficial student
tool. Not affiliated with or endorsed by the University of Toronto."*
