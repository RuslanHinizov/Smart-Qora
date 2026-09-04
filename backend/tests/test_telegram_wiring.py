import asyncio

import pytest

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import LineDirection
from app.db.seed import ensure_default_camera
from app.services import counting_service as cs
from app.telegram.notifications import notifier
from fakes import FakeCameraStream, FakeDetector, straight_crossing_script

NAMES = {0: "sheep"}


@pytest.mark.asyncio
async def test_crossing_triggers_aggregated_telegram_send(monkeypatch, clean_db):
    sent: list[str] = []

    async def fake_sender(message: str) -> None:
        sent.append(message)

    notifier.configure(0.05, fake_sender, "en")
    try:
        async with SessionLocal() as db:
            camera = await ensure_default_camera(db, get_settings())
            camera.name = "Main Gate"
            camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y = 0, 50, 100, 50
            camera.inside_direction = LineDirection.DOWN
            camera.confidence = 0.1
            await db.commit()

        script = straight_crossing_script(track_id=1, cls_index=0)
        monkeypatch.setattr(cs, "CameraStream", lambda source: FakeCameraStream(source, len(script)))
        monkeypatch.setattr(cs, "LivestockDetector", lambda *a, **k: FakeDetector(script, NAMES))

        await cs.CountingService(get_settings()).run()
        await asyncio.sleep(0.2)  # let the aggregator's flush task fire

        assert len(sent) == 1
        assert "ENTERED" in sent[0] and "+1" in sent[0] and "Main Gate" in sent[0]
    finally:
        notifier.configure(0, None, "en")


@pytest.mark.asyncio
async def test_notifier_is_noop_without_sender():
    notifier.configure(1, None, "en")
    await notifier.add("IN", 3, "Gate")  # must not raise


@pytest.mark.asyncio
async def test_saving_telegram_settings_reconfigures_notifier_without_restart(client, admin_token, auth, clean_db):
    notifier.configure(0, None, "en")
    try:
        # a non-telegram change must not wire a sender
        await client.put("/api/settings", headers=auth(admin_token), json={"default_confidence": 0.3})
        assert notifier._aggregator is None

        # setting token + chat id must wire the sender live
        await client.put("/api/settings", headers=auth(admin_token),
                         json={"telegram_bot_token": "123:AAA", "telegram_chat_id": "42"})
        assert notifier._aggregator is not None
    finally:
        notifier.configure(0, None, "en")


class _FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class _FakeUpdate:
    def __init__(self):
        self.message = _FakeMessage()


def test_build_handlers_covers_expected_commands():
    from app.db.database import SessionLocal
    from app.telegram.commands import build_handlers

    commands = {c for handler in build_handlers(SessionLocal, "en") for c in handler.commands}
    assert {"start", "status", "today", "help"} <= commands


@pytest.mark.asyncio
async def test_status_command_replies_with_barn_state(clean_db):
    from app.db.database import SessionLocal
    from app.telegram.commands import build_handlers

    handler = next(h for h in build_handlers(SessionLocal, "en") if "status" in h.commands)
    update = _FakeUpdate()
    await handler.callback(update, None)
    assert update.message.replies and "BARN STATUS" in update.message.replies[0]


@pytest.mark.asyncio
async def test_command_bot_start_is_noop_without_token():
    from app.db.database import SessionLocal
    from app.telegram.bot import CommandBot

    bot = CommandBot()
    await bot.start("", SessionLocal, "en")  # must not raise, must not create an Application
    await bot.stop()
