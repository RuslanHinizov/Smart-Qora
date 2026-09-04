import { useEffect, useState } from "react";
import {
  useCalibrateHerd,
  useRestartWorker,
  useSettings,
  useSettingsMutation,
  useStatsToday,
  useWorkerInfo,
} from "../api/queries";
import type { SettingsInput } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { useLanguage } from "../i18n/useLanguage";
import { languages } from "../i18n/translations";
import { statusLabel } from "../lib/format";

export function Settings() {
  const { t } = useLanguage();
  const { isAdmin } = useAuth();
  const settings = useSettings();
  const worker = useWorkerInfo();
  const stats = useStatsToday();
  const saveSettings = useSettingsMutation();
  const calibrate = useCalibrateHerd();
  const restart = useRestartWorker();

  const [draft, setDraft] = useState<SettingsInput>({});
  const [headcount, setHeadcount] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings.data) {
      setDraft({
        default_language: settings.data.default_language,
        telegram_aggregation_seconds: settings.data.telegram_aggregation_seconds,
        default_confidence: settings.data.default_confidence,
        default_iou: settings.data.default_iou,
        default_frame_skip: settings.data.default_frame_skip,
      });
    }
  }, [settings.data]);

  const patch = (next: Partial<SettingsInput>) => {
    setSaved(false);
    setDraft((d) => ({ ...d, ...next }));
  };

  const submit = async () => {
    await saveSettings.mutateAsync(draft);
    setDraft((d) => ({ ...d, telegram_bot_token: undefined, telegram_chat_id: undefined }));
    setSaved(true);
  };

  const num = (v: string): number | null => (v === "" ? null : Number(v));

  return (
    <main className="page">
      <div className="page-head">
        <span className="section-title">{t.settings}</span>
        {saved && <span className="saved-tag">{t.settingsSaved}</span>}
      </div>

      {!isAdmin && <div className="notice">{t.readOnlyForViewers}</div>}

      <fieldset className="card panel settings-grid" disabled={!isAdmin} style={{ border: 0 }}>
        <div className="panel-head">
          <h3>{t.generalSection}</h3>
        </div>
        <div className="field">
          <label>{t.defaultLanguage}</label>
          <select
            className="select"
            value={draft.default_language ?? "ru"}
            onChange={(e) => patch({ default_language: e.target.value })}
          >
            {languages.map((code) => (
              <option key={code} value={code}>
                {code.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="panel-head">
          <h3>{t.telegramSection}</h3>
        </div>
        {settings.data?.telegram_configured && (
          <span className="saved-tag">{t.telegramTokenSet}</span>
        )}
        <div className="field">
          <label>{t.telegramToken}</label>
          <input
            className="input"
            type="password"
            placeholder="••••••••"
            value={draft.telegram_bot_token ?? ""}
            onChange={(e) => patch({ telegram_bot_token: e.target.value })}
          />
          <span className="hint">{t.telegramTokenHint}</span>
        </div>
        <div className="field">
          <label>{t.telegramChatId}</label>
          <input
            className="input"
            value={draft.telegram_chat_id ?? ""}
            onChange={(e) => patch({ telegram_chat_id: e.target.value })}
          />
        </div>
        <div className="field">
          <label>{t.aggregationSeconds}</label>
          <input
            className="input"
            type="number"
            min={1}
            value={draft.telegram_aggregation_seconds ?? 5}
            onChange={(e) => patch({ telegram_aggregation_seconds: Number(e.target.value) })}
          />
        </div>

        <div className="panel-head">
          <h3>{t.detectionSection}</h3>
        </div>
        <div className="form-row">
          <div className="field">
            <label>{t.defaultConfidence}</label>
            <input
              className="input"
              type="number"
              step={0.05}
              value={draft.default_confidence ?? ""}
              onChange={(e) => patch({ default_confidence: num(e.target.value) })}
            />
          </div>
          <div className="field">
            <label>{t.defaultIou}</label>
            <input
              className="input"
              type="number"
              step={0.05}
              value={draft.default_iou ?? ""}
              onChange={(e) => patch({ default_iou: num(e.target.value) })}
            />
          </div>
        </div>

        <button className="btn primary" onClick={submit} disabled={saveSettings.isPending}>
          {t.save}
        </button>
      </fieldset>

      <div className="card panel settings-grid">
        <div className="panel-head">
          <h3>{t.herdSection}</h3>
        </div>
        <p className="hint">{t.headcountHint}</p>
        <div className="field">
          <label>{t.currentHeadcount}</label>
          <input
            className="input"
            type="number"
            min={0}
            placeholder={String(stats.data?.current ?? 0)}
            value={headcount}
            onChange={(e) => setHeadcount(e.target.value)}
            disabled={!isAdmin}
          />
        </div>
        <button
          className="btn"
          disabled={!isAdmin || headcount === "" || calibrate.isPending}
          onClick={async () => {
            await calibrate.mutateAsync(Number(headcount));
            setHeadcount("");
          }}
        >
          {t.calibrate}
        </button>
      </div>

      <div className="card panel settings-grid">
        <div className="panel-head">
          <h3>{t.workerSection}</h3>
        </div>
        <div className="health-list">
          <div>
            <span>{t.workerState}</span>
            <strong>{statusLabel(t, worker.data?.state ?? "stopped")}</strong>
          </div>
          <div>
            <span>{t.tracking}</span>
            <strong>{statusLabel(t, worker.data?.camera ?? "OFFLINE")}</strong>
          </div>
        </div>
        <button
          className="btn"
          disabled={!isAdmin || restart.isPending}
          onClick={() => restart.mutate()}
        >
          {restart.isSuccess ? t.restartRequested : t.restartWorker}
        </button>
      </div>
    </main>
  );
}
