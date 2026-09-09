import { useState } from "react";
import {
  useAnimalGroups,
  useFarmMutations,
  useFarmZones,
  useInventory,
  useInventoryMovements,
} from "../api/queries";
import type { AnimalGroup, AnimalSpecies, FarmZone, ZoneKind } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { Icon } from "../components/Icon";
import { useLanguage } from "../i18n/useLanguage";

const copy = {
  tr: {
    title: "Çiftliğini kur",
    subtitle:
      "Önce alanları ve hayvan sayılarını gir. Kamera daha sonra bu sayıları otomatik günceller.",
    step1: "1. Alanları ekle",
    step2: "2. Hayvan gruplarını ekle",
    step3: "3. Başlangıç sayısını gir",
    quickFarm: "Ana Ağıl ve Mera oluştur",
    quickAnimals: "Koyun, inek, at ve keçiyi ekle",
    areaExample: "Örnek: Ana Ağıl",
    groupExample: "Örnek: Koyun",
    defaultForSpecies: "Bu tür için varsayılan grup",
    defaultBadge: "Varsayılan",
    addArea: "Alanı ekle",
    addGroup: "Grubu ekle",
    inventoryArea: "Hayvanlar şu anda nerede?",
    inventoryHint: "Her hayvan grubunun gerçek sayısını gir.",
    saveStart: "Başlangıç sayısını kaydet",
    current: "Şu anki sayılar",
    physical: "Gerçek sayım ile kontrol et",
    physicalHint: "Fark varsa gerçek sayıyı yaz ve kaydet. Sistem düzeltmeyi ayrıca kaydeder.",
    save: "Kaydet",
    history: "Hareket geçmişi",
    noAreas: "Henüz alan eklenmedi.",
    noGroups: "Henüz hayvan grubu eklenmedi.",
    empty: "Henüz hareket yok.",
    quantity: "Adet",
    reason: "Not / neden",
    setupError: "Kaydedilemedi. Aynı isimde bir kayıt olabilir.",
    transferTitle: "Bölgeler arası aktarım",
    transferHint: "Bir grubu bir bölgeden diğerine elle taşı. Neden zorunludur.",
    from: "Kaynak bölge",
    to: "Hedef bölge",
    transferAction: "Aktar",
    active: "Aktif",
    inactive: "Pasif",
  },
  ru: {
    title: "Настройте ферму",
    subtitle:
      "Сначала укажите зоны и количество животных. Затем камера будет обновлять числа автоматически.",
    step1: "1. Добавьте зоны",
    step2: "2. Добавьте группы животных",
    step3: "3. Укажите начальное количество",
    quickFarm: "Создать загон и пастбище",
    quickAnimals: "Добавить овец, КРС, лошадей и коз",
    areaExample: "Например: Основной загон",
    groupExample: "Например: Овцы",
    defaultForSpecies: "Группа по умолчанию для этого вида",
    defaultBadge: "По умолчанию",
    addArea: "Добавить зону",
    addGroup: "Добавить группу",
    inventoryArea: "Где сейчас животные?",
    inventoryHint: "Укажите фактическое количество в каждой группе.",
    saveStart: "Сохранить начальный остаток",
    current: "Текущие остатки",
    physical: "Сверка с фактическим подсчётом",
    physicalHint: "Если есть разница, укажите фактическое число. Исправление сохранится отдельно.",
    save: "Сохранить",
    history: "История перемещений",
    noAreas: "Зоны ещё не добавлены.",
    noGroups: "Группы животных ещё не добавлены.",
    empty: "Перемещений пока нет.",
    quantity: "Количество",
    reason: "Примечание / причина",
    setupError: "Не удалось сохранить. Возможно, такое название уже есть.",
    transferTitle: "Перемещение между зонами",
    transferHint: "Вручную переместите группу из одной зоны в другую. Причина обязательна.",
    from: "Из зоны",
    to: "В зону",
    transferAction: "Переместить",
    active: "Активна",
    inactive: "Неактивна",
  },
  kk: {
    title: "Ферманы баптаңыз",
    subtitle:
      "Алдымен аймақтар мен мал санын енгізіңіз. Кейін камера сандарды автоматты жаңартады.",
    step1: "1. Аймақтарды қосыңыз",
    step2: "2. Мал топтарын қосыңыз",
    step3: "3. Бастапқы санын енгізіңіз",
    quickFarm: "Қора мен жайылымды құру",
    quickAnimals: "Қой, ірі қара, жылқы және ешкі қосу",
    areaExample: "Мысалы: Негізгі қора",
    groupExample: "Мысалы: Қой",
    defaultForSpecies: "Осы түр үшін негізгі топ",
    defaultBadge: "Негізгі",
    addArea: "Аймақ қосу",
    addGroup: "Топ қосу",
    inventoryArea: "Мал қазір қайда?",
    inventoryHint: "Әр топтың нақты санын енгізіңіз.",
    saveStart: "Бастапқы санды сақтау",
    current: "Қазіргі сан",
    physical: "Нақты санмен салыстыру",
    physicalHint: "Айырма болса, нақты санды жазыңыз. Түзету бөлек сақталады.",
    save: "Сақтау",
    history: "Қозғалыс тарихы",
    noAreas: "Әлі аймақ қосылмады.",
    noGroups: "Әлі мал тобы қосылмады.",
    empty: "Әлі қозғалыс жоқ.",
    quantity: "Саны",
    reason: "Ескерту / себеп",
    setupError: "Сақталмады. Осындай атау бар болуы мүмкін.",
    transferTitle: "Аймақтар арасында ауыстыру",
    transferHint: "Топты бір аймақтан екіншісіне қолмен ауыстырыңыз. Себеп міндетті.",
    from: "Қайдан",
    to: "Қайда",
    transferAction: "Ауыстыру",
    active: "Белсенді",
    inactive: "Белсенді емес",
  },
  en: {
    title: "Set up your farm",
    subtitle:
      "Add the areas and starting animal numbers first. The camera updates them automatically afterwards.",
    step1: "1. Add areas",
    step2: "2. Add animal groups",
    step3: "3. Enter starting numbers",
    quickFarm: "Create pen and pasture",
    quickAnimals: "Add sheep, cattle, horses and goats",
    areaExample: "Example: Main pen",
    groupExample: "Example: Sheep",
    defaultForSpecies: "Default group for this species",
    defaultBadge: "Default",
    addArea: "Add area",
    addGroup: "Add group",
    inventoryArea: "Where are the animals now?",
    inventoryHint: "Enter the actual count for every group.",
    saveStart: "Save starting numbers",
    current: "Current numbers",
    physical: "Check against a physical count",
    physicalHint: "Enter the real number when it differs. The correction is stored separately.",
    save: "Save",
    history: "Movement history",
    noAreas: "No areas yet.",
    noGroups: "No animal groups yet.",
    empty: "No movements yet.",
    quantity: "Quantity",
    reason: "Note / reason",
    setupError: "Could not save. A record with this name may already exist.",
    transferTitle: "Transfer between zones",
    transferHint: "Manually move a group from one zone to another. A reason is required.",
    from: "From zone",
    to: "To zone",
    transferAction: "Transfer",
    active: "Active",
    inactive: "Inactive",
  },
} as const;

const labels: Record<string, Record<string, string>> = {
  tr: {
    PEN: "Ağıl / kapalı alan",
    PASTURE: "Mera / açık alan",
    QUARANTINE: "Karantina",
    EXTERNAL: "Çiftlik dışı",
    sheep: "Koyun",
    cattle: "İnek",
    goat: "Keçi",
    horse: "At",
    INITIAL: "Başlangıç",
    CAMERA: "Kamera geçişi",
    MANUAL_ADJUSTMENT: "Sayım düzeltmesi",
    TRANSFER: "Elle aktarım",
  },
  ru: {
    PEN: "Загон / закрытая зона",
    PASTURE: "Пастбище / открытая зона",
    QUARANTINE: "Карантин",
    EXTERNAL: "Вне фермы",
    sheep: "Овцы",
    cattle: "КРС",
    goat: "Козы",
    horse: "Лошади",
    INITIAL: "Начальный остаток",
    CAMERA: "Проход камеры",
    MANUAL_ADJUSTMENT: "Корректировка подсчёта",
    TRANSFER: "Ручное перемещение",
  },
  kk: {
    PEN: "Қора / жабық аймақ",
    PASTURE: "Жайылым / ашық аймақ",
    QUARANTINE: "Карантин",
    EXTERNAL: "Фермадан тыс",
    sheep: "Қой",
    cattle: "Ірі қара",
    goat: "Ешкі",
    horse: "Жылқы",
    INITIAL: "Бастапқы сан",
    CAMERA: "Камера өтуі",
    MANUAL_ADJUSTMENT: "Сан түзетуі",
    TRANSFER: "Қолмен ауыстыру",
  },
  en: {
    PEN: "Pen / indoor",
    PASTURE: "Pasture / outdoor",
    QUARANTINE: "Quarantine",
    EXTERNAL: "Outside farm",
    sheep: "Sheep",
    cattle: "Cattle",
    goat: "Goats",
    horse: "Horses",
    INITIAL: "Starting inventory",
    CAMERA: "Camera crossing",
    MANUAL_ADJUSTMENT: "Count correction",
    TRANSFER: "Manual transfer",
  },
};
const species: AnimalSpecies[] = ["sheep", "cattle", "goat", "horse"];
const kinds: ZoneKind[] = ["PEN", "PASTURE", "QUARANTINE", "EXTERNAL"];

export function Farm() {
  const { language, t } = useLanguage();
  const { isAdmin } = useAuth();
  const c = copy[language];
  const l = labels[language];
  const zones = useFarmZones();
  const groups = useAnimalGroups();
  const inventory = useInventory();
  const movements = useInventoryMovements();
  const { createZone, updateZone, createGroup, updateGroup, transfer, initialise, reconcile } =
    useFarmMutations();
  const [zoneName, setZoneName] = useState("");
  const [zoneKind, setZoneKind] = useState<ZoneKind>("PEN");
  const [groupName, setGroupName] = useState("");
  const [groupSpecies, setGroupSpecies] = useState<AnimalSpecies>("sheep");
  const [groupDefault, setGroupDefault] = useState(false);
  const [editingZone, setEditingZone] = useState<{ id: number; draft: FarmZone } | null>(null);
  const [editingGroup, setEditingGroup] = useState<{ id: number; draft: AnimalGroup } | null>(null);
  const [transferGroup, setTransferGroup] = useState("");
  const [transferFrom, setTransferFrom] = useState("");
  const [transferTo, setTransferTo] = useState("");
  const [transferQty, setTransferQty] = useState("");
  const [transferNote, setTransferNote] = useState("");
  const [startZone, setStartZone] = useState("");
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [physical, setPhysical] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState(false);
  const zoneList = zones.data ?? [];
  const groupList = groups.data ?? [];
  const rows = inventory.data ?? [];
  const hasInventory = rows.length > 0;
  const submit = async (run: () => Promise<unknown>) => {
    setError(false);
    try {
      await run();
    } catch {
      setError(true);
    }
  };
  const quickFarm = () =>
    submit(async () => {
      await createZone.mutateAsync({
        name: language === "tr" ? "Ana Ağıl" : language === "ru" ? "Основной загон" : "Main Pen",
        kind: "PEN",
        is_active: true,
        sort_order: 0,
      });
      await createZone.mutateAsync({
        name: language === "tr" ? "Mera" : language === "ru" ? "Пастбище" : "Pasture",
        kind: "PASTURE",
        is_active: true,
        sort_order: 1,
      });
    });
  const quickAnimals = () =>
    submit(async () => {
      const names =
        language === "tr"
          ? ["Koyun", "İnek", "At", "Keçi"]
          : language === "ru"
            ? ["Овцы", "КРС", "Лошади", "Козы"]
            : ["Sheep", "Cattle", "Horses", "Goats"];
      for (const [index, type] of ["sheep", "cattle", "horse", "goat"].entries())
        await createGroup.mutateAsync({
          name: names[index],
          species: type as AnimalSpecies,
          is_default_for_species: false,
          is_active: true,
          sort_order: index,
        });
    });
  return (
    <main className="page farm-page">
      <div className="page-head">
        <div>
          <span className="section-title">{c.title}</span>
          <p>{c.subtitle}</p>
        </div>
      </div>
      {!isAdmin && <div className="notice">{t.readOnlyForViewers}</div>}
      {error && <div className="notice">{c.setupError}</div>}
      <section className="farm-steps">
        <div className={zoneList.length ? "done" : ""}>
          <b>1</b>
          <span>{c.step1}</span>
        </div>
        <div className={groupList.length ? "done" : ""}>
          <b>2</b>
          <span>{c.step2}</span>
        </div>
        <div className={hasInventory ? "done" : ""}>
          <b>3</b>
          <span>{c.step3}</span>
        </div>
      </section>
      <div className="grid-2 even">
        <section className="card panel">
          <div className="panel-head">
            <h3>{c.step1}</h3>
            {zoneList.length === 0 && isAdmin && (
              <button className="btn sm primary" onClick={quickFarm}>
                {c.quickFarm}
              </button>
            )}
          </div>
          {zoneList.length ? (
            <div className="farm-list">
              {zoneList.map((zone) =>
                editingZone?.id === zone.id ? (
                  <div key={zone.id} className="farm-edit-row">
                    <input
                      className="input"
                      value={editingZone.draft.name}
                      onChange={(e) =>
                        setEditingZone({ id: zone.id, draft: { ...editingZone.draft, name: e.target.value } })
                      }
                    />
                    <select
                      className="select"
                      value={editingZone.draft.kind}
                      onChange={(e) =>
                        setEditingZone({
                          id: zone.id,
                          draft: { ...editingZone.draft, kind: e.target.value as ZoneKind },
                        })
                      }
                    >
                      {kinds.map((kind) => (
                        <option key={kind} value={kind}>
                          {l[kind]}
                        </option>
                      ))}
                    </select>
                    <label className="farm-add-check">
                      <input
                        type="checkbox"
                        checked={editingZone.draft.is_active}
                        onChange={(e) =>
                          setEditingZone({
                            id: zone.id,
                            draft: { ...editingZone.draft, is_active: e.target.checked },
                          })
                        }
                      />
                      {c.active}
                    </label>
                    <button
                      className="btn sm primary"
                      disabled={!editingZone.draft.name || updateZone.isPending}
                      onClick={() =>
                        submit(async () => {
                          await updateZone.mutateAsync({ id: zone.id, input: editingZone.draft });
                          setEditingZone(null);
                        })
                      }
                    >
                      {t.save}
                    </button>
                    <button className="btn sm ghost" onClick={() => setEditingZone(null)}>
                      {t.cancel}
                    </button>
                  </div>
                ) : (
                  <div key={zone.id}>
                    <span className="farm-dot" />
                    <strong>{zone.name}</strong>
                    <small>{zone.is_active ? l[zone.kind] : `${l[zone.kind]} · ${c.inactive}`}</small>
                    {isAdmin && (
                      <button className="btn sm ghost" onClick={() => setEditingZone({ id: zone.id, draft: zone })}>
                        {t.edit}
                      </button>
                    )}
                  </div>
                ),
              )}
            </div>
          ) : (
            <p className="hint">{c.noAreas}</p>
          )}
          {isAdmin && (
            <div className="farm-add">
              <input
                className="input"
                placeholder={c.areaExample}
                value={zoneName}
                onChange={(e) => setZoneName(e.target.value)}
              />
              <select
                className="select"
                value={zoneKind}
                onChange={(e) => setZoneKind(e.target.value as ZoneKind)}
              >
                {kinds.map((kind) => (
                  <option key={kind} value={kind}>
                    {l[kind]}
                  </option>
                ))}
              </select>
              <button
                className="btn"
                disabled={!zoneName || createZone.isPending}
                onClick={() =>
                  submit(async () => {
                    await createZone.mutateAsync({
                      name: zoneName,
                      kind: zoneKind,
                      is_active: true,
                      sort_order: zoneList.length,
                    });
                    setZoneName("");
                  })
                }
              >
                <Icon name="plus" size={16} />
                {c.addArea}
              </button>
            </div>
          )}
        </section>
        <section className="card panel">
          <div className="panel-head">
            <h3>{c.step2}</h3>
            {groupList.length === 0 && isAdmin && (
              <button className="btn sm primary" onClick={quickAnimals}>
                {c.quickAnimals}
              </button>
            )}
          </div>
          {groupList.length ? (
            <div className="farm-list">
              {groupList.map((group) =>
                editingGroup?.id === group.id ? (
                  <div key={group.id} className="farm-edit-row">
                    <input
                      className="input"
                      value={editingGroup.draft.name}
                      onChange={(e) =>
                        setEditingGroup({
                          id: group.id,
                          draft: { ...editingGroup.draft, name: e.target.value },
                        })
                      }
                    />
                    <select
                      className="select"
                      value={editingGroup.draft.species}
                      onChange={(e) =>
                        setEditingGroup({
                          id: group.id,
                          draft: { ...editingGroup.draft, species: e.target.value as AnimalSpecies },
                        })
                      }
                    >
                      {species.map((type) => (
                        <option key={type} value={type}>
                          {l[type]}
                        </option>
                      ))}
                    </select>
                    <label className="farm-add-check">
                      <input
                        type="checkbox"
                        checked={editingGroup.draft.is_default_for_species}
                        onChange={(e) =>
                          setEditingGroup({
                            id: group.id,
                            draft: { ...editingGroup.draft, is_default_for_species: e.target.checked },
                          })
                        }
                      />
                      {c.defaultForSpecies}
                    </label>
                    <label className="farm-add-check">
                      <input
                        type="checkbox"
                        checked={editingGroup.draft.is_active}
                        onChange={(e) =>
                          setEditingGroup({
                            id: group.id,
                            draft: { ...editingGroup.draft, is_active: e.target.checked },
                          })
                        }
                      />
                      {c.active}
                    </label>
                    <button
                      className="btn sm primary"
                      disabled={!editingGroup.draft.name || updateGroup.isPending}
                      onClick={() =>
                        submit(async () => {
                          await updateGroup.mutateAsync({ id: group.id, input: editingGroup.draft });
                          setEditingGroup(null);
                        })
                      }
                    >
                      {t.save}
                    </button>
                    <button className="btn sm ghost" onClick={() => setEditingGroup(null)}>
                      {t.cancel}
                    </button>
                  </div>
                ) : (
                  <div key={group.id}>
                    <span className="farm-dot animal" />
                    <strong>{group.name}</strong>
                    <small>{group.is_active ? l[group.species] : `${l[group.species]} · ${c.inactive}`}</small>
                    {group.is_default_for_species && <span className="pill">{c.defaultBadge}</span>}
                    {isAdmin && (
                      <button
                        className="btn sm ghost"
                        onClick={() => setEditingGroup({ id: group.id, draft: group })}
                      >
                        {t.edit}
                      </button>
                    )}
                  </div>
                ),
              )}
            </div>
          ) : (
            <p className="hint">{c.noGroups}</p>
          )}
          {isAdmin && (
            <div className="farm-add with-check">
              <input
                className="input"
                placeholder={c.groupExample}
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
              />
              <select
                className="select"
                value={groupSpecies}
                onChange={(e) => setGroupSpecies(e.target.value as AnimalSpecies)}
              >
                {species.map((type) => (
                  <option key={type} value={type}>
                    {l[type]}
                  </option>
                ))}
              </select>
              <label className="farm-add-check">
                <input
                  type="checkbox"
                  checked={groupDefault}
                  onChange={(e) => setGroupDefault(e.target.checked)}
                />
                {c.defaultForSpecies}
              </label>
              <button
                className="btn"
                disabled={!groupName || createGroup.isPending}
                onClick={() =>
                  submit(async () => {
                    await createGroup.mutateAsync({
                      name: groupName,
                      species: groupSpecies,
                      is_default_for_species: groupDefault,
                      is_active: true,
                      sort_order: groupList.length,
                    });
                    setGroupName("");
                    setGroupDefault(false);
                  })
                }
              >
                <Icon name="plus" size={16} />
                {c.addGroup}
              </button>
            </div>
          )}
        </section>
      </div>
      {!hasInventory && (
        <section className="card panel farm-initial">
          <div className="panel-head">
            <h3>{c.step3}</h3>
          </div>
          <p className="hint">{c.inventoryHint}</p>
          <label className="field">
            <span>{c.inventoryArea}</span>
            <select
              className="select"
              value={startZone}
              onChange={(e) => setStartZone(e.target.value)}
              disabled={!isAdmin}
            >
              <option value="">{c.areaExample}</option>
              {zoneList.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name}
                </option>
              ))}
            </select>
          </label>
          <div className="farm-quantity-grid">
            {groupList.map((group) => (
              <label className="field" key={group.id}>
                <span>{group.name}</span>
                <input
                  className="input"
                  min="0"
                  type="number"
                  placeholder="0"
                  value={quantities[group.id] ?? ""}
                  onChange={(e) =>
                    setQuantities((current) => ({ ...current, [group.id]: e.target.value }))
                  }
                  disabled={!isAdmin}
                />
              </label>
            ))}
          </div>
          {isAdmin && (
            <button
              className="btn primary"
              disabled={
                !startZone ||
                !groupList.some((group) => Number(quantities[group.id]) > 0) ||
                initialise.isPending
              }
              onClick={() =>
                submit(() =>
                  initialise.mutateAsync({
                    zone_id: Number(startZone),
                    entries: groupList
                      .filter((group) => Number(quantities[group.id]) > 0)
                      .map((group) => ({
                        group_id: group.id,
                        quantity: Number(quantities[group.id]),
                      })),
                    note: "Initial inventory",
                  }),
                )
              }
            >
              {c.saveStart}
            </button>
          )}
        </section>
      )}
      {hasInventory && (
        <>
          <section className="card panel">
            <div className="panel-head">
              <h3>{c.current}</h3>
            </div>
            <div className="farm-balance-grid">
              {rows.map((row) => (
                <article key={`${row.zone_id}:${row.group_id}`}>
                  <span>{row.zone_name}</span>
                  <strong>{row.quantity}</strong>
                  <small>{row.group_name}</small>
                </article>
              ))}
            </div>
          </section>
          <section className="card panel">
            <div className="panel-head">
              <h3>{c.physical}</h3>
            </div>
            <p className="hint">{c.physicalHint}</p>
            <input
              className="input"
              placeholder={c.reason}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={!isAdmin}
            />
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{c.step1}</th>
                    <th>{c.step2}</th>
                    <th>{c.quantity}</th>
                    <th>{c.physical}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const key = `${row.zone_id}:${row.group_id}`;
                    return (
                      <tr key={key}>
                        <td>{row.zone_name}</td>
                        <td>{row.group_name}</td>
                        <td>{row.quantity}</td>
                        <td>
                          <input
                            className="input"
                            min="0"
                            type="number"
                            value={physical[key] ?? ""}
                            onChange={(e) =>
                              setPhysical((current) => ({ ...current, [key]: e.target.value }))
                            }
                            disabled={!isAdmin}
                          />
                        </td>
                        <td>
                          {isAdmin && (
                            <button
                              className="btn sm"
                              disabled={physical[key] === undefined || reconcile.isPending}
                              onClick={() =>
                                submit(() =>
                                  reconcile.mutateAsync({
                                    zone_id: row.zone_id,
                                    group_id: row.group_id,
                                    physical_quantity: Number(physical[key]),
                                    note: note || "Physical count",
                                  }),
                                )
                              }
                            >
                              {c.save}
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
          <section className="card panel">
            <div className="panel-head">
              <h3>{c.transferTitle}</h3>
            </div>
            <p className="hint">{c.transferHint}</p>
            {isAdmin && (
              <div className="farm-transfer-grid">
                <select className="select" value={transferGroup} onChange={(e) => setTransferGroup(e.target.value)}>
                  <option value="">{c.step2}</option>
                  {groupList.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
                <select className="select" value={transferFrom} onChange={(e) => setTransferFrom(e.target.value)}>
                  <option value="">{c.from}</option>
                  {zoneList.map((zone) => (
                    <option key={zone.id} value={zone.id}>
                      {zone.name}
                    </option>
                  ))}
                </select>
                <select className="select" value={transferTo} onChange={(e) => setTransferTo(e.target.value)}>
                  <option value="">{c.to}</option>
                  {zoneList.map((zone) => (
                    <option key={zone.id} value={zone.id}>
                      {zone.name}
                    </option>
                  ))}
                </select>
                <input
                  className="input"
                  type="number"
                  min="1"
                  placeholder={c.quantity}
                  value={transferQty}
                  onChange={(e) => setTransferQty(e.target.value)}
                />
                <input
                  className="input"
                  placeholder={c.reason}
                  value={transferNote}
                  onChange={(e) => setTransferNote(e.target.value)}
                />
                <button
                  className="btn primary"
                  disabled={
                    !transferGroup ||
                    (!transferFrom && !transferTo) ||
                    (transferFrom !== "" && transferFrom === transferTo) ||
                    !transferQty ||
                    Number(transferQty) <= 0 ||
                    transferNote.trim().length < 3 ||
                    transfer.isPending
                  }
                  onClick={() =>
                    submit(async () => {
                      await transfer.mutateAsync({
                        group_id: Number(transferGroup),
                        from_zone_id: transferFrom ? Number(transferFrom) : null,
                        to_zone_id: transferTo ? Number(transferTo) : null,
                        quantity: Number(transferQty),
                        note: transferNote,
                      });
                      setTransferGroup("");
                      setTransferFrom("");
                      setTransferTo("");
                      setTransferQty("");
                      setTransferNote("");
                    })
                  }
                >
                  {c.transferAction}
                </button>
              </div>
            )}
          </section>
          <section className="card panel">
            <div className="panel-head">
              <h3>{c.history}</h3>
            </div>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{c.history}</th>
                    <th>{c.quantity}</th>
                    <th>{c.reason}</th>
                  </tr>
                </thead>
                <tbody>
                  {(movements.data ?? []).map((movement) => (
                    <tr key={movement.id}>
                      <td>{l[movement.kind]}</td>
                      <td>{movement.quantity}</td>
                      <td>{movement.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {movements.data?.length === 0 && <span className="hint">{c.empty}</span>}
          </section>
        </>
      )}
    </main>
  );
}
