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


def test_min_track_updates_ignores_short_fragments():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=1, min_track_updates=4)
    # a fragment that appears already crossing and only lives 2 frames -> not counted
    assert counter.update(1, (50, 40), 0) is None   # seen=1
    assert counter.update(1, (50, 60), 1) is None   # seen=2, crossing gated
    # a real track seen long enough on the origin side still counts
    for t in range(5):
        counter.update(2, (50, 40), t)               # seen 1..5 on the DOWN-outside side
    assert counter.update(2, (50, 60), 5).direction == "IN"


def test_gated_fragment_still_counts_once_it_matures():
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=1, min_track_updates=3)
    assert counter.update(1, (50, 40), 0) is None    # seen=1
    assert counter.update(1, (50, 60), 1) is None    # seen=2, gated (side NOT consumed)
    ev = counter.update(1, (50, 62), 2)              # seen=3, now eligible, still on new side
    assert ev and ev.direction == "IN"


def test_entry_zone_requires_prior_registration():
    # DOWN is "inside"; animals enter from the far-outside strip (y 0..20)
    counter = LineCrossingCounter((0, 50), (100, 50), "DOWN", dead_zone=1,
                                  entry_zone=((0, 0), (100, 20)))
    # track A appears between the zone and the line -> its crossing is ignored
    counter.update(1, (50, 40), 0)
    assert counter.update(1, (50, 60), 1) is None
    # track B passes through the entry zone first -> counted
    counter.update(2, (50, 10), 0)                   # inside entry zone
    counter.update(2, (50, 40), 1)
    assert counter.update(2, (50, 60), 2).direction == "IN"
