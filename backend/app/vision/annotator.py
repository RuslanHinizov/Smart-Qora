"""Render an inference result onto a frame: thin per-track boxes + small ID tags,
the counting line, and the running IN / OUT / INSIDE tallies.

Deliberately lightweight — ``result.plot()`` draws thick boxes with filled label
blocks that hide the animals when the flock is dense.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

Point = tuple[int, int]
_LINE_COLOR = (0, 210, 255)   # BGR amber
_FALLBACK_BOX = (80, 220, 80)  # BGR green
_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _color(track_id: int | None) -> tuple[int, int, int]:
    if track_id is None:
        return _FALLBACK_BOX
    try:
        from ultralytics.utils.plotting import colors
        return colors(track_id, True)  # BGR, stable per id
    except Exception:  # noqa: BLE001
        return _FALLBACK_BOX


def annotate_jpeg(frame, result, line: tuple[Point, Point], tally: str, quality: int = 70) -> bytes:
    canvas = np.ascontiguousarray(frame).copy()
    boxes = getattr(result, "boxes", None)
    if boxes is not None:
        for box in boxes:
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            tid = int(box.id.item()) if box.id is not None else None
            colour = _color(tid)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), colour, 1, cv2.LINE_AA)
            if tid is not None:
                cv2.putText(canvas, str(tid), (x1 + 1, max(y1 - 3, 9)),
                            _FONT, 0.4, colour, 1, cv2.LINE_AA)

    (x1, y1), (x2, y2) = line
    cv2.line(canvas, (x1, y1), (x2, y2), _LINE_COLOR, 2, cv2.LINE_AA)
    cv2.putText(canvas, tally, (14, 34), _FONT, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(canvas, tally, (14, 34), _FONT, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    ok, buffer = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return buffer.tobytes()
