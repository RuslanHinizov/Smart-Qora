"""Test bootstrap.

Points the app at a throwaway SQLite file, runs migrations, and exposes an
``httpx`` client + a DB session. Must configure the environment BEFORE any
``app.*`` import so the module-level engine binds to the temp database.
"""
import os
import tempfile
from pathlib import Path

_TMPDIR = Path(tempfile.mkdtemp(prefix="smartqora-test-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMPDIR / 'test.db'}"
os.environ["MODEL_PATH"] = str(_TMPDIR / "no-model.pt")  # lifespan skips the vision worker
os.environ["REQUIRE_CUDA"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-pw"
os.environ["CORS_ORIGINS"] = ""
os.environ.setdefault("ALLOWED_CLASSES", "sheep,cattle,goat,horse")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

_BACKEND = Path(__file__).resolve().parents[1]


def _migrate() -> None:
    cfg = AlembicConfig(str(_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND / "alembic"))
    command.upgrade(cfg, "head")


_migrate()

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import Role, User  # noqa: E402
from app.db.seed import ensure_admin  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def clean_db():
    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM animal_events"))
        await db.execute(text("DELETE FROM daily_statistics"))
        await db.execute(text("DELETE FROM cameras"))
        await db.execute(text("UPDATE herd_state SET current_inside = 0, baseline = 0"))
        await db.execute(text("UPDATE app_settings SET default_language = 'ru', telegram_bot_token = '', telegram_chat_id = ''"))
        await db.commit()
    yield


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as db:
        yield db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _login(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post("/api/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client):
    async with SessionLocal() as db:
        await ensure_admin(db, get_settings())
    return await _login(client, "admin", "test-admin-pw")


@pytest_asyncio.fixture
async def viewer_token(client):
    async with SessionLocal() as db:
        if not await db.scalar(text("SELECT id FROM users WHERE username = 'viewer'")):
            db.add(User(username="viewer", password_hash=hash_password("viewer-pw"), role=Role.viewer))
            await db.commit()
    return await _login(client, "viewer", "viewer-pw")


@pytest.fixture
def auth():
    return lambda token: {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reset_frame_bus():
    from app.services.frame_bus import frame_bus
    frame_bus.latest_jpeg = None
    frame_bus.latest_ts = 0.0
    frame_bus._subscribers.clear()
    yield frame_bus
    frame_bus.latest_jpeg = None
    frame_bus.latest_ts = 0.0
    frame_bus._subscribers.clear()
