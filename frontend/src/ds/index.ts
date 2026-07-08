/**
 * Public entry point for the Deciduous design system (87 components, vendored
 * from design/claude-design-output/_ds_bundle.js).
 *
 * Usage from anywhere in the app:
 *
 *   import { Button, Card, AppShell, DegreeProgressCard } from "@/ds";
 *
 * How this works:
 *  1. `./reactGlobal` stamps `window.React` (and `window.ReactDOM`, `window.lucide`)
 *     — the bundle's components are plain `React.createElement(...)` calls that
 *     read those as bare globals, they don't `import` React themselves.
 *  2. `./_ds_bundle.js` (a verbatim copy of the design package's bundle) is then
 *     imported for its side effect: it populates
 *     `window.DeciduousDesignSystem_6c95c0` with every component.
 *  3. Below, every component is re-exported by name, typed from the matching
 *     `.d.ts` where the design package shipped one (17 of 87 — the "clean"
 *     sources under `./source/{account,courses,data}`; see HANDOFF.md), and
 *     as `React.ComponentType<any>` otherwise.
 *
 * Import order is load-bearing: static imports evaluate depth-first in the
 * order written, and step 1 fully finishes before step 2 starts (see the
 * comment in reactGlobal.ts) — no top-level await needed.
 */
import type { ComponentType } from "react";
import "./reactGlobal";
import "./_ds_bundle.js";

// ---- Prop types lifted from the 17 "clean" component sources ----------------
import type { AuthCardProps } from "./source/account/AuthCard";
import type { DangerZoneProps } from "./source/account/DangerZone";
import type { DataExportMenuProps } from "./source/account/DataExportMenu";
import type { DensityToggleProps } from "./source/account/DensityToggle";
import type { DropzoneProps } from "./source/account/Dropzone";
import type { ImportPanelProps, ImportPreviewProps } from "./source/account/ImportPanel";
import type { NotificationItem, NotificationPanelProps } from "./source/account/NotificationPanel";
import type { RecoveryCodeCardProps } from "./source/account/RecoveryCodeCard";
import type { ShareLinkDialogProps } from "./source/account/ShareLinkDialog";
import type { ThemeToggleProps } from "./source/account/ThemeToggle";
import type { CourseDetail, CourseDetailPanelProps } from "./source/courses/CourseDetailPanel";
import type { PrereqNode, PrereqTreeProps } from "./source/courses/PrereqTree";
import type {
  RequirementMapping,
  RequirementMappingListProps,
} from "./source/courses/RequirementMappingList";
import type { SeatMeterProps } from "./source/courses/SeatMeter";
import type {
  MeetingTime as DsMeetingTime,
  Section as DsSection,
  SectionRowProps,
  SectionListProps,
} from "./source/courses/SectionList";
import type { CardProps } from "./source/data/Card";
import type { CourseCardProps } from "./source/data/CourseCard";

export type {
  AuthCardProps,
  DangerZoneProps,
  DataExportMenuProps,
  DensityToggleProps,
  DropzoneProps,
  ImportPanelProps,
  ImportPreviewProps,
  NotificationItem,
  NotificationPanelProps,
  RecoveryCodeCardProps,
  ShareLinkDialogProps,
  ThemeToggleProps,
  CourseDetail,
  CourseDetailPanelProps,
  PrereqNode,
  PrereqTreeProps,
  RequirementMapping,
  RequirementMappingListProps,
  SeatMeterProps,
  DsMeetingTime,
  DsSection,
  SectionRowProps,
  SectionListProps,
  CardProps,
  CourseCardProps,
};

// The bundle attaches itself here (see _ds_bundle.js line ~5: `window.DeciduousDesignSystem_6c95c0`).
const ns = window.DeciduousDesignSystem_6c95c0;

if (import.meta.env.DEV && (!ns || Object.keys(ns).length === 0)) {
  // eslint-disable-next-line no-console
  console.error(
    "[ds] window.DeciduousDesignSystem_6c95c0 is empty — _ds_bundle.js failed to load or evaluate.",
  );
}

/** Any per-component errors the bundle swallowed while evaluating (see its try/catch wrappers). */
export const dsLoadErrors: { path: string; error: string }[] =
  (ns?.__errors as { path: string; error: string }[]) ?? [];

function pick<Props = any>(name: string): ComponentType<Props> {
  const cmp = ns?.[name];
  if (import.meta.env.DEV && !cmp) {
    // eslint-disable-next-line no-console
    console.error(`[ds] component "${name}" was not found on window.DeciduousDesignSystem_6c95c0`);
  }
  return cmp as ComponentType<Props>;
}

// ---- account/ -----------------------------------------------------------
export const AuthCard = pick<AuthCardProps>("AuthCard");
export const DangerZone = pick<DangerZoneProps>("DangerZone");
export const DataExportMenu = pick<DataExportMenuProps>("DataExportMenu");
export const DensityToggle = pick<DensityToggleProps>("DensityToggle");
export const Dropzone = pick<DropzoneProps>("Dropzone");
export const ImportPanel = pick<ImportPanelProps>("ImportPanel");
export const ImportPreview = pick<ImportPreviewProps>("ImportPreview");
export const NotificationPanel = pick<NotificationPanelProps>("NotificationPanel");
export const RecoveryCodeCard = pick<RecoveryCodeCardProps>("RecoveryCodeCard");
export const ShareLinkDialog = pick<ShareLinkDialogProps>("ShareLinkDialog");
export const ThemeToggle = pick<ThemeToggleProps>("ThemeToggle");

// ---- courses/ -------------------------------------------------------------
export const CourseDetailPanel = pick<CourseDetailPanelProps>("CourseDetailPanel");
export const PrereqTree = pick<PrereqTreeProps>("PrereqTree");
export const RequirementMappingList = pick<RequirementMappingListProps>("RequirementMappingList");
export const SeatMeter = pick<SeatMeterProps>("SeatMeter");
export const SectionRow = pick<SectionRowProps>("SectionRow");
export const SectionList = pick<SectionListProps>("SectionList");

// ---- data/ ------------------------------------------------------------------
export const Card = pick<CardProps>("Card");
export const CourseCard = pick<CourseCardProps>("CourseCard");
export const DataTable = pick<any>("DataTable");
export const TimetableGrid = pick<any>("TimetableGrid");

// ---- display/ -----------------------------------------------------------
export const Avatar = pick<any>("Avatar");
export const Divider = pick<any>("Divider");
export const Kbd = pick<any>("Kbd");
export const Skeleton = pick<any>("Skeleton");
export const Spinner = pick<any>("Spinner");

// ---- feedback/ ----------------------------------------------------------
export const Badge = pick<any>("Badge");
export const Callout = pick<any>("Callout");
export const Chip = pick<any>("Chip");
export const Dialog = pick<any>("Dialog");
export const EmptyState = pick<any>("EmptyState");
export const Tag = pick<any>("Tag");
export const Toast = pick<any>("Toast");
export const Tooltip = pick<any>("Tooltip");

// ---- forms/ -----------------------------------------------------------------
export const Button = pick<any>("Button");
export const Checkbox = pick<any>("Checkbox");
export const Combobox = pick<any>("Combobox");
export const IconButton = pick<any>("IconButton");
export const Input = pick<any>("Input");
export const StrengthMeter = pick<any>("StrengthMeter");
export const PasswordField = pick<any>("PasswordField");
export const Radio = pick<any>("Radio");
export const RangeSlider = pick<any>("RangeSlider");
export const Select = pick<any>("Select");
export const Slider = pick<any>("Slider");
export const Switch = pick<any>("Switch");
export const Textarea = pick<any>("Textarea");

// ---- layout/ ----------------------------------------------------------------
export const AppShell = pick<any>("AppShell");
export const PageHeader = pick<any>("PageHeader");
export const ProgressStrip = pick<any>("ProgressStrip");
export const SideNav = pick<any>("SideNav");
export const TopBar = pick<any>("TopBar");
export const Wordmark = pick<any>("Wordmark");

// ---- navigation/ --------------------------------------------------------
export const Accordion = pick<any>("Accordion");
export const BottomTabBar = pick<any>("BottomTabBar");
export const FilterBar = pick<any>("FilterBar");
export const Stepper = pick<any>("Stepper");
export const Tabs = pick<any>("Tabs");

// ---- overlay/ -----------------------------------------------------------
export const CommandPalette = pick<any>("CommandPalette");
export const Drawer = pick<any>("Drawer");
export const DropdownMenu = pick<any>("DropdownMenu");

// ---- plan/ ------------------------------------------------------------------
export const AutoPlanPanel = pick<any>("AutoPlanPanel");
export const CourseRail = pick<any>("CourseRail");
export const PlanBoard = pick<any>("PlanBoard");
export const PlanCourseCard = pick<any>("PlanCourseCard");
export const TermColumn = pick<any>("TermColumn");
export const ValidationSummary = pick<any>("ValidationSummary");

// ---- programs/ ----------------------------------------------------------
export const POStCombinationValidator = pick<any>("POStCombinationValidator");
export const ProgramCard = pick<any>("ProgramCard");
export const ProgramHeader = pick<any>("ProgramHeader");

// ---- progress/ ----------------------------------------------------------
export const CreditMeter = pick<any>("CreditMeter");
export const DegreeProgressCard = pick<any>("DegreeProgressCard");
export const GPACard = pick<any>("GPACard");
export const ProgressBar = pick<any>("ProgressBar");
export const ProgressRing = pick<any>("ProgressRing");
export const Sparkline = pick<any>("Sparkline");
export const StatTile = pick<any>("StatTile");

// ---- requirements/ -----------------------------------------------------
export const BreadthTracker = pick<any>("BreadthTracker");
export const DegreeAudit = pick<any>("DegreeAudit");
export const RequirementCourseChip = pick<any>("RequirementCourseChip");
export const RequirementGroupCard = pick<any>("RequirementGroupCard");
export const RequirementProgressList = pick<any>("RequirementProgressList");

// ---- timetable/ ---------------------------------------------------------
export const CourseTray = pick<any>("CourseTray");
export const OptimizerPanel = pick<any>("OptimizerPanel");
export const ScenarioTabs = pick<any>("ScenarioTabs");
export const ScheduleCandidateList = pick<any>("ScheduleCandidateList");
export const SectionBlock = pick<any>("SectionBlock");
