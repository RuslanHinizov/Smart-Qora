from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, func

from app.core.calendar import day_bounds, site_day
from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import AnimalEvent, AppSettings, Camera, DailyStatistic, RecordingProgress
from app.services import counting_service as cs
from app.services.statistics_service import statistics
from app.vision.counter import CrossingEvent
from test_counting_integration import _prepare_camera, _install_fakes
from fakes import straight_crossing_script, FakeDetector


async def test_same_session_retries_are_idempotent(clean_db):
    await _prepare_camera()
    service = cs.CountingService(get_settings())
    crossing = CrossingEvent(7, "IN", 1)
    await service._save_event(7, "sheep", crossing, .9)
    await service._save_event(7, "sheep", crossing, .9)
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(AnimalEvent)) == 1


async def test_completed_file_does_not_recount_on_restart_or_id_change(monkeypatch, clean_db, tmp_path):
    await _prepare_camera()
    clip = tmp_path / "sheep.mp4"
    clip.write_bytes(b"recording")
    async with SessionLocal() as db:
        camera = await db.get(Camera, 1)
        camera.source = str(clip)
        await db.commit()
    settings = get_settings().model_copy(update={"video_loop": False})
    for tracking_id in (1, 300):
        _install_fakes(monkeypatch, straight_crossing_script(tracking_id))
        await cs.CountingService(settings).run()
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(AnimalEvent)) == 1
        assert (await db.scalar(select(RecordingProgress))).completed


async def test_interrupted_file_replays_prefix_without_recounting(monkeypatch, clean_db, tmp_path):
    await _prepare_camera()
    clip = tmp_path / "resume.mp4"
    clip.write_bytes(b"resume")
    async with SessionLocal() as db:
        camera = await db.get(Camera, 1)
        camera.source = str(clip)
        db.add(RecordingProgress(camera_id=1, fingerprint=cs.recording_fingerprint(clip), last_frame=9))
        await db.commit()
    _install_fakes(monkeypatch, straight_crossing_script(1) + straight_crossing_script(2))
    await cs.CountingService(get_settings().model_copy(update={"video_loop": False})).run()
    async with SessionLocal() as db:
        assert (await db.scalars(select(AnimalEvent.tracking_id))).all() == [2]


async def test_live_message_contains_today_not_all_time(monkeypatch, clean_db):
    await _prepare_camera()
    async with SessionLocal() as db:
        db.add(DailyStatistic(date=site_day()-timedelta(days=1), animal_type="sheep", total_in=100, total_out=0, current_count=100))
        await db.commit()
    broadcast = AsyncMock()
    monkeypatch.setattr(cs.websockets, "broadcast", broadcast)
    _install_fakes(monkeypatch, straight_crossing_script())
    await cs.CountingService(get_settings()).run()
    messages = [c.args[0] for c in broadcast.call_args_list if c.args[0]["type"] == "statistics"]
    assert messages[-1]["in"] == 1


async def test_zero_skip_overrides_defaults_and_detection_defaults_apply(monkeypatch, clean_db):
    await _prepare_camera()
    async with SessionLocal() as db:
        camera = await db.get(Camera, 1)
        camera.confidence = None
        row = await db.get(AppSettings, 1)
        row.default_confidence = .42
        row.default_frame_skip = 100
        await db.commit()
    script = straight_crossing_script()
    _install_fakes(monkeypatch, script)
    captured = []
    def detector(*args):
        captured.append(args)
        return FakeDetector(script, {0: "sheep"})
    monkeypatch.setattr(cs, "LivestockDetector", detector)
    await cs.CountingService(get_settings().model_copy(update={"frame_skip": 99})).run()
    assert captured[0][2] == .42
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(AnimalEvent)) == 1


async def test_no_active_camera_does_not_start_detector(monkeypatch, clean_db):
    await _prepare_camera()
    async with SessionLocal() as db:
        (await db.get(Camera, 1)).is_active = False
        await db.commit()
    monkeypatch.setattr(cs, "LivestockDetector", lambda *a: pytest.fail("inactive camera started"))
    await cs.CountingService(get_settings()).run()


async def test_invalid_persisted_second_line_falls_back_to_single(monkeypatch, clean_db):
    await _prepare_camera()
    async with SessionLocal() as db:
        camera = await db.get(Camera, 1)
        camera.line2_p1_x = camera.line2_p2_x = 10
        camera.line2_p1_y = camera.line2_p2_y = 20
        await db.commit()
    _install_fakes(monkeypatch, straight_crossing_script())
    service = cs.CountingService(get_settings())
    await service.run()
    assert service.line2 is None
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(AnimalEvent)) == 1


def test_site_day_uses_local_midnight(monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Almaty")
    before = datetime(2026, 9, 6, 18, 59, 59, tzinfo=timezone.utc)
    after = before + timedelta(seconds=1)
    assert site_day(before) == date(2026, 9, 6)
    assert site_day(after) == date(2026, 9, 7)
    assert day_bounds(date(2026, 9, 7))[0] == after


async def test_daily_events_respect_local_midnight(monkeypatch, clean_db):
    monkeypatch.setenv("TZ", "Asia/Almaty")
    await _prepare_camera()
    async with SessionLocal() as db:
        for track, hour in ((1, 18), (2, 19)):
            db.add(AnimalEvent(camera_id=1, animal_type="sheep", tracking_id=track, direction="IN", confidence=.9,
                               timestamp=datetime(2026, 9, 6, hour, tzinfo=timezone.utc)))
        await db.commit()
        assert (await statistics(db, date(2026, 9, 7)))["total_in"] == 1
