from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.db.database import SessionLocal
from app.db.models import AnimalEvent, Camera, Direction

BASE = datetime(2026, 9, 1, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def seeded(clean_db):
    async with SessionLocal() as db:
        a, b = Camera(name="A", source="x"), Camera(name="B", source="y")
        db.add_all([a, b])
        await db.flush()
        db.add_all([
            AnimalEvent(camera_id=a.id, animal_type="sheep", tracking_id=1, crossing_sequence=1,
                        direction=Direction.IN, confidence=0.9, timestamp=BASE),
            AnimalEvent(camera_id=a.id, animal_type="sheep", tracking_id=2, crossing_sequence=1,
                        direction=Direction.OUT, confidence=0.8, timestamp=BASE + timedelta(days=1)),
            AnimalEvent(camera_id=a.id, animal_type="goat", tracking_id=3, crossing_sequence=1,
                        direction=Direction.IN, confidence=0.7, timestamp=BASE + timedelta(days=2)),
            AnimalEvent(camera_id=b.id, animal_type="sheep", tracking_id=4, crossing_sequence=1,
                        direction=Direction.IN, confidence=0.6, timestamp=BASE + timedelta(days=3)),
        ])
        await db.commit()
        return {"a": a.id, "b": b.id}


@pytest.mark.asyncio
async def test_total_count_header_and_default_list(client, admin_token, auth, seeded):
    resp = await client.get("/api/events", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.headers["x-total-count"] == "4"
    assert len(resp.json()) == 4
    assert resp.json()[0]["timestamp"] > resp.json()[-1]["timestamp"]  # newest first


@pytest.mark.asyncio
async def test_filters(client, admin_token, auth, seeded):
    a = auth(admin_token)
    assert (await client.get("/api/events", params={"direction": "IN"}, headers=a)).headers["x-total-count"] == "3"
    assert (await client.get("/api/events", params={"animal_type": "goat"}, headers=a)).headers["x-total-count"] == "1"
    assert (await client.get("/api/events", params={"camera_id": seeded["b"]}, headers=a)).headers["x-total-count"] == "1"
    cutoff = (BASE + timedelta(days=2)).isoformat()
    assert (await client.get("/api/events", params={"from": cutoff}, headers=a)).headers["x-total-count"] == "2"


@pytest.mark.asyncio
async def test_pagination(client, admin_token, auth, seeded):
    a = auth(admin_token)
    page1 = await client.get("/api/events?limit=2&offset=0", headers=a)
    page2 = await client.get("/api/events?limit=2&offset=2", headers=a)
    assert page1.headers["x-total-count"] == "4" and len(page1.json()) == 2
    assert len(page2.json()) == 2
    ids = {e["id"] for e in page1.json()} | {e["id"] for e in page2.json()}
    assert len(ids) == 4


@pytest.mark.asyncio
async def test_bad_direction_rejected(client, admin_token, auth, seeded):
    assert (await client.get("/api/events?direction=SIDEWAYS", headers=auth(admin_token))).status_code == 422
