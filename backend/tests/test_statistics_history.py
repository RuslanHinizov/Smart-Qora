from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import AnimalEvent, DailyStatistic, LineDirection
from app.db.seed import ensure_default_camera
from app.services import counting_service as cs
from fakes import FakeCameraStream, FakeDetector, straight_crossing_script

NAMES = {0: "sheep", 1: "goat"}


async def _run_crossings(monkeypatch, *scripts):
    async with SessionLocal() as db:
        camera = await ensure_default_camera(db, get_settings())
        camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y = 0, 50, 100, 50
        camera.inside_direction = LineDirection.DOWN
        camera.confidence = 0.1
        await db.commit()
    for script in scripts:
        monkeypatch.setattr(cs, "CameraStream", lambda source, s=script: FakeCameraStream(source, len(s)))
        monkeypatch.setattr(cs, "LivestockDetector", lambda *a, s=script, **k: FakeDetector(s, NAMES))
        await cs.CountingService(get_settings()).run()


@pytest.mark.asyncio
async def test_rollup_matches_raw_events(monkeypatch, clean_db):
    await _run_crossings(
        monkeypatch,
        straight_crossing_script(track_id=1, cls_index=0),
        straight_crossing_script(track_id=2, cls_index=0),
        straight_crossing_script(track_id=3, cls_index=1),
    )
    async with SessionLocal() as db:
        raw = dict((await db.execute(
            select(AnimalEvent.animal_type, func.count()).group_by(AnimalEvent.animal_type))).all())
        rows = (await db.scalars(select(DailyStatistic))).all()
    rollup = {r.animal_type: r.total_in for r in rows}
    assert raw == {"sheep": 2, "goat": 1}
    assert rollup == raw


@pytest.mark.asyncio
async def test_history_endpoint_shape(client, admin_token, auth, monkeypatch, clean_db):
    await _run_crossings(monkeypatch, straight_crossing_script(track_id=9, cls_index=0))
    today = date.today().isoformat()
    resp = await client.get(f"/api/statistics/history?from={today}&to={today}", headers=auth(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body and body[0]["animal_type"] == "sheep"
    assert body[0]["total_in"] == 1 and body[0]["net"] == 1


@pytest.mark.asyncio
async def test_today_reads_rollup_and_herd_state(client, admin_token, auth, monkeypatch, clean_db):
    await _run_crossings(monkeypatch, straight_crossing_script(track_id=5, cls_index=0))
    resp = await client.get("/api/statistics/today", headers=auth(admin_token))
    assert resp.json() == {"total_in": 1, "total_out": 0, "current": 1}


@pytest.mark.asyncio
async def test_history_requires_from(client, admin_token, auth):
    assert (await client.get("/api/statistics/history", headers=auth(admin_token))).status_code == 422


@pytest.mark.asyncio
async def test_history_group_week_and_month_aggregate(client, admin_token, auth, clean_db):
    from datetime import date, timedelta

    from app.db.database import SessionLocal
    from app.db.models import DailyStatistic

    d1 = date(2026, 8, 3)   # Monday
    async with SessionLocal() as db:
        db.add_all([
            DailyStatistic(date=d1, animal_type="sheep", total_in=2, total_out=0, current_count=2),
            DailyStatistic(date=d1 + timedelta(days=2), animal_type="sheep", total_in=3, total_out=1, current_count=2),
            DailyStatistic(date=d1 + timedelta(days=40), animal_type="sheep", total_in=5, total_out=0, current_count=5),
        ])
        await db.commit()

    a = auth(admin_token)
    week = (await client.get("/api/statistics/history",
                             params={"from": "2026-08-01", "to": "2026-10-01", "group": "week"}, headers=a)).json()
    assert {"date": "2026-08-03", "animal_type": "sheep", "total_in": 5, "total_out": 1, "net": 4} in week

    month = (await client.get("/api/statistics/history",
                              params={"from": "2026-08-01", "to": "2026-10-01", "group": "month"}, headers=a)).json()
    by_month = {row["date"]: row for row in month}
    assert by_month["2026-08-01"]["total_in"] == 5
    assert by_month["2026-09-01"]["total_in"] == 5


@pytest.mark.asyncio
async def test_ws_initial_state_payload(monkeypatch, clean_db):
    from app.main import _initial_state, app

    empty = await _initial_state(app)
    assert empty == {"type": "statistics", "in": 0, "out": 0, "current": 0, "camera": "OFFLINE", "ai": "IDLE"}

    await _run_crossings(monkeypatch, straight_crossing_script(track_id=1, cls_index=0))
    after = await _initial_state(app)
    assert after["in"] == 1 and after["current"] == 1
