import { useState } from "react";
import { useFarmZones, useInventory, useSystemStatus, useStatsToday } from "../api/queries";
import type { AnimalSpecies, InventoryHealth, ZoneKind } from "../api/types";
import { CameraView } from "../components/CameraView";
import { useLanguage } from "../i18n/useLanguage";
import { statusLabel } from "../lib/format";

const TYPES: AnimalSpecies[] = ["sheep", "cattle", "goat", "horse"];
const META = { sheep: "🐑", cattle: "🐄", goat: "🐐", horse: "🐎" } as const;
const names = {
  tr: {
    all: "Tümü",
    inPen: "Qorada",
    outside: "Dışarıda / merada",
    herdNow: "Hayvanların şu anki yeri",
    inventory: "Kayıtlı envanter",
    camera: "Canlı kamera",
    movement: "Bugünkü hareket",
    entered: "Giriş",
    exited: "Çıkış",
    locations: "Hayvanlar nerede?",
    recent: "Son hareketler",
    empty: "Henüz hareket yok",
    animals: { sheep: "Koyun", cattle: "İnek", goat: "Keçi", horse: "At" },
    inventoryMismatch: "Bir kapı geçişi envanteri güncelleyemedi — kaynak bölgede yeterli hayvan kaydı yok. Fiziksel sayım gerekli.",
    inventoryUnconfigured: "Bir kapı geçişi hiçbir hayvan grubuna bağlanamadı. Çiftlik sayfasından grupları kontrol edin.",
  },
  ru: {
    all: "Все",
    inPen: "В загоне",
    outside: "Снаружи / на пастбище",
    herdNow: "Где животные сейчас",
    inventory: "Учётный остаток",
    camera: "Камера в реальном времени",
    movement: "Движения сегодня",
    entered: "Вход",
    exited: "Выход",
    locations: "Где животные?",
    recent: "Последние перемещения",
    empty: "Перемещений пока нет",
    animals: { sheep: "Овцы", cattle: "КРС", goat: "Козы", horse: "Лошади" },
    inventoryMismatch: "Проход через ворота не обновил учётный остаток — в исходной зоне недостаточно животных. Нужна физическая сверка.",
    inventoryUnconfigured: "Проход через ворота не привязан к группе животных. Проверьте группы на странице «Ферма».",
  },
  kk: {
    all: "Барлығы",
    inPen: "Қорада",
    outside: "Сыртта / жайылымда",
    herdNow: "Мал қазір қайда",
    inventory: "Есептегі мал",
    camera: "Тікелей камера",
    movement: "Бүгінгі қозғалыс",
    entered: "Кіру",
    exited: "Шығу",
    locations: "Мал қайда?",
    recent: "Соңғы қозғалыстар",
    empty: "Әзірге қозғалыс жоқ",
    animals: { sheep: "Қой", cattle: "Ірі қара", goat: "Ешкі", horse: "Жылқы" },
    inventoryMismatch: "Қақпадан өту есептегі қалдықты жаңарта алмады — көзі аймақта мал жеткіліксіз. Физикалық тексеру керек.",
    inventoryUnconfigured: "Қақпадан өту ешбір мал тобына байланыстырылмады. «Ферма» бетінде топтарды тексеріңіз.",
  },
  en: {
    all: "All",
    inPen: "In the pen",
    outside: "Outside / pasture",
    herdNow: "Where animals are now",
    inventory: "Recorded inventory",
    camera: "Live camera",
    movement: "Today's movement",
    entered: "Entered",
    exited: "Exited",
    locations: "Where are the animals?",
    recent: "Recent movements",
    empty: "No movements yet",
    animals: { sheep: "Sheep", cattle: "Cattle", goat: "Goats", horse: "Horses" },
    inventoryMismatch: "A gate crossing could not update the inventory — the source zone does not have enough animals recorded. Physical verification needed.",
    inventoryUnconfigured: "A gate crossing is not linked to any animal group. Check the groups on the Farm page.",
  },
} as const;

export function Dashboard() {
  const { language, t } = useLanguage();
  const c = names[language];
  const status = useSystemStatus();
  const stats = useStatsToday();
  const inventory = useInventory();
  const zones = useFarmZones();
  const [selected, setSelected] = useState<AnimalSpecies | null>(null);
  const rows = inventory.data ?? [];
  const zoneKinds = new Map((zones.data ?? []).map((zone) => [zone.id, zone.kind]));
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
  const outside = quantityIn(["PASTURE", "EXTERNAL"]);
  const visibleRows = selected ? rows.filter((row) => row.species === selected) : rows;
  const inventoryHealth = (status.data?.inventory_health ?? "ok") as InventoryHealth;
  return (
    <main className="page dashboard-v2">
      {inventoryHealth !== "ok" && (
        <div className="card banner warn">
          <span className="dot" />
          {inventoryHealth === "mismatch" ? c.inventoryMismatch : c.inventoryUnconfigured}
        </div>
      )}
      <nav className="animal-filters">
        <button className={!selected ? "active" : ""} onClick={() => setSelected(null)}>
          <span>✦</span>
          <strong>{c.all}</strong>
          <small>{inPen}</small>
        </button>
        {TYPES.map((type) => (
          <button
            key={type}
            className={selected === type ? "active" : ""}
            onClick={() => setSelected(type)}
          >
            <span>{META[type]}</span>
            <strong>{c.animals[type]}</strong>
            <small>{byType[type]}</small>
          </button>
        ))}
      </nav>
      <section className="dashboard-v2-grid">
        <article className="card panel live-panel">
          <div className="panel-head">
            <div>
              <span className="section-title">{c.camera}</span>
              <h3>{cameraOnline ? c.camera : statusLabel(t, status.data?.camera ?? "OFFLINE")}</h3>
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
            <span className="section-title">{c.movement}</span>
            <div className="movement-numbers">
              <div>
                <span className="in-dot">↓</span>
                <strong>{totals.total_in}</strong>
                <small>{c.entered}</small>
              </div>
              <div>
                <span className="out-dot">↑</span>
                <strong>{totals.total_out}</strong>
                <small>{c.exited}</small>
              </div>
            </div>
          </article>
          <article className="card panel">
            <div className="panel-head">
              <h3>{c.locations}</h3>
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
              <p className="hint">{c.empty}</p>
            )}
          </article>
        </div>
      </section>
      <section className="card panel herd-now">
        <div className="panel-head">
          <div>
            <span className="section-title">{c.inventory}</span>
            <h3>{c.herdNow}</h3>
          </div>
          <strong className="herd-total">{total}</strong>
        </div>
        <div className="herd-location-summary">
          <div className="herd-place inside">
            <span className="herd-place-icon">⌂</span>
            <div>
              <small>{c.inPen}</small>
              <strong>{inPen}</strong>
            </div>
          </div>
          <div className="herd-place outside">
            <span className="herd-place-icon">☀</span>
            <div>
              <small>{c.outside}</small>
              <strong>{outside}</strong>
            </div>
          </div>
          <div className="herd-breakdown">
            {TYPES.map((type) => (
              <div key={type} className={selected === type ? "selected" : ""}>
                <span>{META[type]}</span>
                <small>{c.animals[type]}</small>
                <strong>{byType[type]}</strong>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
