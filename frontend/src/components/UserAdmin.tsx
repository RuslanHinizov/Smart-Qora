import { useState } from "react";
import { useChangePassword, useMe, useUserMutations, useUsers } from "../api/queries";
import type { Role } from "../api/types";
import { useLanguage } from "../i18n/useLanguage";

const MIN_PASSWORD = 8;

/** Change the signed-in user's own password. Available to every role. */
export function AccountCard() {
  const { t } = useLanguage();
  const me = useMe();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");

  const submit = async () => {
    try {
      await change.mutateAsync({ current_password: current, new_password: next });
      setCurrent("");
      setNext("");
    } catch {
      /* shown through change.isError */
    }
  };

  return (
    <div className="card panel settings-grid">
      <div className="panel-head">
        <h3>{t.accountSection}</h3>
        {change.isSuccess && <span className="saved-tag">{t.passwordChanged}</span>}
      </div>
      {me.data && (
        <p className="hint">
          {t.signedInAs}: <strong>{me.data.username}</strong>
        </p>
      )}
      <div className="field">
        <label htmlFor="pw-current">{t.currentPassword}</label>
        <input
          id="pw-current"
          className="input"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="pw-new">{t.newPassword}</label>
        <input
          id="pw-new"
          className="input"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
        <span className="hint">{t.passwordHint}</span>
      </div>
      {change.isError && <p className="error-text">{t.passwordChangeError}</p>}
      <button
        className="btn"
        disabled={!current || next.length < MIN_PASSWORD || change.isPending}
        onClick={submit}
      >
        {t.changePassword}
      </button>
    </div>
  );
}

/** Admin-only: add users, switch their role, set a password, deactivate. */
export function UsersCard() {
  const { t } = useLanguage();
  const users = useUsers(true);
  const { create, update } = useUserMutations();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [resetFor, setResetFor] = useState<number | null>(null);
  const [resetValue, setResetValue] = useState("");
  const [error, setError] = useState(false);

  const run = async (action: () => Promise<unknown>) => {
    setError(false);
    try {
      await action();
    } catch {
      setError(true);
    }
  };
  const roleLabel = (value: Role) => (value === "admin" ? t.roleAdmin : t.roleViewer);

  return (
    <div className="card panel">
      <div className="panel-head">
        <h3>{t.usersSection}</h3>
      </div>
      <p className="hint">{t.usersHint}</p>
      {error && <p className="error-text">{t.userSaveError}</p>}
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>{t.username}</th>
              <th>{t.role}</th>
              <th>{t.activeToggle}</th>
              <th aria-label="actions" />
            </tr>
          </thead>
          <tbody>
            {(users.data ?? []).map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>
                  <select
                    className="select"
                    aria-label={`${t.role}: ${user.username}`}
                    value={user.role}
                    onChange={(e) =>
                      run(() =>
                        update.mutateAsync({
                          id: user.id,
                          input: { role: e.target.value as Role },
                        }),
                      )
                    }
                  >
                    <option value="admin">{roleLabel("admin")}</option>
                    <option value="viewer">{roleLabel("viewer")}</option>
                  </select>
                </td>
                <td>{user.is_active ? "✓" : t.inactive}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  {resetFor === user.id ? (
                    <span style={{ display: "inline-flex", gap: "var(--sp-2)" }}>
                      <input
                        className="input"
                        type="password"
                        autoComplete="new-password"
                        aria-label={t.newPassword}
                        placeholder={t.passwordHint}
                        value={resetValue}
                        onChange={(e) => setResetValue(e.target.value)}
                      />
                      <button
                        className="btn sm primary"
                        disabled={resetValue.length < MIN_PASSWORD || update.isPending}
                        onClick={() =>
                          run(async () => {
                            await update.mutateAsync({
                              id: user.id,
                              input: { password: resetValue },
                            });
                            setResetFor(null);
                            setResetValue("");
                          })
                        }
                      >
                        {t.save}
                      </button>
                      <button
                        className="btn sm ghost"
                        onClick={() => {
                          setResetFor(null);
                          setResetValue("");
                        }}
                      >
                        {t.cancel}
                      </button>
                    </span>
                  ) : (
                    <>
                      <button
                        className="btn sm ghost"
                        onClick={() => {
                          setResetFor(user.id);
                          setResetValue("");
                        }}
                      >
                        {t.resetPassword}
                      </button>
                      <button
                        className={user.is_active ? "btn sm danger" : "btn sm ghost"}
                        disabled={update.isPending}
                        onClick={() =>
                          run(() =>
                            update.mutateAsync({
                              id: user.id,
                              input: { is_active: !user.is_active },
                            }),
                          )
                        }
                      >
                        {user.is_active ? t.deactivate : t.activate}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor="user-name">{t.username}</label>
          <input
            id="user-name"
            className="input"
            autoComplete="off"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="user-password">{t.password}</label>
          <input
            id="user-password"
            className="input"
            type="password"
            autoComplete="new-password"
            placeholder={t.passwordHint}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
      </div>
      <div className="field" style={{ maxWidth: 320 }}>
        <label htmlFor="user-role">{t.role}</label>
        <select
          id="user-role"
          className="select"
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
        >
          <option value="viewer">{roleLabel("viewer")}</option>
          <option value="admin">{roleLabel("admin")}</option>
        </select>
      </div>
      <button
        className="btn primary"
        style={{ alignSelf: "flex-start" }}
        disabled={username.trim().length < 3 || password.length < MIN_PASSWORD || create.isPending}
        onClick={() =>
          run(async () => {
            await create.mutateAsync({ username: username.trim(), password, role });
            setUsername("");
            setPassword("");
            setRole("viewer");
          })
        }
      >
        {t.addUser}
      </button>
    </div>
  );
}
