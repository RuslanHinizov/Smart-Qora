"""Render an inference result onto a frame: boxes + track IDs (via Ultralytics
``result.plot()``), the counting line, and the running IN / OUT / INSIDE tallies.
"""
import logging

import cv2

logger = logging.getLogger(__name__)

Point = tuple[int, int]
_LINE_COLOR = (0, 210, 255)  # BGR amber
_FONT = cv2.FONT_HERSHEY_SIMPLEX


def annotate_jpeg(frame, result, line: tuple[Point, Point], tally: str, quality: int = 70) -> bytes:
    try:
        canvas = result.plot()
    except Exception:  # noqa: BLE001 - never let a draw failure kill the worker
        logger.exception("result_plot_failed")
        canvas = frame.copy()

    (x1, y1), (x2, y2) = line
    cv2.line(canvas, (x1, y1), (x2, y2), _LINE_COLOR, 2, cv2.LINE_AA)
    cv2.putText(canvas, tally, (14, 34), _FONT, 0.8, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(canvas, tally, (14, 34), _FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    ok, buffer = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return buffer.tobytes()
