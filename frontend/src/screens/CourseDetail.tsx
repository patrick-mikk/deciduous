import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Drawer, CourseDetailPanel, Skeleton, EmptyState, Callout, Toast, Button } from "@/ds";
import type { CourseDetail as DsCourseDetail, PrereqNode, RequirementMapping } from "@/ds";
import { api } from "@/api";
import type { BreadthKey, Course } from "@/api";

/**
 * Course detail — routed at "/courses/:code" (design/screens/03-programs-and-courses.md
 * "Course detail: drawer on mobile, page on desktop"). Implemented as an
 * always-open Drawer over the route so navigating here from Courses (or
 * deep-linking directly) reads as the same drawer pattern either way; closing
 * it navigates back to "/courses".
 *
 * Composes the design system's CourseDetailPanel (which owns the
 * Overview/Sections/Satisfies tabs, PrereqTree and SectionList/SeatMeter
 * internally) — this screen's job is only to fetch the course and shape it
 * into that component's `CourseDetail` prop.
 */

/** "Society and Its Institutions (3)" -> "BR3". */
function breadthKeyFromLabel(label: string): BreadthKey | undefined {
  const m = /\((\d)\)\s*$/.exec(label);
  if (!m) return undefined;
  const key = `BR${m[1]}`;
  return key === "BR1" || key === "BR2" || key === "BR3" || key === "BR4" || key === "BR5"
    ? (key as BreadthKey)
    : undefined;
}

// Best-effort prerequisite text -> PrereqTree parser. Real structured prereqs
// are a backend concern (validators, design/09) — this is a display-only
// approximation of the raw `Course.prerequisites` string for the Overview tab.
const COURSE_CODE_RE = /^[A-Za-z]{3,6}\d{3}[A-Za-z]\d$/;

function isCourseCode(token: string): boolean {
  return COURSE_CODE_RE.test(token.trim());
}

function parseLeaf(token: string, completed: Set<string>): PrereqNode {
  const t = token.trim().replace(/^[.;]+|[.;]+$/g, "");
  if (isCourseCode(t)) {
    const code = t.toUpperCase();
    return { type: "course", code, met: completed.has(code) ? true : undefined };
  }
  return { type: "credits", text: t };
}

function parseAndBranch(text: string, completed: Set<string>): PrereqNode | undefined {
  const items = text
    .split(/[,/]/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (items.length === 0) return undefined;
  if (items.length === 1) return parseLeaf(items[0], completed);
  return { type: "group", op: "AND", children: items.map((i) => parseLeaf(i, completed)) };
}

function parsePrereqText(text: string, completed: Set<string>): PrereqNode | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  const orBranches = trimmed
    .split(/\bor\b/i)
    .map((s) => s.trim().replace(/^,+|,+$/g, "").trim())
    .filter(Boolean);
  if (orBranches.length <= 1) return parseAndBranch(trimmed, completed);
  const children = orBranches
    .map((b) => parseAndBranch(b, completed))
    .filter((n): n is PrereqNode => Boolean(n));
  if (children.length === 0) return undefined;
  if (children.length === 1) return children[0];
  return { type: "group", op: "OR", children };
}

interface Derived {
  prereqTree?: PrereqNode;
  satisfies: RequirementMapping[];
}

/** "Satisfies" = requirement groups (across my enrolled programs) whose course
 * list includes this course, plus any breadth categories it carries. Both
 * lookups are non-fatal — guests (or a program whose requirements fail to
 * parse) just see fewer/no mappings, not an error. */
async function buildDerived(course: Course): Promise<Derived> {
  const completed = new Set<string>();
  const mappings: RequirementMapping[] = [];

  try {
    const record = await api.getMyRecord();
    for (const t of record.transcript) {
      if (t.status === "completed" || t.status === "in_progress") completed.add(t.code.toUpperCase());
    }
    for (const p of record.programs) {
      try {
        const groups = await api.getProgramRequirements(p.code);
        for (const g of groups) {
          const inGroup = g.courseCodes.includes(course.code) || g.courses.some((c) => c.code === course.code);
          if (inGroup) mappings.push({ programCode: p.code, programName: p.name, group: g.heading || "Requirements" });
        }
      } catch {
        // Skip this one program's mapping — its requirements failed to load.
      }
    }
  } catch {
    // Not signed in / no record: breadth mappings below still apply.
  }

  for (const b of course.breadth) {
    const key = breadthKeyFromLabel(b);
    if (key) {
      mappings.push({
        programCode: "ARTSC",
        programName: "Arts & Science breadth requirement",
        group: b.replace(/\s*\(\d\)\s*$/, ""),
        breadth: key,
      });
    }
  }

  return { prereqTree: parsePrereqText(course.prerequisites, completed), satisfies: mappings };
}

export default function CourseDetail() {
  const { code = "" } = useParams();
  const navigate = useNavigate();

  const [course, setCourse] = React.useState<Course | null | undefined>(undefined); // undefined = loading
  const [error, setError] = React.useState<string | null>(null);
  const [derived, setDerived] = React.useState<Derived>({ satisfies: [] });
  const [selectedSections, setSelectedSections] = React.useState<Record<string, string>>({});
  const [toast, setToast] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setCourse(undefined);
    setError(null);
    setSelectedSections({});
    setDerived({ satisfies: [] });
    api
      .getCourse(code)
      .then((c) => {
        if (cancelled) return;
        setCourse(c);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load this course.");
        setCourse(null);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  React.useEffect(() => {
    if (!course) return;
    let cancelled = false;
    buildDerived(course).then((d) => {
      if (!cancelled) setDerived(d);
    });
    return () => {
      cancelled = true;
    };
  }, [course]);

  const handleClose = () => navigate("/courses");

  const dsCourse: DsCourseDetail | null = course
    ? {
        code: course.code,
        title: course.title,
        credit: course.credit,
        campus: course.campus || undefined,
        description: course.description || undefined,
        breadth: course.breadth.map(breadthKeyFromLabel).filter((b): b is BreadthKey => Boolean(b)),
        prereqTree: derived.prereqTree,
        exclusions: course.exclusions || undefined,
        sections: course.sections.map((s) => ({
          name: s.name,
          teachMethod: s.teachMethod,
          currentEnrol: s.currentEnrol,
          maxEnrol: s.maxEnrol,
          waitlist: s.waitlist,
          instructors: s.instructors,
          meetingTimes: s.meetingTimes.map((m) => ({
            day: m.day,
            startMin: m.startMin,
            endMin: m.endMin,
            building: m.building,
          })),
        })),
        satisfies: derived.satisfies,
      }
    : null;

  return (
    <Drawer open onClose={handleClose} title={course ? course.code : "Course"} width={640}>
      {course === undefined && !error && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }} aria-busy="true">
          <Skeleton width="35%" height={13} />
          <Skeleton width="70%" height={26} />
          <Skeleton width="100%" height={90} />
          <Skeleton width="100%" height={140} />
        </div>
      )}

      {error && (
        <Callout tone="danger" title="Couldn't load this course">
          {error}
        </Callout>
      )}

      {course === null && !error && (
        <EmptyState
          title="Course not found"
          description={`No course matches "${code}".`}
          icon="search"
          action={
            <Button variant="secondary" onClick={handleClose}>
              Back to Courses
            </Button>
          }
        />
      )}

      {dsCourse && (
        <CourseDetailPanel
          course={dsCourse}
          selectedSections={selectedSections}
          onSelectSection={(method: string, name: string) =>
            setSelectedSections((s) => ({ ...s, [method]: name }))
          }
          onAddPlan={() => setToast(`${dsCourse.code} — plan integration is coming soon.`)}
          onAddTimetable={() => setToast(`${dsCourse.code} — timetable integration is coming soon.`)}
        />
      )}

      {toast && (
        <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 300 }}>
          <Toast tone="info" onClose={() => setToast(null)}>
            {toast}
          </Toast>
        </div>
      )}
    </Drawer>
  );
}
