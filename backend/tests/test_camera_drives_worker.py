import pytest

from app.main import app


class _FakeSupervisor:
    def __init__(self):
        self.restart_calls = 0
        self.state = "running"
        self.restarts = 0
        self.last_error = None
        self.camera_status = "ONLINE"

    def request_restart(self):
        self.restart_calls += 1


@pytest.fixture
def fake_supervisor():
    supervisor = _FakeSupervisor()
    app.state.supervisor = supervisor
    yield supervisor
    app.state.supervisor = None


@pytest.mark.asyncio
async def test_put_active_camera_triggers_restart(client, admin_token, auth, clean_db, fake_supervisor):
    first = (await client.post("/api/cameras", headers=auth(admin_token),
                               json={"name": "A", "source": "x", "is_active": True})).json()
    second = (await client.post("/api/cameras", headers=auth(admin_token),
                                json={"name": "B", "source": "y", "is_active": False})).json()
    fake_supervisor.restart_calls = 0

    await client.put(f"/api/cameras/{first['id']}", headers=auth(admin_token),
                     json={"name": "A2", "source": "x", "line_p1_x": 0, "line_p1_y": 9,
                           "line_p2_x": 99, "line_p2_y": 9})
    assert fake_supervisor.restart_calls == 1

    await client.put(f"/api/cameras/{second['id']}", headers=auth(admin_token),
                     json={"name": "B2", "source": "y", "is_active": False})
    assert fake_supervisor.restart_calls == 1  # non-active camera -> no restart


@pytest.mark.asyncio
async def test_worker_endpoints(client, admin_token, auth, fake_supervisor):
    info = await client.get("/api/worker", headers=auth(admin_token))
    assert info.json()["state"] == "running"

    restart = await client.post("/api/worker/restart", headers=auth(admin_token))
    assert restart.json() == {"restarting": True} and fake_supervisor.restart_calls == 1


@pytest.mark.asyncio
async def test_worker_restart_requires_admin(client, viewer_token, auth):
    assert (await client.post("/api/worker/restart", headers=auth(viewer_token))).status_code == 403


@pytest.mark.asyncio
async def test_video_endpoint_is_gone(client):
    assert (await client.get("/api/video")).status_code == 410


async def test_selecting_camera_deactivates_previous_and_restarts(client, admin_token, auth, clean_db, fake_supervisor):
    a = auth(admin_token)
    first = (await client.post("/api/cameras", headers=a, json={"name": "A", "is_active": True})).json()
    second = (await client.post("/api/cameras", headers=a, json={"name": "B", "is_active": True})).json()
    rows = (await client.get("/api/cameras", headers=a)).json()
    assert [r["id"] for r in rows if r["is_active"]] == [second["id"]]
    assert fake_supervisor.restart_calls == 2
    await client.put(f"/api/cameras/{first['id']}", headers=a, json={"name": "A", "is_active": True})
    rows = (await client.get("/api/cameras", headers=a)).json()
    assert [r["id"] for r in rows if r["is_active"]] == [first["id"]]


async def test_camera_edit_preserves_masked_password(client, admin_token, auth, clean_db):
    from app.db.database import SessionLocal
    from app.db.models import Camera
    a = auth(admin_token)
    source = "rtsp://user:camera-password@host/live"
    row = (await client.post("/api/cameras", headers=a, json={"name": "A", "source": source})).json()
    row["name"] = "Renamed"
    assert (await client.put(f"/api/cameras/{row['id']}", headers=a, json=row)).status_code == 200
    async with SessionLocal() as db:
        assert (await db.get(Camera, row["id"])).source == source


@pytest.mark.parametrize("coords", [
    {"line_p1_x": 1},
    {"line_p1_x": 0, "line_p1_y": 0, "line_p2_x": 0, "line_p2_y": 0},
    {"line_p1_x": 0, "line_p1_y": 50, "line_p2_x": 100, "line_p2_y": 50,
     "line2_p1_x": 0, "line2_p1_y": 0, "line2_p2_x": 100, "line2_p2_y": 100},
])
async def test_bad_lines_rejected_before_worker_restart(client, admin_token, auth, clean_db, coords):
    response = await client.post("/api/cameras", headers=auth(admin_token), json={"name": "A", **coords})
    assert response.status_code == 422


async def test_camera_with_history_cannot_be_deleted(client, admin_token, auth, clean_db):
    from test_counting_integration import _prepare_camera
    from app.services.counting_service import CountingService
    from app.core.config import get_settings
    from app.vision.counter import CrossingEvent
    await _prepare_camera()
    await CountingService(get_settings())._save_event(1, "sheep", CrossingEvent(1, "IN", 1), .9)
    assert (await client.delete("/api/cameras/1", headers=auth(admin_token))).status_code == 409


async def test_detection_settings_restart_worker(client, admin_token, auth, clean_db, fake_supervisor):
    response = await client.put("/api/settings", headers=auth(admin_token), json={"default_confidence": .4})
    assert response.status_code == 200 and fake_supervisor.restart_calls == 1
