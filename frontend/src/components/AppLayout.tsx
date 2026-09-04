import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useLiveSocket } from "../api/useLiveSocket";
import { useSettings } from "../api/queries";
import { useAuth } from "../auth/useAuth";
import { useLanguage } from "../i18n/useLanguage";
import type { Language } from "../i18n/translations";
import { Icon, type IconName } from "./Icon";
import { LanguageSwitcher } from "./LanguageSwitcher";

const NAV: Array<{
  to: string;
  icon: IconName;
  key: "dashboard" | "cameras" | "events" | "statistics" | "settings";
}> = [
  { to: "/", icon: "grid", key: "dashboard" },
  { to: "/cameras", icon: "camera", key: "cameras" },
  { to: "/events", icon: "events", key: "events" },
  { to: "/statistics", icon: "chart", key: "statistics" },
  { to: "/settings", icon: "settings", key: "settings" },
];

export function AppLayout() {
  const { t } = useLanguage();
  const { setLanguageIfUnset } = useLanguage();
  const { role, logout } = useAuth();
  const location = useLocation();
  useLiveSocket();

  const settings = useSettings();
  useEffect(() => {
    if (settings.data?.default_language) {
      setLanguageIfUnset(settings.data.default_language as Language);
    }
  }, [settings.data?.default_language, setLanguageIfUnset]);

  const current = NAV.find((item) => item.to === location.pathname) ?? NAV[0];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="livestock" size={22} />
          </span>
          <span className="brand-text">
            <strong>{t.appName}</strong>
            <span>{t.tagline}</span>
          </span>
        </div>
        <nav className="nav" aria-label={t.dashboard}>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}>
              <Icon name={item.icon} size={18} />
              <span>{t[item.key]}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="user-chip">
            <span className="avatar">{(role ?? "?").slice(0, 2).toUpperCase()}</span>
            <span>{role === "admin" ? "Admin" : "Viewer"}</span>
          </div>
          <button className="btn sm ghost" onClick={logout}>
            <Icon name="logout" size={14} />
            {t.logout}
          </button>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">{t.appName}</span>
            <h1>{t[current.key]}</h1>
          </div>
          <div className="topbar-actions">
            <LanguageSwitcher />
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
