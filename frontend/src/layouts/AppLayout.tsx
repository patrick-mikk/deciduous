import * as React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useTheme } from "@/theme/ThemeProvider";
import { TopBar, SideNav, ProgressStrip, Callout } from "@/ds";
import { api, isMockApi } from "@/api";
import { RouteErrorBoundary } from "./RouteErrorBoundary";
import "./AppLayout.css";

/**
 * The authenticated app frame: TopBar + SideNav + routed page content +
 * persistent ProgressStrip (design/01-information-architecture.md's "App
 * shell (authenticated layout)").
 *
 * This is a hand-composed equivalent of the design system's own `<AppShell>`
 * (see design/claude-design-output/_ds_bundle.js, components/layout/AppShell.jsx)
 * rather than that component directly: AppShell manages its own theme state
 * internally (uncontrolled `useState('light')`), which would fight this app's
 * `ThemeProvider`. Composing TopBar/SideNav/ProgressStrip by hand lets the
 * real ThemeProvider drive the toggle instead, while keeping the exact same
 * grid layout (mirrored in AppLayout.css).
 */
export function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = React.useState(false);
  const [progress, setProgress] = React.useState({
    credits: 0,
    creditsTotal: 20,
    breadth: 0,
    breadthTotal: 5,
    cgpa: 0,
    degreePct: 0,
  });
  const [notifications, setNotifications] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    Promise.all([api.getMySummary(), api.getMyBreadth(), api.getMyAlerts()])
      .then(([summary, breadth, alerts]) => {
        if (cancelled) return;
        setProgress({
          credits: summary.creditsEarned,
          creditsTotal: summary.creditsTotal,
          breadth: breadth.evaluation.fulls,
          breadthTotal: 5,
          cgpa: summary.cgpa,
          degreePct: summary.degreePct,
        });
        setNotifications(alerts.filter((a) => !a.read).length);
      })
      .catch(() => {
        // Non-fatal: the strip just keeps its zeroed defaults. A real error
        // surface (Callout/Toast) belongs to the screen that owns this data,
        // not the persistent chrome.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Active SideNav key = the first path segment ("/programs/:code" -> "programs").
  const active = location.pathname.split("/").filter(Boolean)[0] ?? "dashboard";

  return (
    <div className="dc-app-shell">
      <TopBar
        theme={theme}
        onThemeToggle={toggleTheme}
        onMenuClick={() => setCollapsed((c) => !c)}
        notifications={notifications}
      />
      <SideNav active={active} onNavigate={(key: string) => navigate(`/${key}`)} collapsed={collapsed} />
      <main className="dc-app-shell__main">
        <div className="dc-app-shell__main-inner">
          {isMockApi && (
            <div style={{ marginBottom: "var(--space-5)" }}>
              <Callout tone="warning" title="Demo data — not connected to a backend">
                Everything on this screen (transcript, programs, GPA, alerts) comes from seeded
                sample data, not your account. Remove <code>VITE_API_BASE=mock</code> from{" "}
                <code>frontend/.env</code> to use the real API.
              </Callout>
            </div>
          )}
          <RouteErrorBoundary key={location.pathname}>
            <Outlet />
          </RouteErrorBoundary>
        </div>
      </main>
      <ProgressStrip {...progress} onDetails={() => navigate("/dashboard")} />
    </div>
  );
}

export default AppLayout;
