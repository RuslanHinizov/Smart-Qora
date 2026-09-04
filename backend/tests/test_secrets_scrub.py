import pytest

RTSP = "rtsp://admin:sup3rsecret@10.9.9.9:554/h264"


@pytest.mark.asyncio
async def test_camera_source_password_never_returned(client, admin_token, auth, clean_db):
    created = await client.post("/api/cameras", headers=auth(admin_token),
                                json={"name": "Barn", "source": RTSP})
    assert created.status_code == 201
    for resp in (created, await client.get("/api/cameras", headers=auth(admin_token))):
        assert "sup3rsecret" not in resp.text
        assert ":***@10.9.9.9" in resp.text


@pytest.mark.asyncio
async def test_settings_never_returns_telegram_token(client, admin_token, auth, clean_db):
    await client.put("/api/settings", headers=auth(admin_token),
                     json={"telegram_bot_token": "123:AAA-secret", "telegram_chat_id": "42"})
    resp = await client.get("/api/settings", headers=auth(admin_token))
    assert resp.status_code == 200
    assert "AAA-secret" not in resp.text
    assert resp.json()["telegram_configured"] is True


@pytest.mark.asyncio
async def test_no_endpoint_leaks_secret_key(client, admin_token, auth, clean_db):
    from app.core.config import get_settings
    secret = get_settings().secret_key
    for path in ("/api/health", "/api/status", "/api/settings", "/api/cameras", "/api/auth/me"):
        resp = await client.get(path, headers=auth(admin_token))
        assert secret not in resp.text, path
