import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";

import Landing from "@/screens/Landing";
import SignIn from "@/screens/SignIn";
import SignUp from "@/screens/SignUp";
import Share from "@/screens/Share";

import Onboarding from "@/screens/Onboarding";
import Dashboard from "@/screens/Dashboard";
import Programs from "@/screens/Programs";
import ProgramDetail from "@/screens/ProgramDetail";
import Requirements from "@/screens/Requirements";
import RequirementDetail from "@/screens/RequirementDetail";
import Plan from "@/screens/Plan";
import Courses from "@/screens/Courses";
import CourseDetail from "@/screens/CourseDetail";
import Transcript from "@/screens/Transcript";
import Timetable from "@/screens/Timetable";
import TimetableOptimize from "@/screens/TimetableOptimize";
import Settings from "@/screens/Settings";
import Help from "@/screens/Help";

/**
 * Route map, 1:1 with design/01-information-architecture.md's sitemap.
 *
 *   Public (no app shell): /, /signin, /signup, /share/:token
 *   Authenticated (AppLayout: TopBar + SideNav + ProgressStrip): everything else.
 *
 * Screens are stubs (frontend/src/screens/*.tsx) — each owning agent overwrites
 * only their own screen's file body; this file and the route paths are the
 * contract they build against.
 */
export default function App() {
  return (
    <Routes>
      {/* ---- Public ---------------------------------------------------- */}
      <Route path="/" element={<Landing />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/share/:token" element={<Share />} />

      {/* ---- Authenticated (app shell) ---------------------------------- */}
      <Route element={<AppLayout />}>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/dashboard" element={<Dashboard />} />

        <Route path="/programs" element={<Programs />} />
        <Route path="/programs/:code" element={<ProgramDetail />} />

        <Route path="/requirements" element={<Requirements />} />
        <Route path="/requirements/:code" element={<RequirementDetail />} />

        <Route path="/plan" element={<Plan />} />

        <Route path="/courses" element={<Courses />} />
        <Route path="/courses/:code" element={<CourseDetail />} />

        <Route path="/transcript" element={<Transcript />} />

        <Route path="/timetable" element={<Timetable />} />
        <Route path="/timetable/optimize" element={<TimetableOptimize />} />

        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
      </Route>

      {/* ---- Fallback ---------------------------------------------------- */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
