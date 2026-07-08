# 06 — Data Model & API Mapping

The backend data layer already exists (`../backend/`). This maps each UI concept
to a real shape so the design binds to reality. Types shown as TypeScript for the
React client; they mirror the Python dataclasses in `backend/data_sources/models.py`.

## Core types

```ts
type Term = "F" | "S" | "Y";                 // Fall / Winter(Spring) / Year
type SessionCode = string;                   // "20269"=Fall 2026, "20271"=Winter 2027, "20265"=Summer 2026

interface MeetingTime { day: 1|2|3|4|5|6|7;  // ISO Mon..Sun
  startMin: number; endMin: number;          // minutes since midnight (render HH:MM)
  building: string; session: SessionCode; }

interface Instructor { first: string; last: string; }

interface Section {
  name: string;            // "LEC0101"
  teachMethod: "LEC"|"TUT"|"PRA";
  sectionNumber: string;
  currentEnrol: number; maxEnrol: number; waitlist: number;
  instructors: Instructor[];
  meetingTimes: MeetingTime[];
  deliveryModes: string[];
}

interface Course {
  code: string;            // "POL208H1"
  title: string; sectionCode: Term; credit: number;   // 0.5 / 1.0
  campus: string;
  description: string; prerequisites: string; corequisites: string; exclusions: string;
  breadth: string[];       // e.g. ["Society and its Institutions (3)"]
  distribution: string[];
  sections: Section[];     // live TTB offerings (empty for calendar-only)
}

interface RequirementCourse { code: string; credits: number; notes: string; }
interface RequirementRule { credits: number; description: string; courseCodes: string[]; }
interface RequirementGroup {
  heading: string;         // "First Year", "Group A: ...", "" = intro/ungrouped
  credits: number;         // credits this group requires
  isNote: boolean;
  courseCodes: string[];
  rules: RequirementRule[];
  courses: RequirementCourse[];  // per-course credit + notes (from Gemini grouper)
  notes: string;           // group-level note
}
interface Program {
  code: string;            // "ASMAJ1305A"
  title: string; programType: "specialist"|"major"|"minor"|""; department: string;
  departmentUrl: string; enrolmentRequirements: string;
  totalCredits: number; completionRequirements: RequirementGroup[]; rawCompletionText: string;
}

// student record (from Degree Explorer import; sensitive → encrypted at rest)
interface TranscriptCourse { code: string; title: string; credits: number;
  mark: number|null; grade: string; session: string; status: "completed"|"in_progress"|"planned"|"extra"; }
interface RequirementProgress { key: string; label: string; status: "complete"|"incomplete"|"na";
  earned: number; required: number; appliedCourses: string[]; }
interface StudentRecord {
  programs: { code: string; name: string; startSession: string }[];
  transcript: TranscriptCourse[];
  requirementProgress: Record<string, RequirementProgress[]>;  // by program code
  cgpa: number;
}
```

## Screen → endpoint map (proposed REST; backend clients already produce these shapes)

| UI area | Endpoint(s) | Backed by |
|--------|-------------|-----------|
| Auth | `POST /api/auth/signup` · `/signin` · `/reset` | Flask auth (ADR-0004) |
| Import | `POST /api/import/pdf` · `POST /api/import/capture` | Degree Explorer PDF parser + bookmarklet normalizer |
| Program search | `GET /api/programs?q=&type=&subject=&page=` | `ProgramClient` (Academic Calendar) |
| Program detail | `GET /api/programs/:code` | `ProgramClient` |
| Program requirements | `GET /api/programs/:code/requirements` | heuristic parser + **on-demand Gemini grouper** (`POST /api/programs/:code/requirements/reparse`) |
| Course search | `GET /api/courses?q=&level=&breadth=&term=&hasSeats=` | SQLite cache over TTB session sync |
| Course detail | `GET /api/courses/:code` | TTB (`getCoursesByCodeAndSectionCode`) + calendar |
| Sessions | `GET /api/sessions` (current session list) | TTB `/reference-data` |
| Plan | `GET/PUT /api/plan` · `POST /api/plan/validate` · `POST /api/plan/autoplan` | planner engine + prereq/exclusion/offering checks |
| Requirements progress | `GET /api/me/requirements` | transcript × program requirements |
| Transcript / GPA | `GET /api/me/transcript` (encrypted) | StudentRecord |
| Timetable | `GET /api/plan/:term/sections` · `POST /api/timetable/optimize` | TTB sections + optimizer |
| Summary/alerts | `GET /api/me/summary` · `/api/me/alerts` | aggregate |
| Share | `POST /api/share` → `GET /api/share/:token` | read-only snapshot |

## Behaviours the UI must honor (from the real data)
- **Requirement grouping is on-demand.** Program requirements come back heuristically
  segmented instantly; the **"Load/Reload requirements (Gemini)"** action re-parses one
  program via the LLM grouper (≈10–20s, async → spinner + toast). Cache-first: once
  loaded, it's instant. Per-course credits + notes only appear after LLM grouping.
- **Sessions:** never hard-code; fetch current sessions. Codes end in a term digit
  (1=Winter, 5=Summer, 9=Fall). Default term = Fall.
- **Empty search ≠ error.** TTB returns HTTP 404 for "no matches" — show EmptyState.
- **Timetable conflict** = interval overlap on the same `day` between two selected
  sections' meetingTimes.
- **Credits** derive from the code suffix (H=0.5, Y=1.0); always show as tabular nums.
- **Sensitive data** (transcript, marks, plan) is encrypted at rest and unlocked by the
  session; never render it on the public `/share` view beyond what the owner opted to share.
