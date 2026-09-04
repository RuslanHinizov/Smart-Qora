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
                               json={"name": "A", "source": "x"})).json()
    second = (await client.post("/api/cameras", headers=auth(admin_token),
                                json={"name": "B", "source": "y"})).json()

    await client.put(f"/api/cameras/{first['id']}", headers=auth(admin_token),
                     json={"name": "A2", "source": "x", "line_p1_x": 0, "line_p1_y": 9,
                           "line_p2_x": 99, "line_p2_y": 9})
    assert fake_supervisor.restart_calls == 1

    await client.put(f"/api/cameras/{second['id']}", headers=auth(admin_token),
                     json={"name": "B2", "source": "y"})
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
