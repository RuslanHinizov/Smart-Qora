import { useEvents, useSystemStatus, useStatsToday } from "../api/queries";
import { CameraView } from "../components/CameraView";
import { Icon, type IconName } from "../components/Icon";
import { useLanguage } from "../i18n/useLanguage";
import { animalLabel, formatTime, statusLabel } from "../lib/format";

function Metric({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: number | string;
  icon: IconName;
  tone: string;
}) {
  return (
    <article className={`card metric ${tone}`}>
      <div className="metric-head">
        <span>{label}</span>
        <span className="metric-icon">
          <Icon name={icon} size={18} />
        </span>
      </div>
      <strong>{value}</strong>
    </article>
  );
}

export function Dashboard() {
  const { language, t } = useLanguage();
  const status = useSystemStatus();
  const stats = useStatsToday();
  const events = useEvents({ limit: 6 });

  const camera = status.data?.camera ?? "OFFLINE";
  const ai = status.data?.ai ?? "IDLE";
  const cameraOnline = camera === "ONLINE";
  const aiActive = ai === "ACTIVE";
  const totals = stats.data ?? { total_in: 0, total_out: 0, current: 0 };
  const rows = events.data?.rows ?? [];

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h2 style={{ fontSize: "var(--fs-5)" }}>{t.greeting}</h2>
          <p>{t.subtitle}</p>
        </div>
        <span className={`badge ${cameraOnline && aiActive ? "" : "warn"}`}>
          <span className="dot" />
          {cameraOnline && aiActive ? t.allSystems : t.degraded}
        </span>
      </div>

      <section className="metrics">
        <Metric label={t.currentInside} value={totals.current} icon="livestock" tone="" />
        <Metric label={t.enteredToday} value={totals.total_in} icon="arrow" tone="cyan" />
        <Metric label={t.exitedToday} value={totals.total_out} icon="arrow" tone="indigo" />
        <Metric label={t.aiModel} value={statusLabel(t, ai)} icon="sparkles" tone="violet" />
      </section>

      <section className="grid-2">
        <article className="card panel">
          <div className="panel-head">
            <div>
              <span className="section-title">{t.liveCamera}</span>
              <h3>{t.detectionLine}</h3>
            </div>
            <span className={`badge ${cameraOnline ? "" : "off"}`}>
              <span className="dot" />
              {statusLabel(t, camera)}
            </span>
          </div>
          <CameraView active={cameraOnline} />
        </article>

        <article className="card panel">
          <div className="panel-head">
            <div>
              <span className="section-title">{t.aiModel}</span>
              <h3>{t.systemHealth}</h3>
            </div>
            <span className={`badge ${aiActive ? "" : "off"}`}>
              <span className="dot" />
              {statusLabel(t, ai)}
            </span>
          </div>
          <div className="health-list">
            <div>
              <span>{t.model}</span>
              <strong>YOLOE-26s</strong>
            </div>
            <div>
              <span>{t.gpu}</span>
              <strong>CUDA</strong>
            </div>
            <div>
              <span>{t.tracking}</span>
              <strong>BoT-SORT</strong>
            </div>
            <div>
              <span>{t.workerState}</span>
              <strong>{statusLabel(t, status.data?.worker ?? "stopped")}</strong>
            </div>
          </div>
        </article>
      </section>

      <article className="card panel">
        <div className="panel-head">
          <div>
            <span className="section-title">{t.recentEvents}</span>
            <h3>{t.flowToday}</h3>
          </div>
        </div>
        {rows.length === 0 ? (
          <div className="empty">
            <Icon name="clock" />
            <span>{t.noEvents}</span>
          </div>
        ) : (
          <div className="event-list">
            {rows.map((event) => (
              <div className="event-row" key={event.id}>
                <span className={`event-dir ${event.direction === "OUT" ? "out" : ""}`}>
                  <Icon name="arrow" size={16} />
                </span>
                <div className="event-main">
                  <strong>{animalLabel(t, event.animal_type)}</strong>
                  <span>{event.direction === "IN" ? t.entered : t.exited}</span>
                </div>
                <div className="event-meta">
                  <strong>{Math.round(event.confidence * 100)}%</strong>
                  <span>{formatTime(event.timestamp, language)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>
    </main>
  );
}
