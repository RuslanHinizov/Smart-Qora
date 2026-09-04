import { useState } from "react";
import { useCameraMutations, useCameras } from "../api/queries";
import type { Camera, CameraInput, InsideDirection } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { Icon } from "../components/Icon";
import { LineEditor } from "../components/LineEditor";
import { useLanguage } from "../i18n/useLanguage";

const EMPTY: CameraInput = {
  name: "",
  source: "",
  location: "",
  is_active: true,
  line_p1_x: null,
  line_p1_y: null,
  line_p2_x: null,
  line_p2_y: null,
  line2_p1_x: null,
  line2_p1_y: null,
  line2_p2_x: null,
  line2_p2_y: null,
  inside_direction: null,
  confidence: null,
  iou: null,
  frame_skip: 0,
  stream_fps: 12,
};

function toInput(camera: Camera): CameraInput {
  const { id: _id, created_at: _created, ...rest } = camera;
  return rest;
}

const DIRECTIONS: InsideDirection[] = ["UP", "DOWN", "LEFT", "RIGHT"];

export function Cameras() {
  const { t } = useLanguage();
  const { isAdmin } = useAuth();
  const cameras = useCameras();
  const { create, update, remove } = useCameraMutations();
  const [editing, setEditing] = useState<{ id: number | null; input: CameraInput } | null>(null);

  const list = cameras.data ?? [];

  const save = async () => {
    if (!editing) return;
    if (editing.id === null) await create.mutateAsync(editing.input);
    else await update.mutateAsync({ id: editing.id, input: editing.input });
    setEditing(null);
  };

  return (
    <main className="page">
      <div className="page-head">
        <span className="section-title">{t.cameras}</span>
        {isAdmin && (
          <button
            className="btn primary"
            onClick={() => setEditing({ id: null, input: { ...EMPTY } })}
          >
            <Icon name="plus" size={16} />
            {t.addCamera}
          </button>
        )}
      </div>

      <div className="card panel">
        {list.length === 0 ? (
          <div className="empty">
            <Icon name="camera" />
            <span>{t.noCameras}</span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t.name}</th>
                  <th>{t.source}</th>
                  <th>{t.insideDirection}</th>
                  <th>{t.activeToggle}</th>
                  {isAdmin && <th aria-label="actions" />}
                </tr>
              </thead>
              <tbody>
                {list.map((camera) => (
                  <tr key={camera.id}>
                    <td>{camera.name}</td>
                    <td style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {camera.source}
                    </td>
                    <td>{camera.inside_direction ?? "—"}</td>
                    <td>{camera.is_active ? "✓" : "—"}</td>
                    {isAdmin && (
                      <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                        <button
                          className="btn sm ghost"
                          onClick={() => setEditing({ id: camera.id, input: toInput(camera) })}
                        >
                          {t.edit}
                        </button>
                        <button
                          className="btn sm danger"
                          onClick={() => {
                            if (window.confirm(t.deleteCameraQ)) remove.mutate(camera.id);
                          }}
                        >
                          {t.delete}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <div className="drawer-scrim" onClick={() => setEditing(null)}>
          <div className="card drawer" onClick={(e) => e.stopPropagation()}>
            <div className="panel-head">
              <h3>{editing.id === null ? t.addCamera : t.editCamera}</h3>
              <button
                className="btn sm ghost"
                aria-label={t.close}
                onClick={() => setEditing(null)}
              >
                <Icon name="x" size={16} />
              </button>
            </div>

            <div className="form-grid">
              <Text
                label={t.name}
                value={editing.input.name}
                onChange={(v) => setEditing({ ...editing, input: { ...editing.input, name: v } })}
              />
              <div className="field">
                <label>{t.source}</label>
                <input
                  className="input"
                  value={editing.input.source}
                  onChange={(e) =>
                    setEditing({ ...editing, input: { ...editing.input, source: e.target.value } })
                  }
                />
                <span className="hint">{t.sourceHint}</span>
              </div>
              <Text
                label={t.location}
                value={editing.input.location}
                onChange={(v) =>
                  setEditing({ ...editing, input: { ...editing.input, location: v } })
                }
              />
              <LineEditor
                value={editing.input}
                onChange={(next) =>
                  setEditing({ ...editing, input: { ...editing.input, ...next } })
                }
              />
              <div className="form-row">
                <NumPair
                  label={t.lineStart}
                  x={editing.input.line_p1_x}
                  y={editing.input.line_p1_y}
                  onChange={(x, y) =>
                    setEditing({
                      ...editing,
                      input: { ...editing.input, line_p1_x: x, line_p1_y: y },
                    })
                  }
                />
                <NumPair
                  label={t.lineEnd}
                  x={editing.input.line_p2_x}
                  y={editing.input.line_p2_y}
                  onChange={(x, y) =>
                    setEditing({
                      ...editing,
                      input: { ...editing.input, line_p2_x: x, line_p2_y: y },
                    })
                  }
                />
              </div>
              <div className="form-row">
                <NumPair
                  label={t.line2Start}
                  x={editing.input.line2_p1_x}
                  y={editing.input.line2_p1_y}
                  onChange={(x, y) =>
                    setEditing({
                      ...editing,
                      input: { ...editing.input, line2_p1_x: x, line2_p1_y: y },
                    })
                  }
                />
                <NumPair
                  label={t.line2End}
                  x={editing.input.line2_p2_x}
                  y={editing.input.line2_p2_y}
                  onChange={(x, y) =>
                    setEditing({
                      ...editing,
                      input: { ...editing.input, line2_p2_x: x, line2_p2_y: y },
                    })
                  }
                />
              </div>
              <span className="hint">{t.dualLineHint}</span>
              <div className="field">
                <label>{t.insideDirection}</label>
                <select
                  className="select"
                  value={editing.input.inside_direction ?? ""}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      input: {
                        ...editing.input,
                        inside_direction: (e.target.value || null) as InsideDirection | null,
                      },
                    })
                  }
                >
                  <option value="">{t.globalDefault}</option>
                  {DIRECTIONS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <NumField
                  label={t.confidenceThreshold}
                  value={editing.input.confidence}
                  step={0.05}
                  onChange={(v) =>
                    setEditing({ ...editing, input: { ...editing.input, confidence: v } })
                  }
                />
                <NumField
                  label={t.iouThreshold}
                  value={editing.input.iou}
                  step={0.05}
                  onChange={(v) => setEditing({ ...editing, input: { ...editing.input, iou: v } })}
                />
              </div>
              <div className="form-row">
                <NumField
                  label={t.frameSkip}
                  value={editing.input.frame_skip}
                  step={1}
                  onChange={(v) =>
                    setEditing({ ...editing, input: { ...editing.input, frame_skip: v ?? 0 } })
                  }
                />
                <NumField
                  label={t.streamFps}
                  value={editing.input.stream_fps}
                  step={1}
                  onChange={(v) =>
                    setEditing({ ...editing, input: { ...editing.input, stream_fps: v ?? 12 } })
                  }
                />
              </div>
              <label
                style={{
                  display: "flex",
                  gap: "var(--sp-2)",
                  alignItems: "center",
                  fontSize: "var(--fs-2)",
                }}
              >
                <input
                  type="checkbox"
                  checked={editing.input.is_active}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      input: { ...editing.input, is_active: e.target.checked },
                    })
                  }
                />
                {t.activeToggle}
              </label>
            </div>

            <div className="drawer-actions">
              <button
                className="btn primary"
                disabled={!editing.input.name || create.isPending || update.isPending}
                onClick={save}
              >
                {t.save}
              </button>
              <button className="btn ghost" onClick={() => setEditing(null)}>
                {t.cancel}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function Text({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <input className="input" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function NumField({
  label,
  value,
  step,
  onChange,
}: {
  label: string;
  value: number | null;
  step: number;
  onChange: (v: number | null) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <input
        className="input"
        type="number"
        step={step}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      />
    </div>
  );
}

function NumPair({
  label,
  x,
  y,
  onChange,
}: {
  label: string;
  x: number | null;
  y: number | null;
  onChange: (x: number | null, y: number | null) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <div style={{ display: "flex", gap: "var(--sp-2)" }}>
        <input
          className="input"
          type="number"
          value={x ?? ""}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value), y)}
        />
        <input
          className="input"
          type="number"
          value={y ?? ""}
          onChange={(e) => onChange(x, e.target.value === "" ? null : Number(e.target.value))}
        />
      </div>
    </div>
  );
}
