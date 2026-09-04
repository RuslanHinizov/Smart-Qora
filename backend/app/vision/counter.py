from dataclasses import dataclass
from math import hypot
from time import monotonic


Point = tuple[int, int]
Line = tuple[Point, Point]
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
    in_zone: bool = False      # (single-line) has its centre ever been inside the entry zone
    # dual-line
    zone: int = 0              # -1 = before A, 0 = in the gate, +1 = past B
    armed: str = ""            # "AB" or "BA" — the direction it is mid-crossing


def _norm_rect(rect: Rect) -> tuple[int, int, int, int]:
    (ax, ay), (bx, by) = rect
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)


def _raw_signed_distance(point: Point, line: Line) -> float:
    (x1, y1), (x2, y2) = line
    x, y = point
    return ((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) / hypot(x2 - x1, y2 - y1)


def _mid(line: Line) -> Point:
    (x1, y1), (x2, y2) = line
    return (x1 + x2) // 2, (y1 + y2) // 2


class LineCrossingCounter:
    """Counts a track when it moves across the gate.

    Single line (``line2`` unset): a crossing fires when the smoothed centre moves
    from one side of the line to the other.

    Two lines (``line2`` set): a crossing fires only when the track passes the whole
    gate in order — outside → between A and B → past the far line. Touching one line,
    hovering on it, or clipping it at an angle does not count. ``inside_direction``
    still says which far side is "inside" (→ IN) vs "outside" (→ OUT).

    Optional gates (either mode): ``min_track_updates`` ignores a crossing until the
    track has that many hits; ``entry_zone`` requires the centre to have visited a
    rectangle first.
    """

    PROBE = {"DOWN": (0, 1), "UP": (0, -1), "RIGHT": (1, 0), "LEFT": (-1, 0)}

    def __init__(self, p1: Point, p2: Point, inside_direction: str = "DOWN", dead_zone: float = 6.0,
                 cooldown_seconds: float = 2.0, track_ttl_seconds: float = 30.0,
                 min_track_updates: int = 0, entry_zone: Rect | None = None,
                 line2: Line | None = None):
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

        self.line2 = line2
        if line2 is not None:
            if line2[0] == line2[1]:
                raise ValueError("Second line endpoints must differ")
            self._setup_dual((p1, p2), line2)

    # ── single-line geometry ────────────────────────────────────────────────
    def _signed_distance(self, point: Point) -> float:
        return _raw_signed_distance(point, (self.p1, self.p2))

    def _side(self, point: Point) -> int:
        distance = self._signed_distance(point)
        return 0 if abs(distance) <= self.dead_zone else (1 if distance > 0 else -1)

    def _is_inside_side(self, side: int) -> bool:
        dx = self.p2[0] - self.p1[0]; dy = self.p2[1] - self.p1[1]
        probe = self.PROBE[self.inside_direction]
        desired = 1 if dx * probe[1] - dy * probe[0] > 0 else -1
        return side == desired

    def _in_entry_zone(self, point: Point) -> bool:
        x, y = point; x1, y1, x2, y2 = self.entry_zone
        return x1 <= x <= x2 and y1 <= y <= y2

    # ── dual-line geometry ──────────────────────────────────────────────────
    def _setup_dual(self, line_a: Line, line_b: Line) -> None:
        # orient each line's positive side to face the other line, so the strip
        # between them is where both signed distances are positive.
        self._a, self._b = line_a, line_b
        self._sa = 1.0 if _raw_signed_distance(_mid(line_b), line_a) >= 0 else -1.0
        self._sb = 1.0 if _raw_signed_distance(_mid(line_a), line_b) >= 0 else -1.0
        gate_mid = ((_mid(line_a)[0] + _mid(line_b)[0]) // 2, (_mid(line_a)[1] + _mid(line_b)[1]) // 2)
        px, py = self.PROBE[self.inside_direction]
        probe_point = (gate_mid[0] + px * 10000, gate_mid[1] + py * 10000)
        self._inside_zone = self._zone(probe_point) or 1  # -1 (past A) or +1 (past B)

    def _zone(self, point: Point) -> int:
        da = self._sa * _raw_signed_distance(point, self._a)
        db = self._sb * _raw_signed_distance(point, self._b)
        if da < -self.dead_zone:
            return -1                       # before line A (one outside)
        if db < -self.dead_zone:
            return 1                        # past line B (other outside)
        if da > self.dead_zone and db > self.dead_zone:
            return 0                        # in the gate
        return -99                          # on a line — inconclusive this frame

    # ── update ─────────────────────────────────────────────────────────────
    def update(self, tracking_id: int, center: Point, now: float | None = None) -> CrossingEvent | None:
        now = monotonic() if now is None else now
        return self._update_dual(tracking_id, center, now) if self.line2 is not None \
            else self._update_single(tracking_id, center, now)

    def _new_state(self, center: Point, now: float) -> TrackState:
        state = TrackState(self._side(center), now)
        if self.entry_zone is not None:
            state.in_zone = self._in_entry_zone(center)
        if self.line2 is not None:
            z = self._zone(center)
            state.zone = z if z != -99 else 0
        return state

    def _gates_block(self, state: TrackState, center: Point) -> bool:
        if state.seen < self.min_track_updates:
            return True
        if self.entry_zone is not None and not state.in_zone:
            return True
        return False

    def _emit(self, tracking_id: int, direction: str) -> CrossingEvent:
        key = (tracking_id, direction)
        sequence = self.sequences[key] = self.sequences.get(key, 0) + 1
        return CrossingEvent(tracking_id, direction, sequence)

    def _update_single(self, tracking_id: int, center: Point, now: float) -> CrossingEvent | None:
        state = self.tracks.get(tracking_id)
        if state is None:
            if self._side(center):
                self.tracks[tracking_id] = self._new_state(center, now)
            return None
        state.last_seen = now
        state.seen += 1
        if self.entry_zone is not None and not state.in_zone and self._in_entry_zone(center):
            state.in_zone = True
        side = self._side(center)
        if side == 0 or side == state.stable_side:
            return None
        old_inside = self._is_inside_side(state.stable_side)
        new_inside = self._is_inside_side(side)
        if self._gates_block(state, center):
            return None
        state.stable_side = side
        if old_inside == new_inside or now - state.last_counted < self.cooldown_seconds:
            return None
        state.last_counted = now
        return self._emit(tracking_id, "IN" if new_inside else "OUT")

    def _update_dual(self, tracking_id: int, center: Point, now: float) -> CrossingEvent | None:
        state = self.tracks.get(tracking_id)
        if state is None:
            self.tracks[tracking_id] = self._new_state(center, now)
            return None
        state.last_seen = now
        state.seen += 1
        if self.entry_zone is not None and not state.in_zone and self._in_entry_zone(center):
            state.in_zone = True

        z = self._zone(center)
        if z == -99 or z == state.zone:
            return None

        prev, state.zone = state.zone, z
        # arm when entering the gate from one side
        if z == 0 and prev == -1:
            state.armed = "AB"
        elif z == 0 and prev == 1:
            state.armed = "BA"
        # a completed pass: gate -> far side (or a fast side->side jump)
        crossed = ""
        if prev == 0 and z == 1 and state.armed == "AB":
            crossed = "AB"
        elif prev == 0 and z == -1 and state.armed == "BA":
            crossed = "BA"
        elif prev == -1 and z == 1:
            crossed = "AB"
        elif prev == 1 and z == -1:
            crossed = "BA"
        if not crossed:
            return None
        state.armed = ""
        if self._gates_block(state, center) or now - state.last_counted < self.cooldown_seconds:
            return None
        state.last_counted = now
        ends_zone = 1 if crossed == "AB" else -1
        return self._emit(tracking_id, "IN" if ends_zone == self._inside_zone else "OUT")

    def prune(self, now: float | None = None) -> None:
        now = monotonic() if now is None else now
        self.tracks = {key: value for key, value in self.tracks.items()
                       if now - value.last_seen <= self.track_ttl_seconds}
