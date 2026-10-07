import { useState } from "react";
import {
  useAnimalGroups,
  useFarmMutations,
  useFarmZones,
  useInventory,
  useInventoryMovements,
} from "../api/queries";
import type { AnimalGroup, AnimalSpecies, FarmZone, MovementKind, ZoneKind } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { Icon } from "../components/Icon";
import type { TranslationKey } from "../i18n/translations";
import { useLanguage } from "../i18n/useLanguage";

const species: AnimalSpecies[] = ["sheep", "cattle", "goat", "horse"];
const kinds: ZoneKind[] = ["PEN", "PASTURE", "QUARANTINE", "EXTERNAL"];

const SPECIES_KEY: Record<AnimalSpecies, TranslationKey> = {
  sheep: "speciesSheep",
  cattle: "speciesCattle",
  goat: "speciesGoat",
  horse: "speciesHorse",
};
const ZONE_KIND_KEY: Record<ZoneKind, TranslationKey> = {
  PEN: "zoneKindPen",
  PASTURE: "zoneKindPasture",
  QUARANTINE: "zoneKindQuarantine",
  EXTERNAL: "zoneKindExternal",
};
const MOVEMENT_KIND_KEY: Record<MovementKind, TranslationKey> = {
  INITIAL: "movementKindInitial",
  CAMERA: "movementKindCamera",
  MANUAL_ADJUSTMENT: "movementKindManualAdjustment",
  TRANSFER: "movementKindTransfer",
};
const QUICK_PEN_NAME = { tr: "Ana Ağıl", ru: "Основной загон", kk: "Негізгі қора", en: "Main Pen" };
const QUICK_PASTURE_NAME = { tr: "Mera", ru: "Пастбище", kk: "Жайылым", en: "Pasture" };

export function Farm() {
  const { language, t } = useLanguage();
  const { isAdmin } = useAuth();
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
        name: QUICK_PEN_NAME[language],
        kind: "PEN",
        is_active: true,
        sort_order: 0,
      });
      await createZone.mutateAsync({
        name: QUICK_PASTURE_NAME[language],
        kind: "PASTURE",
        is_active: true,
        sort_order: 1,
      });
    });
  const quickAnimals = () =>
    submit(async () => {
      for (const [index, type] of species.entries())
        await createGroup.mutateAsync({
          name: t[SPECIES_KEY[type]],
          species: type,
          is_default_for_species: false,
          is_active: true,
          sort_order: index,
        });
    });
  return (
    <main className="page farm-page">
      <div className="page-head">
        <div>
          <span className="section-title">{t.farmTitle}</span>
          <p>{t.farmSubtitle}</p>
        </div>
      </div>
      {!isAdmin && <div className="notice">{t.readOnlyForViewers}</div>}
      {error && <div className="notice">{t.farmSetupError}</div>}
      <section className="farm-steps">
        <div className={zoneList.length ? "done" : ""}>
          <b>1</b>
          <span>{t.farmStep1}</span>
        </div>
        <div className={groupList.length ? "done" : ""}>
          <b>2</b>
          <span>{t.farmStep2}</span>
        </div>
        <div className={hasInventory ? "done" : ""}>
          <b>3</b>
          <span>{t.farmStep3}</span>
        </div>
      </section>
      <div className="grid-2 even">
        <section className="card panel">
          <div className="panel-head">
            <h3>{t.farmStep1}</h3>
            {zoneList.length === 0 && isAdmin && (
              <button className="btn sm primary" onClick={quickFarm}>
                {t.farmQuickZones}
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
                        setEditingZone({
                          id: zone.id,
                          draft: { ...editingZone.draft, name: e.target.value },
                        })
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
                          {t[ZONE_KIND_KEY[kind]]}
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
                      {t.activeToggle}
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
                    <small>
                      {zone.is_active
                        ? t[ZONE_KIND_KEY[zone.kind]]
                        : `${t[ZONE_KIND_KEY[zone.kind]]} · ${t.inactive}`}
                    </small>
                    {isAdmin && (
                      <button
                        className="btn sm ghost"
                        onClick={() => setEditingZone({ id: zone.id, draft: zone })}
                      >
                        {t.edit}
                      </button>
                    )}
                  </div>
                ),
              )}
            </div>
          ) : (
            <p className="hint">{t.farmNoAreas}</p>
          )}
          {isAdmin && (
            <div className="farm-add">
              <input
                className="input"
                placeholder={t.farmAreaExample}
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
                    {t[ZONE_KIND_KEY[kind]]}
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
                {t.farmAddArea}
              </button>
            </div>
          )}
        </section>
        <section className="card panel">
          <div className="panel-head">
            <h3>{t.farmStep2}</h3>
            {groupList.length === 0 && isAdmin && (
              <button className="btn sm primary" onClick={quickAnimals}>
                {t.farmQuickGroups}
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
                          draft: {
                            ...editingGroup.draft,
                            species: e.target.value as AnimalSpecies,
                          },
                        })
                      }
                    >
                      {species.map((type) => (
                        <option key={type} value={type}>
                          {t[SPECIES_KEY[type]]}
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
                            draft: {
                              ...editingGroup.draft,
                              is_default_for_species: e.target.checked,
                            },
                          })
                        }
                      />
                      {t.farmDefaultForSpecies}
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
                      {t.activeToggle}
                    </label>
                    <button
                      className="btn sm primary"
                      disabled={!editingGroup.draft.name || updateGroup.isPending}
                      onClick={() =>
                        submit(async () => {
                          await updateGroup.mutateAsync({
                            id: group.id,
                            input: editingGroup.draft,
                          });
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
                    <small>
                      {group.is_active
                        ? t[SPECIES_KEY[group.species]]
                        : `${t[SPECIES_KEY[group.species]]} · ${t.inactive}`}
                    </small>
                    {group.is_default_for_species && (
                      <span className="pill">{t.farmDefaultBadge}</span>
                    )}
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
            <p className="hint">{t.farmNoGroups}</p>
          )}
          {isAdmin && (
            <div className="farm-add with-check">
              <input
                className="input"
                placeholder={t.farmGroupExample}
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
                    {t[SPECIES_KEY[type]]}
                  </option>
                ))}
              </select>
              <label className="farm-add-check">
                <input
                  type="checkbox"
                  checked={groupDefault}
                  onChange={(e) => setGroupDefault(e.target.checked)}
                />
                {t.farmDefaultForSpecies}
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
                {t.farmAddGroup}
              </button>
            </div>
          )}
        </section>
      </div>
      {!hasInventory && (
        <section className="card panel farm-initial">
          <div className="panel-head">
            <h3>{t.farmStep3}</h3>
          </div>
          <p className="hint">{t.farmInventoryHint}</p>
          <label className="field">
            <span>{t.farmInventoryArea}</span>
            <select
              className="select"
              value={startZone}
              onChange={(e) => setStartZone(e.target.value)}
              disabled={!isAdmin}
            >
              <option value="">{t.farmAreaExample}</option>
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
              {t.farmSaveStart}
            </button>
          )}
        </section>
      )}
      {hasInventory && (
        <>
          <section className="card panel">
            <div className="panel-head">
              <h3>{t.farmCurrent}</h3>
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
              <h3>{t.farmPhysical}</h3>
            </div>
            <p className="hint">{t.farmPhysicalHint}</p>
            <input
              className="input"
              placeholder={t.reason}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={!isAdmin}
            />
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{t.farmStep1}</th>
                    <th>{t.farmStep2}</th>
                    <th>{t.quantity}</th>
                    <th>{t.farmPhysical}</th>
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
                              {t.save}
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
              <h3>{t.farmTransferTitle}</h3>
            </div>
            <p className="hint">{t.farmTransferHint}</p>
            {isAdmin && (
              <div className="farm-transfer-grid">
                <select
                  className="select"
                  value={transferGroup}
                  onChange={(e) => setTransferGroup(e.target.value)}
                >
                  <option value="">{t.farmStep2}</option>
                  {groupList.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
                <select
                  className="select"
                  value={transferFrom}
                  onChange={(e) => setTransferFrom(e.target.value)}
                >
                  <option value="">{t.fromZone}</option>
                  {zoneList.map((zone) => (
                    <option key={zone.id} value={zone.id}>
                      {zone.name}
                    </option>
                  ))}
                </select>
                <select
                  className="select"
                  value={transferTo}
                  onChange={(e) => setTransferTo(e.target.value)}
                >
                  <option value="">{t.toZone}</option>
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
                  placeholder={t.quantity}
                  value={transferQty}
                  onChange={(e) => setTransferQty(e.target.value)}
                />
                <input
                  className="input"
                  placeholder={t.reason}
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
                  {t.farmTransferAction}
                </button>
              </div>
            )}
          </section>
          <section className="card panel">
            <div className="panel-head">
              <h3>{t.farmHistory}</h3>
            </div>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{t.farmHistory}</th>
                    <th>{t.quantity}</th>
                    <th>{t.reason}</th>
                  </tr>
                </thead>
                <tbody>
                  {(movements.data ?? []).map((movement) => (
                    <tr key={movement.id}>
                      <td>{t[MOVEMENT_KIND_KEY[movement.kind]]}</td>
                      <td>{movement.quantity}</td>
                      <td>{movement.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {movements.data?.length === 0 && <span className="hint">{t.noMovementsYet}</span>}
          </section>
        </>
      )}
    </main>
  );
}
