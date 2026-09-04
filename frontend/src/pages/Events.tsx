import { useMemo, useState } from "react";
import { useEvents } from "../api/queries";
import type { Direction, EventQuery } from "../api/types";
import { Icon } from "../components/Icon";
import { useLanguage } from "../i18n/useLanguage";
import { animalLabel, formatDateTime } from "../lib/format";

const PAGE_SIZE = 25;
const ANIMALS = ["sheep", "cattle", "goat", "horse"];

export function Events() {
  const { language, t } = useLanguage();
  const [page, setPage] = useState(0);
  const [direction, setDirection] = useState<Direction | "">("");
  const [animal, setAnimal] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const query = useMemo<EventQuery>(() => {
    const q: EventQuery = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
    if (direction) q.direction = direction;
    if (animal) q.animal_type = animal;
    if (from) q.from = `${from}T00:00:00`;
    if (to) q.to = `${to}T23:59:59`;
    return q;
  }, [page, direction, animal, from, to]);

  const events = useEvents(query);
  const total = events.data?.total ?? 0;
  const rows = events.data?.rows ?? [];
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const reset = () => {
    setDirection("");
    setAnimal("");
    setFrom("");
    setTo("");
    setPage(0);
  };
  const onFilter = (fn: () => void) => {
    fn();
    setPage(0);
  };

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <span className="section-title">{t.events}</span>
          <p>
            {total} {t.totalRows}
          </p>
        </div>
      </div>

      <div className="card panel">
        <div className="toolbar">
          <div className="field">
            <label htmlFor="f-dir">{t.direction}</label>
            <select
              id="f-dir"
              className="select"
              value={direction}
              onChange={(e) => onFilter(() => setDirection(e.target.value as Direction | ""))}
            >
              <option value="">{t.all}</option>
              <option value="IN">{t.dirIn}</option>
              <option value="OUT">{t.dirOut}</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-animal">{t.animalType}</label>
            <select
              id="f-animal"
              className="select"
              value={animal}
              onChange={(e) => onFilter(() => setAnimal(e.target.value))}
            >
              <option value="">{t.all}</option>
              {ANIMALS.map((a) => (
                <option key={a} value={a}>
                  {animalLabel(t, a)}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-from">{t.dateFrom}</label>
            <input
              id="f-from"
              type="date"
              className="input"
              value={from}
              onChange={(e) => onFilter(() => setFrom(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="f-to">{t.dateTo}</label>
            <input
              id="f-to"
              type="date"
              className="input"
              value={to}
              onChange={(e) => onFilter(() => setTo(e.target.value))}
            />
          </div>
          <button className="btn sm ghost" onClick={reset}>
            <Icon name="x" size={14} />
            {t.clearFilters}
          </button>
        </div>

        {rows.length === 0 ? (
          <div className="empty">
            <Icon name="events" />
            <span>{t.noEventsFound}</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t.time}</th>
                  <th>{t.animalType}</th>
                  <th>{t.direction}</th>
                  <th>{t.confidence}</th>
                  <th>ID</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDateTime(event.timestamp, language)}</td>
                    <td style={{ textTransform: "capitalize" }}>
                      {animalLabel(t, event.animal_type)}
                    </td>
                    <td>
                      <span className={event.direction === "IN" ? "pill-in" : "pill-out"}>
                        {event.direction === "IN" ? t.dirIn : t.dirOut}
                      </span>
                    </td>
                    <td>{Math.round(event.confidence * 100)}%</td>
                    <td>{event.tracking_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="pager">
          <span>
            {t.page} {page + 1} {t.rowsOf} {pages}
          </span>
          <span style={{ display: "flex", gap: "var(--sp-2)" }}>
            <button
              className="btn sm"
              disabled={page === 0}
              aria-label={t.back}
              onClick={() => setPage((p) => p - 1)}
            >
              <span style={{ transform: "rotate(180deg)" }}>
                <Icon name="arrow" size={14} />
              </span>
            </button>
            <button
              className="btn sm"
              disabled={page + 1 >= pages}
              aria-label={t.dirRight}
              onClick={() => setPage((p) => p + 1)}
            >
              <Icon name="arrow" size={14} />
            </button>
          </span>
        </div>
      </div>
    </main>
  );
}
