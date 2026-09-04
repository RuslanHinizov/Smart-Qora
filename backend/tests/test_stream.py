import asyncio

import pytest

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import LineDirection
from app.db.seed import ensure_default_camera
from app.services import counting_service as cs
from app.services.frame_bus import frame_bus
from fakes import FakeCameraStream, FakeDetector, straight_crossing_script

NAMES = {0: "sheep"}
_FAKE_JPEG = b"\xff\xd8" + b"SENTINEL" + b"\xff\xd9"


@pytest.mark.asyncio
async def test_snapshot_requires_a_token(client, reset_frame_bus):
    assert (await client.get("/api/stream/snapshot")).status_code == 401


@pytest.mark.asyncio
async def test_snapshot_accepts_query_token_and_returns_jpeg(client, admin_token, reset_frame_bus):
    reset_frame_bus.publish(_FAKE_JPEG)
    resp = await client.get(f"/api/stream/snapshot?token={admin_token}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.content == _FAKE_JPEG


@pytest.mark.asyncio
async def test_mjpeg_requires_a_token(client):
    assert (await client.get("/api/stream/mjpeg")).status_code == 401
    assert (await client.get("/api/stream/mjpeg?token=not-a-jwt")).status_code == 401


@pytest.mark.asyncio
async def test_mjpeg_generator_emits_multipart_jpeg_parts(reset_frame_bus):
    from app.api.routes.stream import _mjpeg

    reset_frame_bus.publish(_FAKE_JPEG)
    generator = _mjpeg()
    try:
        chunk = await asyncio.wait_for(generator.__anext__(), timeout=2.0)
    finally:
        await generator.aclose()

    assert chunk.startswith(b"--frame")
    assert b"Content-Type: image/jpeg" in chunk
    assert b"SENTINEL" in chunk


@pytest.mark.asyncio
async def test_worker_publishes_a_real_jpeg_only_when_subscribed(monkeypatch, clean_db, reset_frame_bus):
    async with SessionLocal() as db:
        camera = await ensure_default_camera(db, get_settings())
        camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y = 0, 50, 100, 50
        camera.inside_direction = LineDirection.DOWN
        camera.confidence = 0.1
        await db.commit()

    script = straight_crossing_script(track_id=1, cls_index=0)
    monkeypatch.setattr(cs, "CameraStream", lambda source: FakeCameraStream(source, len(script)))
    monkeypatch.setattr(cs, "LivestockDetector", lambda *a, **k: FakeDetector(script, NAMES))

    # No subscriber -> nothing published.
    await cs.CountingService(get_settings()).run()
    assert frame_bus.latest_jpeg is None

    # With a subscriber -> annotated JPEG lands on the bus.
    frame_bus.subscribe()
    monkeypatch.setattr(cs, "CameraStream", lambda source: FakeCameraStream(source, len(script)))
    monkeypatch.setattr(cs, "LivestockDetector", lambda *a, **k: FakeDetector(script, NAMES))
    await cs.CountingService(get_settings()).run()
    assert frame_bus.latest_jpeg is not None
    assert frame_bus.latest_jpeg[:2] == b"\xff\xd8"  # JPEG start-of-image
