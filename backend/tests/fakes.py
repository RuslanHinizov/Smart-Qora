"""Lightweight stand-ins for the Ultralytics result and the camera stream."""
import numpy as np


class _Scalar:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class _Coords:
    def __init__(self, values):
        self._values = list(values)

    def tolist(self):
        return self._values


class FakeBox:
    def __init__(self, track_id: int, cls_index: int, xyxy, conf: float):
        self.id = _Scalar(track_id)
        self.cls = _Scalar(cls_index)
        self.conf = _Scalar(conf)
        self.xyxy = [_Coords(xyxy)]


class FakeResult:
    def __init__(self, boxes, names, frame):
        self.boxes = boxes
        self.names = names
        self._frame = frame

    def plot(self):
        return self._frame.copy()


class FakeDetector:
    """Replays a script: one list of ``(track_id, cls_index, (x1,y1,x2,y2), conf)`` per frame."""

    def __init__(self, script, names):
        self.script = list(script)
        self.names = names
        self._i = 0

    def track(self, frame):
        entries = self.script[self._i] if self._i < len(self.script) else []
        self._i += 1
        boxes = [FakeBox(*entry) for entry in entries]
        return FakeResult(boxes or None, self.names, frame)

    def reset_tracker(self) -> None:
        self._i = 0  # replay the script from the start on each video loop


class FakeCameraStream:
    instances = 0

    def __init__(self, source, frame_count: int):
        FakeCameraStream.instances += 1
        self.source = source
        self.status = "ONLINE"
        self._frame_count = frame_count

    async def frames(self):
        for _ in range(self._frame_count):
            yield np.zeros((120, 160, 3), dtype=np.uint8)

    def close(self):
        self.status = "OFFLINE"


def straight_crossing_script(track_id: int = 1, cls_index: int = 0, conf: float = 0.9):
    """3 frames well above the y=50 line, then 6 well below -> one IN crossing (INSIDE=DOWN)."""
    above = (track_id, cls_index, (40, 10, 60, 30), conf)   # center (50, 20)
    below = (track_id, cls_index, (40, 70, 60, 90), conf)   # center (50, 80)
    return [[above]] * 3 + [[below]] * 6
