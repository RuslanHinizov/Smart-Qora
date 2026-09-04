import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import AnimalEvent, DailyStatistic, HerdState, LineDirection
from app.db.seed import ensure_default_camera
from app.services import counting_service as cs
from fakes import FakeCameraStream, FakeDetector, straight_crossing_script

NAMES = {0: "sheep", 1: "cattle"}


async def _prepare_camera():
    async with SessionLocal() as db:
        camera = await ensure_default_camera(db, get_settings())
        camera.source = "fake"
        camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y = 0, 50, 100, 50
        camera.inside_direction = LineDirection.DOWN
        camera.confidence = 0.1
        camera.frame_skip = 0
        await db.commit()


def _install_fakes(monkeypatch, script):
    monkeypatch.setattr(cs, "CameraStream", lambda source: FakeCameraStream(source, len(script)))
    monkeypatch.setattr(cs, "LivestockDetector", lambda *args, **kwargs: FakeDetector(script, NAMES))


@pytest.mark.asyncio
async def test_single_crossing_persists_and_updates_rollups(monkeypatch, clean_db):
    await _prepare_camera()
    _install_fakes(monkeypatch, straight_crossing_script(track_id=1, cls_index=0))

    await cs.CountingService(get_settings()).run()

    async with SessionLocal() as db:
        events = (await db.scalars(select(AnimalEvent))).all()
        assert len(events) == 1
        assert events[0].direction.value == "IN"
        assert events[0].animal_type == "sheep"
        assert events[0].crossing_sequence == 1

        daily = (await db.scalars(select(DailyStatistic))).all()
        assert len(daily) == 1 and daily[0].total_in == 1 and daily[0].total_out == 0

        current = await db.scalar(select(HerdState.current_inside).where(HerdState.id == 1))
        assert current == 1


@pytest.mark.asyncio
async def test_video_loop_replays_without_inflating_counts(monkeypatch, clean_db, tmp_path):
    import asyncio

    from fakes import FakeCameraStream

    video = tmp_path / "loop.mp4"
    video.touch()
    async with SessionLocal() as db:
        camera = await ensure_default_camera(db, get_settings())
        camera.source = str(video)  # a real file -> loop_file path
        camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y = 0, 50, 100, 50
        camera.inside_direction = LineDirection.DOWN
        camera.confidence = 0.1
        await db.commit()

    script = straight_crossing_script(track_id=1, cls_index=0)
    FakeCameraStream.instances = 0
    monkeypatch.setattr(cs, "CameraStream", lambda source: FakeCameraStream(source, len(script)))
    monkeypatch.setattr(cs, "LivestockDetector", lambda *a, **k: FakeDetector(script, NAMES))

    service = cs.CountingService(get_settings())
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)
    service.stop()
    await task

    assert FakeCameraStream.instances >= 2  # the file looped
    async with SessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(AnimalEvent))
        assert count == 1  # dedup held across loops


@pytest.mark.asyncio
async def test_replaying_the_same_footage_is_idempotent(monkeypatch, clean_db):
    await _prepare_camera()
    script = straight_crossing_script(track_id=7, cls_index=1)

    _install_fakes(monkeypatch, script)
    await cs.CountingService(get_settings()).run()
    _install_fakes(monkeypatch, script)  # fresh counter → crossing_sequence restarts at 1
    await cs.CountingService(get_settings()).run()

    async with SessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(AnimalEvent))
        assert count == 1
        assert (await db.scalar(select(AnimalEvent.animal_type))) == "cattle"
        current = await db.scalar(select(HerdState.current_inside).where(HerdState.id == 1))
        assert current == 1
