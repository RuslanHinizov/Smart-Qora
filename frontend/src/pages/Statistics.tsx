import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useHistory } from "../api/queries";
import { Icon } from "../components/Icon";
import { useLanguage } from "../i18n/useLanguage";
import { animalLabel, daysAgoISO, formatDate, todayISO } from "../lib/format";

type Group = "day" | "week" | "month";

export function Statistics() {
  const { language, t } = useLanguage();
  const [group, setGroup] = useState<Group>("day");
  const [from, setFrom] = useState(daysAgoISO(30));
  const [to, setTo] = useState(todayISO());

  const history = useHistory(from, to, group);
  const rows = useMemo(() => history.data ?? [], [history.data]);

  const byPeriod = useMemo(() => {
    const map = new Map<string, { period: string; in: number; out: number }>();
    for (const row of rows) {
      const entry = map.get(row.date) ?? { period: row.date, in: 0, out: 0 };
      entry.in += row.total_in;
      entry.out += row.total_out;
      map.set(row.date, entry);
    }
    return [...map.values()]
      .sort((a, b) => a.period.localeCompare(b.period))
      .map((e) => ({ ...e, label: formatDate(e.period, language) }));
  }, [rows, language]);

  const byAnimal = useMemo(() => {
    const map = new Map<string, { animal: string; in: number; out: number }>();
    for (const row of rows) {
      const entry = map.get(row.animal_type) ?? { animal: row.animal_type, in: 0, out: 0 };
      entry.in += row.total_in;
      entry.out += row.total_out;
      map.set(row.animal_type, entry);
    }
    return [...map.values()].map((e) => ({ ...e, label: animalLabel(t, e.animal) }));
  }, [rows, t]);

  const hasData = rows.length > 0;

  return (
    <main className="page">
      <div className="card panel">
        <div className="toolbar">
          <div className="field">
            <label htmlFor="s-from">{t.rangeStart}</label>
            <input
              id="s-from"
              type="date"
              className="input"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="s-to">{t.rangeEnd}</label>
            <input
              id="s-to"
              type="date"
              className="input"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="s-group">{t.groupBy}</label>
            <select
              id="s-group"
              className="select"
              value={group}
              onChange={(e) => setGroup(e.target.value as Group)}
            >
              <option value="day">{t.groupDay}</option>
              <option value="week">{t.groupWeek}</option>
              <option value="month">{t.groupMonth}</option>
            </select>
          </div>
        </div>
      </div>

      {!hasData ? (
        <div className="card panel">
          <div className="empty">
            <Icon name="chart" />
            <span>{t.noStatsData}</span>
          </div>
        </div>
      ) : (
        <>
          <article className="card panel">
            <div className="panel-head">
              <h3>{t.dailyFlow}</h3>
            </div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byPeriod}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--c-text-muted)" }} />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: "var(--c-text-muted)" }}
                  />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="in"
                    name={t.totalInLabel}
                    fill="var(--c-primary)"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="out"
                    name={t.totalOutLabel}
                    fill="var(--c-indigo)"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="card panel">
            <div className="panel-head">
              <h3>{t.byAnimalType}</h3>
            </div>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byAnimal} layout="vertical">
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--c-border)"
                    horizontal={false}
                  />
                  <XAxis
                    type="number"
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: "var(--c-text-muted)" }}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={80}
                    tick={{ fontSize: 11, fill: "var(--c-text-muted)" }}
                  />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="in"
                    name={t.totalInLabel}
                    fill="var(--c-primary)"
                    radius={[0, 4, 4, 0]}
                  />
                  <Bar
                    dataKey="out"
                    name={t.totalOutLabel}
                    fill="var(--c-indigo)"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>
        </>
      )}
    </main>
  );
}
