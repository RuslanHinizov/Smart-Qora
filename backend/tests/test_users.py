import pytest
import pytest_asyncio
from sqlalchemy import delete, update

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.db.models import Role, User

NEW = {"username": "shepherd", "password": "long-enough-pw", "role": "viewer"}


async def _only_seeded_admin():
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.username != "admin"))
        await db.execute(update(User).where(User.username == "admin").values(
            password_hash=hash_password("test-admin-pw"), is_active=True, role=Role.admin))
        await db.commit()


@pytest_asyncio.fixture
async def only_admin(admin_token):
    """Start from just the seeded admin, and put its password back afterwards."""
    await _only_seeded_admin()
    yield
    await _only_seeded_admin()


async def _login(client, username, password):
    return await client.post("/api/auth/login", data={"username": username, "password": password})


@pytest.mark.asyncio
async def test_admin_creates_a_viewer_who_can_sign_in_read_only(client, admin_token, auth, only_admin):
    created = await client.post("/api/users", headers=auth(admin_token), json=NEW)
    assert created.status_code == 201
    assert created.json()["role"] == "viewer" and "password" not in created.text

    login = await _login(client, "shepherd", "long-enough-pw")
    assert login.status_code == 200 and login.json()["role"] == "viewer"
    token = login.json()["access_token"]
    client.cookies.clear()
    assert (await client.get("/api/cameras", headers=auth(token))).status_code == 200
    assert (await client.get("/api/users", headers=auth(token))).status_code == 403
    assert (await client.post("/api/users", headers=auth(token), json={**NEW, "username": "x2x"})).status_code == 403

    listed = await client.get("/api/users", headers=auth(admin_token))
    assert [user["username"] for user in listed.json()] == ["admin", "shepherd"]


@pytest.mark.asyncio
async def test_user_validation_and_duplicates(client, admin_token, auth, only_admin):
    assert (await client.post("/api/users", headers=auth(admin_token), json=NEW)).status_code == 201
    assert (await client.post("/api/users", headers=auth(admin_token), json=NEW)).status_code == 409
    assert (await client.post("/api/users", headers=auth(admin_token),
                              json={**NEW, "username": "other", "password": "short"})).status_code == 422
    assert (await client.put("/api/users/9999", headers=auth(admin_token), json={"is_active": False})).status_code == 404
    client.cookies.clear()
    assert (await client.get("/api/users")).status_code == 401


@pytest.mark.asyncio
async def test_deactivating_a_user_locks_them_out_immediately(client, admin_token, auth, only_admin):
    user_id = (await client.post("/api/users", headers=auth(admin_token), json=NEW)).json()["id"]
    token = (await _login(client, "shepherd", "long-enough-pw")).json()["access_token"]
    client.cookies.clear()

    updated = await client.put(f"/api/users/{user_id}", headers=auth(admin_token), json={"is_active": False})
    assert updated.status_code == 200 and updated.json()["is_active"] is False
    assert (await client.get("/api/cameras", headers=auth(token))).status_code == 401
    assert (await _login(client, "shepherd", "long-enough-pw")).status_code == 401


@pytest.mark.asyncio
async def test_admin_can_reset_a_password_and_change_a_role(client, admin_token, auth, only_admin):
    user_id = (await client.post("/api/users", headers=auth(admin_token), json=NEW)).json()["id"]
    updated = await client.put(f"/api/users/{user_id}", headers=auth(admin_token),
                               json={"password": "another-long-pw", "role": "admin"})
    assert updated.status_code == 200 and updated.json()["role"] == "admin"
    assert (await _login(client, "shepherd", "long-enough-pw")).status_code == 401
    assert (await _login(client, "shepherd", "another-long-pw")).json()["role"] == "admin"


@pytest.mark.asyncio
async def test_the_last_active_admin_cannot_be_removed(client, admin_token, auth, only_admin):
    me = (await client.get("/api/auth/me", headers=auth(admin_token))).json()
    for change in ({"is_active": False}, {"role": "viewer"}):
        blocked = await client.put(f"/api/users/{me['id']}", headers=auth(admin_token), json=change)
        assert blocked.status_code == 409
    still = (await client.get("/api/auth/me", headers=auth(admin_token))).json()
    assert still["role"] == "admin" and still["is_active"] is True


@pytest.mark.asyncio
async def test_change_own_password(client, admin_token, auth, only_admin):
    wrong = await client.post("/api/auth/change-password", headers=auth(admin_token),
                              json={"current_password": "nope", "new_password": "brand-new-password"})
    assert wrong.status_code == 400
    short = await client.post("/api/auth/change-password", headers=auth(admin_token),
                              json={"current_password": "test-admin-pw", "new_password": "short"})
    assert short.status_code == 422
    changed = await client.post("/api/auth/change-password", headers=auth(admin_token),
                                json={"current_password": "test-admin-pw", "new_password": "brand-new-password"})
    assert changed.status_code == 204
    assert (await _login(client, "admin", "test-admin-pw")).status_code == 401
    assert (await _login(client, "admin", "brand-new-password")).status_code == 200
    client.cookies.clear()
    assert (await client.post("/api/auth/change-password",
                              json={"current_password": "a", "new_password": "brand-new-password"})).status_code == 401
