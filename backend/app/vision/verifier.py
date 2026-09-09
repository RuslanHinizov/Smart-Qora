"""Second-pass guard for animals that the livestock model mistakes for sheep.

The counting model is deliberately trained only on livestock.  A dog can therefore
occasionally look like a sheep to it.  The small COCO model is used only as a
negative check: when it agrees that the same box is a dog, that tracked object is
never written as a livestock crossing.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

Box = tuple[int, int, int, int]


def iou(a: Box, b: Box) -> float:
    """Intersection-over-union for two xyxy boxes."""
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    if not overlap:
        return 0.0
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    return overlap / max(area_a + area_b - overlap, 1)


class NonLivestockGuard:
    """Remember track IDs that a generic detector has confirmed as dogs."""

    def __init__(self, model_path: str, device: str, confidence: float = 0.25,
                 candidate_max_confidence: float = 0.75, overlap: float = 0.35):
        self.blocked_track_ids: set[int] = set()
        self.confidence = confidence
        self.candidate_max_confidence = candidate_max_confidence
        self.overlap = overlap
        self.model = None
        path = Path(model_path)
        if not path.is_file():
            logger.warning("non_livestock_guard_unavailable", extra={"model_path": model_path})
            return
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(path))
            self.device = device
        except Exception:  # noqa: BLE001 - counting must continue if the guard cannot start
            logger.exception("non_livestock_guard_load_failed")

    @property
    def enabled(self) -> bool:
        return self.model is not None

    def observe(self, frame, candidates: list[tuple[int, float, Box]]) -> set[int]:
        """Mark low-confidence livestock tracks that overlap a confirmed dog."""
        if self.model is None:
            return set()
        candidates = [item for item in candidates if item[1] <= self.candidate_max_confidence]
        if not candidates:
            return set()
        result = self.model(frame, verbose=False, conf=self.confidence, imgsz=1280,
                            device=self.device)[0]
        if result.boxes is None:
            return set()
        dogs = [
            tuple(int(value) for value in box.xyxy[0].tolist())
            for box in result.boxes
            if result.names[int(box.cls.item())] == "dog"
        ]
        marked = {track_id for track_id, _, box in candidates
                  if any(iou(box, dog) >= self.overlap for dog in dogs)}
        self.blocked_track_ids.update(marked)
        return marked

    def reset(self) -> None:
        self.blocked_track_ids.clear()

    def prune(self, active_track_ids: set[int]) -> None:
        self.blocked_track_ids.intersection_update(active_track_ids)
