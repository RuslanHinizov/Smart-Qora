import { useCallback, useRef, useState } from "react";
import { readToken } from "../api/client";
import { useLanguage } from "../i18n/useLanguage";

export type LinePoints = {
  line_p1_x: number | null;
  line_p1_y: number | null;
  line_p2_x: number | null;
  line_p2_y: number | null;
};

const FALLBACK_W = 1920;
const FALLBACK_H = 1080;

/**
 * Click-to-place counting line over a live camera snapshot. Falls back to a
 * neutral grid when no feed is available (worker stopped / new camera). Click
 * alternately sets the start and end point; endpoints are also draggable.
 * All coordinates are stored in source-image pixels.
 */
export function LineEditor({
  value,
  onChange,
}: {
  value: LinePoints;
  onChange: (next: LinePoints) => void;
}) {
  const { t } = useLanguage();
  const boxRef = useRef<HTMLDivElement>(null);
  const [nat, setNat] = useState<{ w: number; h: number }>({ w: FALLBACK_W, h: FALLBACK_H });
  const [snapshotOk, setSnapshotOk] = useState(false);
  const [next, setNext] = useState<"p1" | "p2">("p1");
  const dragging = useRef<"p1" | "p2" | null>(null);

  const token = readToken();
  const snapshotSrc = token ? `/api/stream/snapshot?token=${encodeURIComponent(token)}` : "";

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

  const setPoint = (which: "p1" | "p2", x: number, y: number) => {
    onChange(
      which === "p1"
        ? { ...value, line_p1_x: x, line_p1_y: y }
        : { ...value, line_p2_x: x, line_p2_y: y },
    );
  };

  const onBoxClick = (event: React.MouseEvent) => {
    if (dragging.current) return;
    const { x, y } = toImageCoords(event.clientX, event.clientY);
    setPoint(next, x, y);
    setNext(next === "p1" ? "p2" : "p1");
  };

  const onMove = (event: React.MouseEvent) => {
    if (!dragging.current) return;
    const { x, y } = toImageCoords(event.clientX, event.clientY);
    setPoint(dragging.current, x, y);
  };

  const hasLine =
    value.line_p1_x !== null &&
    value.line_p1_y !== null &&
    value.line_p2_x !== null &&
    value.line_p2_y !== null;

  return (
    <div className="field">
      <label>{t.countingLine}</label>
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
          {hasLine && (
            <line
              x1={value.line_p1_x!}
              y1={value.line_p1_y!}
              x2={value.line_p2_x!}
              y2={value.line_p2_y!}
              className="le-line"
            />
          )}
          {value.line_p1_x !== null && value.line_p1_y !== null && (
            <circle
              cx={value.line_p1_x}
              cy={value.line_p1_y}
              r={Math.max(8, nat.w / 120)}
              className="le-handle"
              onMouseDown={(e) => {
                e.stopPropagation();
                dragging.current = "p1";
              }}
            />
          )}
          {value.line_p2_x !== null && value.line_p2_y !== null && (
            <circle
              cx={value.line_p2_x}
              cy={value.line_p2_y}
              r={Math.max(8, nat.w / 120)}
              className="le-handle"
              onMouseDown={(e) => {
                e.stopPropagation();
                dragging.current = "p2";
              }}
            />
          )}
        </svg>
      </div>
      <span className="hint">
        {t.lineEditorHint} — {value.line_p1_x ?? "—"},{value.line_p1_y ?? "—"} →{" "}
        {value.line_p2_x ?? "—"},{value.line_p2_y ?? "—"}
      </span>
    </div>
  );
}

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n));
}
