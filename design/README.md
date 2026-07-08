# Deciduous — Claude Design Package

This package is a complete design brief for building the **Deciduous**
web UI in **Claude Design**. It is written so an AI design tool can generate a
coherent component library and screens, and so we can then build the real React
app directly from those components.

## What's in here

| File | Purpose |
|------|---------|
| `00-product-overview.md` | Vision, personas, goals, scope |
| `01-information-architecture.md` | Sitemap, navigation, routes, layout shell |
| `02-user-flows.md` | Step-by-step flows for every feature |
| `03-design-system.md` | Design tokens: color (light/dark), type, spacing, elevation, motion |
| `04-component-library.md` | Every component: variants, props, states, anatomy |
| `05-screens/` | Screen-by-screen specs with ASCII wireframes |
| `06-data-model-and-api.md` | Data shapes + the real backend API each screen binds to |
| `07-states-interactions-a11y.md` | Loading/empty/error, interactions, accessibility, responsive |
| `08-claude-design-brief.md` | The concise brief to paste into Claude Design first |

## How to use this with Claude Design

1. **Start** by pasting `08-claude-design-brief.md` — it sets the product,
   design language, and the design-system tokens in one shot.
2. **Generate the design system** first (colors, type, spacing, core primitives
   from `03` + `04`), then confirm it before screens.
3. **Generate components** from `04-component-library.md`, section by section
   (primitives → layout → domain components).
4. **Generate screens** from `05-screens/` — each screen names the exact
   components it composes, so the tool reuses, not reinvents.
5. **Send the resulting Claude Design package back to this repo**, and we build
   the React implementation against `06-data-model-and-api.md` (the live backend
   endpoints already exist).

## Ground truth: the backend already exists

The data layer is built and tested (see `../backend/`): Timetable Builder API
client, Academic Calendar course + program clients, a Gemini-powered requirement
grouper, a Degree Explorer transcript importer, and a local cache. `06-data-model-
and-api.md` maps each screen to those real data shapes so the UI is designed
against reality, not placeholders.

## Design principles (non-negotiable)

- **Clarity over cleverness.** Students under deadline pressure; every screen
  answers "what do I still need, and can I take it?"
- **Progress is always visible.** Credits, breadth, GPA, and per-program
  completion surface on the dashboard and persist in the shell.
- **Trustworthy + calm.** Academic tool; accessible (WCAG AA), light/dark,
  responsive to mobile. No dark patterns, no noise.
- **Fast.** Optimistic UI, skeleton loaders, cached data; heavy actions
  (LLM requirement parsing, schedule optimization) are explicit and async.
