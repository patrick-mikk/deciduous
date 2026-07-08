# Documentation index

Structured docs for the UofT Degree Planner. Start with [`../AGENTS.md`](../AGENTS.md)
for the project overview and agent instructions; this tree holds the detail that
`AGENTS.md` deliberately keeps out (progressive disclosure — read what a task needs).

| Doc | Read it when you need… |
|-----|------------------------|
| [architecture.md](architecture.md) | the system shape: layers, data flow, components |
| [conventions.md](conventions.md) | how to write code/tests/config in this repo |
| [roadmap.md](roadmap.md) | what's built, what's next, phase order |
| [decisions/](decisions/) | why a choice was made (ADRs) — read before reversing one |
| [../backend/docs/TTB_API_REFERENCE.md](../backend/docs/TTB_API_REFERENCE.md) | the Timetable Builder API contract |

## Maintaining these docs

- **Pointers over copies.** Reference `file:line` instead of pasting code; copies rot.
- Keep `AGENTS.md` under ~150 lines. Detail belongs here, linked from there.
- A significant/irreversible choice → add an ADR (see [decisions/README.md](decisions/README.md)).
- Update the relevant doc in the same change that makes it stale.
