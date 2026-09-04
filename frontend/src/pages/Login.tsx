import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { Icon } from "../components/Icon";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useLanguage } from "../i18n/useLanguage";

export function Login() {
  const { t } = useLanguage();
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username.trim(), password);
      navigate("/", { replace: true });
    } catch {
      setError(t.signInError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="card login-card" onSubmit={submit}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="brand">
            <span className="brand-mark">
              <Icon name="livestock" size={20} />
            </span>
            <span className="brand-text">
              <strong>{t.appName}</strong>
              <span>{t.tagline}</span>
            </span>
          </div>
          <LanguageSwitcher />
        </div>
        <h2>{t.signIn}</h2>
        <p>{t.signInSubtitle}</p>

        <div className="field">
          <label htmlFor="username">{t.username}</label>
          <input
            id="username"
            className="input"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">{t.password}</label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? t.loading : t.signInAction}
        </button>
      </form>
    </div>
  );
}
