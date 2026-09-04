import pytest

CAMERA = {"name": "X", "source": "videos/test.mp4"}


@pytest.mark.asyncio
async def test_viewer_can_read(client, viewer_token, auth, clean_db):
    assert (await client.get("/api/events", headers=auth(viewer_token))).status_code == 200
    assert (await client.get("/api/cameras", headers=auth(viewer_token))).status_code == 200
    assert (await client.get("/api/settings", headers=auth(viewer_token))).status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_write_cameras(client, viewer_token, auth, clean_db):
    assert (await client.post("/api/cameras", headers=auth(viewer_token), json=CAMERA)).status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_write_settings_or_calibrate(client, viewer_token, auth):
    assert (await client.put("/api/settings", headers=auth(viewer_token),
                             json={"default_language": "en"})).status_code == 403
    assert (await client.post("/api/herd/calibrate", headers=auth(viewer_token),
                              json={"current_inside": 10})).status_code == 403


@pytest.mark.asyncio
async def test_admin_can_write(client, admin_token, auth, clean_db):
    assert (await client.post("/api/cameras", headers=auth(admin_token), json=CAMERA)).status_code == 201
    assert (await client.put("/api/settings", headers=auth(admin_token),
                             json={"default_language": "tr"})).status_code == 200
    assert (await client.post("/api/herd/calibrate", headers=auth(admin_token),
                              json={"current_inside": 42})).json()["current_inside"] == 42


@pytest.mark.asyncio
async def test_anon_blocked_everywhere(client):
    for path in ("/api/events", "/api/statistics/today", "/api/cameras", "/api/status", "/api/settings"):
        assert (await client.get(path)).status_code == 401, path
