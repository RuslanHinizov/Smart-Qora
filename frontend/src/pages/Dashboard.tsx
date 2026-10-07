import { useState } from "react";
import { useFarmZones, useInventory, useSystemStatus, useStatsToday } from "../api/queries";
import type { AnimalSpecies, InventoryHealth, ZoneKind } from "../api/types";
import { CameraView } from "../components/CameraView";
import type { TranslationKey } from "../i18n/translations";
import { useLanguage } from "../i18n/useLanguage";
import { statusLabel } from "../lib/format";

const TYPES: AnimalSpecies[] = ["sheep", "cattle", "goat", "horse"];
const META = { sheep: "🐑", cattle: "🐄", goat: "🐐", horse: "🐎" } as const;
const SPECIES_KEY: Record<AnimalSpecies, TranslationKey> = {
  sheep: "speciesSheep",
  cattle: "speciesCattle",
  goat: "speciesGoat",
  horse: "speciesHorse",
};

export function Dashboard() {
  const { t } = useLanguage();
  const status = useSystemStatus();
  const stats = useStatsToday();
  const inventory = useInventory();
  const zones = useFarmZones();
  const [selected, setSelected] = useState<AnimalSpecies | null>(null);
  const zoneKinds = new Map((zones.data ?? []).map((zone) => [zone.id, zone.kind]));
  // An EXTERNAL zone is the farm boundary, not a place animals are kept: its
  // balance is "net brought in from outside" (often negative), never a headcount.
  const rows = (inventory.data ?? []).filter(
    (row) => (zoneKinds.get(row.zone_id) ?? "EXTERNAL") !== "EXTERNAL",
  );
  const cameraOnline = status.data?.camera === "ONLINE";
  const totals = stats.data ?? { total_in: 0, total_out: 0, current: 0 };
  const byType = Object.fromEntries(
    TYPES.map((type) => [
      type,
      rows
        .filter(
          (row) =>
            row.species === type &&
            ["PEN", "QUARANTINE"].includes(zoneKinds.get(row.zone_id) ?? "EXTERNAL"),
        )
        .reduce((sum, row) => sum + row.quantity, 0),
    ]),
  ) as Record<AnimalSpecies, number>;
  const total = rows.reduce((sum, row) => sum + row.quantity, 0);
  const quantityIn = (kinds: ZoneKind[]) =>
    rows
      .filter((row) => kinds.includes(zoneKinds.get(row.zone_id) ?? "EXTERNAL"))
      .reduce((sum, row) => sum + row.quantity, 0);
  const inPen = quantityIn(["PEN", "QUARANTINE"]);
  const outside = quantityIn(["PASTURE"]);
  const visibleRows = selected ? rows.filter((row) => row.species === selected) : rows;
  const inventoryHealth = (status.data?.inventory_health ?? "ok") as InventoryHealth;
  return (
    <main className="page dashboard-v2">
      {inventoryHealth !== "ok" && (
        <div className="card banner warn">
          <span className="dot" />
          {inventoryHealth === "mismatch" ? t.inventoryMismatchAlert : t.inventoryUnconfiguredAlert}
        </div>
      )}
      <nav className="animal-filters">
        <button className={!selected ? "active" : ""} onClick={() => setSelected(null)}>
          <span>✦</span>
          <strong>{t.all}</strong>
          <small>{inPen}</small>
        </button>
        {TYPES.map((type) => (
          <button
            key={type}
            className={selected === type ? "active" : ""}
            onClick={() => setSelected(type)}
          >
            <span>{META[type]}</span>
            <strong>{t[SPECIES_KEY[type]]}</strong>
            <small>{byType[type]}</small>
          </button>
        ))}
      </nav>
      <section className="dashboard-v2-grid">
        <article className="card panel live-panel">
          <div className="panel-head">
            <div>
              <span className="section-title">{t.liveCamera}</span>
              <h3>
                {cameraOnline ? t.liveCamera : statusLabel(t, status.data?.camera ?? "OFFLINE")}
              </h3>
            </div>
            <span className={`badge ${cameraOnline ? "" : "off"}`}>
              <span className="dot" />
              {statusLabel(t, status.data?.camera ?? "OFFLINE")}
            </span>
          </div>
          <CameraView active={cameraOnline} />
        </article>
        <div className="dashboard-side">
          <article className="card panel">
            <span className="section-title">{t.todaysMovement}</span>
            <div className="movement-numbers">
              <div>
                <span className="in-dot">↓</span>
                <strong>{totals.total_in}</strong>
                <small>{t.dashboardEntered}</small>
              </div>
              <div>
                <span className="out-dot">↑</span>
                <strong>{totals.total_out}</strong>
                <small>{t.dashboardExited}</small>
              </div>
            </div>
          </article>
          <article className="card panel">
            <div className="panel-head">
              <h3>{t.whereAreAnimals}</h3>
            </div>
            {visibleRows.length ? (
              <div className="location-list">
                {visibleRows.map((row) => (
                  <div key={`${row.zone_id}:${row.group_id}`}>
                    <span>{META[row.species]}</span>
                    <div>
                      <strong>{row.group_name}</strong>
                      <small>{row.zone_name}</small>
                    </div>
                    <b>{row.quantity}</b>
                  </div>
                ))}
              </div>
            ) : (
              <p className="hint">{t.noMovementsYet}</p>
            )}
          </article>
        </div>
      </section>
      <section className="card panel herd-now">
        <div className="panel-head">
          <div>
            <span className="section-title">{t.recordedInventory}</span>
            <h3>{t.dashboardHerdNow}</h3>
          </div>
          <strong className="herd-total">{total}</strong>
        </div>
        <div className="herd-location-summary">
          <div className="herd-place inside">
            <span className="herd-place-icon">⌂</span>
            <div>
              <small>{t.dashboardInPen}</small>
              <strong>{inPen}</strong>
            </div>
          </div>
          <div className="herd-place outside">
            <span className="herd-place-icon">☀</span>
            <div>
              <small>{t.dashboardOutside}</small>
              <strong>{outside}</strong>
            </div>
          </div>
          <div className="herd-breakdown">
            {TYPES.map((type) => (
              <div key={type} className={selected === type ? "selected" : ""}>
                <span>{META[type]}</span>
                <small>{t[SPECIES_KEY[type]]}</small>
                <strong>{byType[type]}</strong>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
