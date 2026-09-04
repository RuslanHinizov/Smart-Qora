from dataclasses import dataclass
from math import hypot
from time import monotonic


Point = tuple[int, int]
Rect = tuple[Point, Point]


@dataclass(frozen=True)
class CrossingEvent:
    tracking_id: int
    direction: str
    sequence: int


@dataclass
class TrackState:
    stable_side: int
    last_seen: float
    last_counted: float = -1e9
    seen: int = 1              # how many updates this track has had
    in_zone: bool = False      # has its centre ever been inside the entry zone


def _norm_rect(rect: Rect) -> tuple[int, int, int, int]:
    (ax, ay), (bx, by) = rect
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)


class LineCrossingCounter:
    """Counts a track once its centre moves from one line side to the other.

    Robustness gates (both optional):
    - ``min_track_updates`` — ignore a crossing until the track has been seen this
      many times, so a 2-3 frame detector fragment straddling the line is not counted.
    - ``entry_zone`` — a rectangle the track's centre must have been inside at some
      point before a crossing counts (filters edge-of-frame flicker / teleporting IDs).
    A gated crossing does not consume the track's side, so it re-fires as soon as the
    gate passes.
    """

    def __init__(self, p1: Point, p2: Point, inside_direction: str = "DOWN", dead_zone: float = 6.0,
                 cooldown_seconds: float = 2.0, track_ttl_seconds: float = 30.0,
                 min_track_updates: int = 0, entry_zone: Rect | None = None):
        if p1 == p2:
            raise ValueError("Counting line endpoints must differ")
        self.p1, self.p2 = p1, p2
        self.inside_direction = inside_direction
        self.dead_zone = dead_zone
        self.cooldown_seconds = cooldown_seconds
        self.track_ttl_seconds = track_ttl_seconds
        self.min_track_updates = max(0, min_track_updates)
        self.entry_zone = _norm_rect(entry_zone) if entry_zone else None
        self.tracks: dict[int, TrackState] = {}
        self.sequences: dict[tuple[int, str], int] = {}

    def _signed_distance(self, point: Point) -> float:
        x, y = point; x1, y1 = self.p1; x2, y2 = self.p2
        return ((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) / hypot(x2 - x1, y2 - y1)

    def _side(self, point: Point) -> int:
        distance = self._signed_distance(point)
        return 0 if abs(distance) <= self.dead_zone else (1 if distance > 0 else -1)

    def _is_inside_side(self, side: int) -> bool:
        dx = self.p2[0] - self.p1[0]; dy = self.p2[1] - self.p1[1]
        probe = {"DOWN": (0, 1), "UP": (0, -1), "RIGHT": (1, 0), "LEFT": (-1, 0)}[self.inside_direction]
        desired = 1 if dx * probe[1] - dy * probe[0] > 0 else -1
        return side == desired

    def _in_entry_zone(self, point: Point) -> bool:
        x, y = point; x1, y1, x2, y2 = self.entry_zone
        return x1 <= x <= x2 and y1 <= y <= y2

    def update(self, tracking_id: int, center: Point, now: float | None = None) -> CrossingEvent | None:
        now = monotonic() if now is None else now
        side = self._side(center)
        state = self.tracks.get(tracking_id)
        if state is None:
            if side:
                state = self.tracks[tracking_id] = TrackState(side, now)
                if self.entry_zone is not None:
                    state.in_zone = self._in_entry_zone(center)
            return None
        state.last_seen = now
        state.seen += 1
        if self.entry_zone is not None and not state.in_zone and self._in_entry_zone(center):
            state.in_zone = True
        if side == 0 or side == state.stable_side:
            return None
        old_inside = self._is_inside_side(state.stable_side)
        new_inside = self._is_inside_side(side)
        if state.seen < self.min_track_updates:
            return None                                   # too new — keep side, retry later
        if self.entry_zone is not None and not state.in_zone:
            return None                                   # never registered in the entry zone
        state.stable_side = side
        if old_inside == new_inside or now - state.last_counted < self.cooldown_seconds:
            return None
        state.last_counted = now
        direction = "IN" if new_inside else "OUT"
        key = (tracking_id, direction)
        sequence = self.sequences[key] = self.sequences.get(key, 0) + 1
        return CrossingEvent(tracking_id, direction, sequence)

    def prune(self, now: float | None = None) -> None:
        now = monotonic() if now is None else now
        self.tracks = {key: value for key, value in self.tracks.items() if now - value.last_seen <= self.track_ttl_seconds}
