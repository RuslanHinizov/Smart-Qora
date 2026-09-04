import asyncio

import pytest

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import AppSettings, LineDirection, TelegramChat
from app.db.seed import ensure_default_camera
from app.services import counting_service as cs
from app.telegram.notifications import notifier
from fakes import FakeCameraStream, FakeDetector, straight_crossing_script

NAMES = {0: "sheep"}


async def _set_authorized(*chat_ids: str) -> None:
    async with SessionLocal() as db:
        row = await db.get(AppSettings, 1) or AppSettings(id=1)
        row.telegram_chat_id = ",".join(chat_ids)
        await db.merge(row)
        await db.commit()


def _recipients_of(*pairs):
    async def provider():
        return list(pairs)
    return provider


class _Chat:
    def __init__(self, cid):
        self.id = cid


class _FakeMessage:
    def __init__(self):
        self.replies: list[str] = []
        self.photos: list[bytes] = []

    async def reply_text(self, text, **kw):
        self.replies.append(text)

    async def reply_photo(self, photo, caption=None, **kw):
        self.photos.append(photo)
        if caption:
            self.replies.append(caption)


class _FakeUpdate:
    def __init__(self, chat_id="42"):
        self.effective_chat = _Chat(chat_id)
        self.message = _FakeMessage()


class _Ctx:
    def __init__(self, args=None):
        self.args = args or []


def _status():
    return {"camera": "ONLINE", "ai": "ACTIVE"}


def _handler(name):
    from app.telegram.commands import build_handlers
    return next(h for h in build_handlers(SessionLocal, _status) for c in h.commands if c == name)


@pytest.mark.asyncio
async def test_crossing_fans_out_to_every_recipient_in_its_language(monkeypatch, clean_db):
    sent: list[tuple[str, str]] = []

    async def fake_send(chat_id: str, text: str) -> None:
        sent.append((chat_id, text))

    notifier.configure(0.05, fake_send, _recipients_of(("10", "en"), ("20", "tr")))
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
        await asyncio.sleep(0.2)

        assert {c for c, _ in sent} == {"10", "20"}
        by_chat = dict(sent)
        assert "ENTERED THE BARN" in by_chat["10"] and "+1" in by_chat["10"]
        assert "AHIRA GİRDİ" in by_chat["20"]
    finally:
        notifier.configure(0, None, _recipients_of())


@pytest.mark.asyncio
async def test_notifier_is_noop_without_sender():
    notifier.configure(1, None, _recipients_of())
    await notifier.add("IN", 3, "Gate")  # must not raise


@pytest.mark.asyncio
async def test_alert_reaches_recipients():
    sent: list[tuple[str, str]] = []

    async def fake_send(chat_id, text):
        sent.append((chat_id, text))

    notifier.configure(0, fake_send, _recipients_of(("10", "ru"), ("20", "en")))
    await notifier.alert(lambda lang: f"boom-{lang}")
    assert sent == [("10", "boom-ru"), ("20", "boom-en")]
    notifier.configure(0, None, _recipients_of())


@pytest.mark.asyncio
async def test_saving_telegram_settings_reconfigures_notifier_without_restart(client, admin_token, auth, clean_db):
    notifier.configure(0, None, _recipients_of())
    try:
        await client.put("/api/settings", headers=auth(admin_token), json={"default_confidence": 0.3})
        assert notifier._agg is None

        await client.put("/api/settings", headers=auth(admin_token),
                         json={"telegram_bot_token": "123:AAA", "telegram_chat_id": "42"})
        assert notifier._agg is not None
    finally:
        notifier.configure(0, None, _recipients_of())


def test_build_handlers_covers_expected_commands():
    from app.telegram.commands import build_handlers

    commands = {c for handler in build_handlers(SessionLocal, _status) for c in handler.commands}
    assert {"start", "help", "status", "today", "week", "photo", "dil"} <= commands


@pytest.mark.asyncio
async def test_unauthorized_chat_is_refused_and_told_its_id(clean_db):
    await _set_authorized("999")
    update = _FakeUpdate(chat_id="123")
    await _handler("status").callback(update, _Ctx())
    assert update.message.replies and "123" in update.message.replies[0]


@pytest.mark.asyncio
async def test_status_command_replies_for_authorized_chat(clean_db):
    await _set_authorized("42")
    update = _FakeUpdate(chat_id="42")
    await _handler("status").callback(update, _Ctx())
    assert update.message.replies and "СОСТОЯНИЕ ХЛЕВА" in update.message.replies[0]  # default ru


@pytest.mark.asyncio
async def test_dil_command_persists_language(clean_db):
    await _set_authorized("42")
    update = _FakeUpdate(chat_id="42")
    await _handler("dil").callback(update, _Ctx(args=["tr"]))
    assert update.message.replies and "Dil" in update.message.replies[0]
    async with SessionLocal() as db:
        row = await db.get(TelegramChat, "42")
    assert row is not None and row.language == "tr"

    update2 = _FakeUpdate(chat_id="42")
    await _handler("status").callback(update2, _Ctx())
    assert "AHIR DURUMU" in update2.message.replies[0]  # now Turkish


@pytest.mark.asyncio
async def test_command_bot_start_is_noop_without_token():
    from app.telegram.bot import CommandBot

    bot = CommandBot()
    await bot.start("", SessionLocal, _status)  # must not raise, must not create an Application
    await bot.stop()
