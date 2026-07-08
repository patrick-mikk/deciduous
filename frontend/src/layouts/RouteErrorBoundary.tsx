import * as React from "react";

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Contains a crash to the routed content area instead of white-screening the
 * whole app -- TopBar/SideNav/ProgressStrip in AppLayout stay interactive so
 * the user can navigate to a working screen. Resets when the route changes
 * (`key` on the wrapping element in AppLayout), since the error is almost
 * always specific to whatever screen was mounted, not global app state.
 */
export class RouteErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Screen crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32, maxWidth: 560, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ marginBottom: 8 }}>Something went wrong loading this page</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
            {this.state.error.message || "An unexpected error occurred."}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            style={{
              padding: "8px 16px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              background: "var(--surface-card)",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
