import { useCallback, useRef, useState } from "react";
import { readToken } from "../api/client";
import { useLanguage } from "../i18n/useLanguage";

export type LinePoints = {
  line_p1_x: number | null;
  line_p1_y: number | null;
  line_p2_x: number | null;
  line_p2_y: number | null;
  line2_p1_x?: number | null;
  line2_p1_y?: number | null;
  line2_p2_x?: number | null;
  line2_p2_y?: number | null;
};

const FALLBACK_W = 1920;
const FALLBACK_H = 1080;

type Field = keyof LinePoints;
const PTS: { xf: Field; yf: Field; line: "A" | "B" }[] = [
  { xf: "line_p1_x", yf: "line_p1_y", line: "A" },
  { xf: "line_p2_x", yf: "line_p2_y", line: "A" },
  { xf: "line2_p1_x", yf: "line2_p1_y", line: "B" },
  { xf: "line2_p2_x", yf: "line2_p2_y", line: "B" },
];

/**
 * Click-to-place counting line(s) over a live camera snapshot. Click cycles
 * through line A start/end then the optional line B start/end; endpoints are
 * draggable. Two lines = a track must cross both in order to be counted.
 * All coordinates are stored in source-image pixels.
 */
export function LineEditor({
  value,
  onChange,
}: {
  value: LinePoints;
  onChange: (next: Partial<LinePoints>) => void;
}) {
  const { t } = useLanguage();
  const boxRef = useRef<HTMLDivElement>(null);
  const [nat, setNat] = useState({ w: FALLBACK_W, h: FALLBACK_H });
  const [snapshotOk, setSnapshotOk] = useState(false);
  const [nextIdx, setNextIdx] = useState(0);
  const dragging = useRef<number | null>(null);

  const token = readToken();
  const snapshotSrc = token ? `/api/stream/snapshot?token=${encodeURIComponent(token)}` : "";

  const num = (f: Field) => (value[f] ?? null) as number | null;

  const toImageCoords = useCallback(
    (clientX: number, clientY: number) => {
      const rect = boxRef.current!.getBoundingClientRect();
      const scale = Math.min(rect.width / nat.w, rect.height / nat.h);
      const offsetX = (rect.width - nat.w * scale) / 2;
      const offsetY = (rect.height - nat.h * scale) / 2;
      const x = Math.round(clamp((clientX - rect.left - offsetX) / scale, 0, nat.w));
      const y = Math.round(clamp((clientY - rect.top - offsetY) / scale, 0, nat.h));
      return { x, y };
    },
    [nat],
  );

  const setPoint = (idx: number, x: number, y: number) => {
    const p = PTS[idx];
    onChange({ [p.xf]: x, [p.yf]: y });
  };

  const onBoxClick = (event: React.MouseEvent) => {
    if (dragging.current !== null) return;
    const { x, y } = toImageCoords(event.clientX, event.clientY);
    setPoint(nextIdx, x, y);
    setNextIdx((nextIdx + 1) % PTS.length);
  };

  const onMove = (event: React.MouseEvent) => {
    if (dragging.current === null) return;
    const { x, y } = toImageCoords(event.clientX, event.clientY);
    setPoint(dragging.current, x, y);
  };

  const clearLine2 = () => {
    onChange({ line2_p1_x: null, line2_p1_y: null, line2_p2_x: null, line2_p2_y: null });
    setNextIdx(0);
  };

  const seg = (a: number, b: number) =>
    num(PTS[a].xf) !== null &&
    num(PTS[a].yf) !== null &&
    num(PTS[b].xf) !== null &&
    num(PTS[b].yf) !== null;
  const r = Math.max(8, nat.w / 120);

  return (
    <div className="field">
      <label>
        {t.countingLine}
        {seg(2, 3) && (
          <button type="button" className="link-btn" onClick={clearLine2}>
            {t.clearSecondLine}
          </button>
        )}
      </label>
      <div
        ref={boxRef}
        className="line-editor"
        onClick={onBoxClick}
        onMouseMove={onMove}
        onMouseUp={() => (dragging.current = null)}
        onMouseLeave={() => (dragging.current = null)}
      >
        {snapshotSrc && (
          <img
            src={snapshotSrc}
            alt=""
            onLoad={(e) => {
              const img = e.currentTarget;
              if (img.naturalWidth > 1 && img.naturalHeight > 1) {
                setNat({ w: img.naturalWidth, h: img.naturalHeight });
                setSnapshotOk(true);
              }
            }}
            onError={() => setSnapshotOk(false)}
          />
        )}
        {!snapshotOk && <div className="line-editor-grid" />}
        <svg
          className="line-editor-svg"
          viewBox={`0 0 ${nat.w} ${nat.h}`}
          preserveAspectRatio="xMidYMid meet"
        >
          {seg(0, 1) && (
            <line
              x1={num(PTS[0].xf)!}
              y1={num(PTS[0].yf)!}
              x2={num(PTS[1].xf)!}
              y2={num(PTS[1].yf)!}
              className="le-line"
            />
          )}
          {seg(2, 3) && (
            <line
              x1={num(PTS[2].xf)!}
              y1={num(PTS[2].yf)!}
              x2={num(PTS[3].xf)!}
              y2={num(PTS[3].yf)!}
              className="le-line le-line-b"
            />
          )}
          {PTS.map((p, idx) =>
            num(p.xf) !== null && num(p.yf) !== null ? (
              <circle
                key={idx}
                cx={num(p.xf)!}
                cy={num(p.yf)!}
                r={r}
                className={p.line === "B" ? "le-handle le-handle-b" : "le-handle"}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  dragging.current = idx;
                }}
              />
            ) : null,
          )}
        </svg>
      </div>
      <span className="hint">
        {t.lineEditorHint}
        {" — A: "}
        {num("line_p1_x") ?? "—"},{num("line_p1_y") ?? "—"} → {num("line_p2_x") ?? "—"},
        {num("line_p2_y") ?? "—"}
        {seg(2, 3) && (
          <>
            {" · B: "}
            {num("line2_p1_x")},{num("line2_p1_y")} → {num("line2_p2_x")},{num("line2_p2_y")}
          </>
        )}
      </span>
    </div>
  );
}

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n));
}
