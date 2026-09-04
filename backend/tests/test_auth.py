import pytest


@pytest.mark.asyncio
async def test_login_success_and_me(client, admin_token, auth):
    me = await client.get("/api/auth/me", headers=auth(admin_token))
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "admin" and body["role"] == "admin" and body["is_active"] is True


@pytest.mark.asyncio
async def test_login_bad_password(client, admin_token):
    resp = await client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_token_rejected(client):
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.get("/api/events")).status_code == 401


@pytest.mark.asyncio
async def test_garbage_token_rejected(client, auth):
    assert (await client.get("/api/auth/me", headers=auth("not-a-jwt"))).status_code == 401


@pytest.mark.asyncio
async def test_expired_token_rejected(client, monkeypatch, admin_token, auth):
    import jwt
    from app.core.config import get_settings
    from app.core.security import decode_token

    expired = jwt.encode({"sub": "1", "role": "admin", "exp": 1_000_000_000},
                         get_settings().secret_key, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)
    assert (await client.get("/api/auth/me", headers=auth(expired))).status_code == 401
