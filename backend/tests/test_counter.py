import pytest

from app.vision.counter import LineCrossingCounter


def test_in_crossing():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=2)
    assert counter.update(1, (50, 40), 0) is None
    assert counter.update(1, (50, 50), 1) is None
    event = counter.update(1, (50, 60), 2)
    assert event and event.direction == "IN" and event.sequence == 1


def test_crossing_sequence_is_monotonic_per_track_and_direction():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=2, cooldown_seconds=0)
    assert counter.update(1, (50, 40), 0) is None
    assert counter.update(1, (50, 60), 1).sequence == 1
    assert counter.update(1, (50, 40), 2).sequence == 1  # first OUT
    assert counter.update(1, (50, 60), 3).sequence == 2  # second IN


def test_out_crossing():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=2)
    counter.update(7, (50, 60), 0)
    event = counter.update(7, (50, 40), 3)
    assert event and event.direction == "OUT"


def test_touching_line_is_not_crossing():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN")
    counter.update(2, (50, 40), 0)
    assert counter.update(2, (50, 50), 1) is None
    assert counter.update(2, (50, 45), 2) is None


def test_duplicate_tracking_id_cooldown():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=1, cooldown_seconds=5)
    counter.update(3, (50, 40), 0)
    assert counter.update(3, (50, 60), 1).direction == "IN"
    assert counter.update(3, (50, 40), 2) is None


def test_multiple_animals():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=1)
    for track_id in range(5): counter.update(track_id, (20, 40), 0)
    events = [counter.update(track_id, (20, 60), 3) for track_id in range(5)]
    assert len([event for event in events if event]) == 5


def test_zero_length_line_rejected():
    with pytest.raises(ValueError): LineCrossingCounter((1, 1), (1, 1))
