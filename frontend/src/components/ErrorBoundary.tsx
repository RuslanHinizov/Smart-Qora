import { Component, type ErrorInfo, type ReactNode } from "react";
import { translations } from "../i18n/translations";

type Props = { children: ReactNode };
type State = { error: Error | null };

// Class component: React error boundaries have no hook equivalent yet.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ui_error_boundary", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    const t = translations.en; // boundary sits above the language provider
    return (
      <div className="login-screen">
        <div className="card login-card" role="alert">
          <h2>{t.errorTitle}</h2>
          <p>{t.errorBody}</p>
          <button className="btn primary" onClick={() => window.location.reload()}>
            {t.retry}
          </button>
        </div>
      </div>
    );
  }
}
