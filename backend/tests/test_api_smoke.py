import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200 and response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_status_requires_auth(client):
    assert (await client.get("/api/status")).status_code == 401


@pytest.mark.asyncio
async def test_status_and_ready(client, admin_token, auth):
    status = await client.get("/api/status", headers=auth(admin_token))
    assert status.status_code == 200
    body = status.json()
    assert body["camera"] == "OFFLINE" and body["ai"] == "IDLE"
    assert set(body["languages"]) == {"ru", "kk", "en", "tr"}

    ready = await client.get("/api/ready")
    assert ready.status_code == 200 and ready.json()["ready"] is True


@pytest.mark.asyncio
async def test_camera_crud_roundtrip(client, clean_db, admin_token, auth):
    created = await client.post("/api/cameras", headers=auth(admin_token), json={
        "name": "Gate A", "source": "rtsp://user:pw@10.0.0.5/stream", "inside_direction": "DOWN",
        "line_p1_x": 0, "line_p1_y": 100, "line_p2_x": 640, "line_p2_y": 100,
    })
    assert created.status_code == 201, created.text
    camera = created.json()
    assert camera["source"] == "rtsp://user:***@10.0.0.5/stream"  # masked
    assert camera["inside_direction"] == "DOWN"

    listed = await client.get("/api/cameras", headers=auth(admin_token))
    assert listed.status_code == 200 and len(listed.json()) == 1

    updated = await client.put(f"/api/cameras/{camera['id']}", headers=auth(admin_token),
                               json={"name": "Gate B", "source": "rtsp://user:pw@10.0.0.5/stream"})
    assert updated.status_code == 200 and updated.json()["name"] == "Gate B"

    deleted = await client.delete(f"/api/cameras/{camera['id']}", headers=auth(admin_token))
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_events_and_statistics_empty(client, clean_db, admin_token, auth):
    events = await client.get("/api/events", headers=auth(admin_token))
    assert events.status_code == 200 and events.json() == []

    stats = await client.get("/api/statistics/today", headers=auth(admin_token))
    assert stats.status_code == 200
    assert stats.json() == {"total_in": 0, "total_out": 0, "current": 0}
