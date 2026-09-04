import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

TEXT = {
    "ru": {"in": "🐄 ВОШЛИ В ХЛЕВ", "out": "🐄 ВЫШЛИ ИЗ ХЛЕВА", "current": "📊 Сейчас в хлеву", "animals": "животных", "camera": "📷 Камера"},
    "kk": {"in": "🐄 ҚОРАҒА КІРДІ", "out": "🐄 ҚОРАДАН ШЫҚТЫ", "current": "📊 Қорадағы қазіргі саны", "animals": "мал", "camera": "📷 Камера"},
    "en": {"in": "🐄 ENTERED THE BARN", "out": "🐄 LEFT THE BARN", "current": "📊 Currently in barn", "animals": "animals", "camera": "📷 Camera"},
    "tr": {"in": "🐄 AHIRA GİRDİ", "out": "🐄 AHIRDAN ÇIKTI", "current": "📊 Ahırdaki mevcut sayı", "animals": "hayvan", "camera": "📷 Kamera"},
}

ALERT = {
    "ru": {
        "worker_down": "⚠️ Модуль ИИ остановлен — подсчёт не ведётся. Проверьте сервер.",
        "camera_offline": "⚠️ Камера недоступна — нет видеопотока.",
        "recovered": "✅ Система восстановлена, подсчёт возобновлён.",
        "idle": "⚠️ Уже {hours} ч нет ни одного прохода через ворота. Проверьте камеру.",
    },
    "kk": {
        "worker_down": "⚠️ ЖИ модулі тоқтады — санақ жүрмейді. Серверді тексеріңіз.",
        "camera_offline": "⚠️ Камера қолжетімсіз — видео ағыны жоқ.",
        "recovered": "✅ Жүйе қалпына келді, санақ жалғасуда.",
        "idle": "⚠️ {hours} сағат бойы қақпадан бірде-бір өту жоқ. Камераны тексеріңіз.",
    },
    "en": {
        "worker_down": "⚠️ The AI worker has stopped — counting is paused. Check the server.",
        "camera_offline": "⚠️ Camera is unreachable — no video stream.",
        "recovered": "✅ System recovered, counting resumed.",
        "idle": "⚠️ No gate crossings for {hours}h. Check the camera.",
    },
    "tr": {
        "worker_down": "⚠️ Yapay zeka modülü durdu — sayım yapılmıyor. Sunucuyu kontrol edin.",
        "camera_offline": "⚠️ Kameraya ulaşılamıyor — video akışı yok.",
        "recovered": "✅ Sistem düzeldi, sayım devam ediyor.",
        "idle": "⚠️ {hours} saattir kapıdan hiç geçiş yok. Kamerayı kontrol edin.",
    },
}

DIGEST = {
    "ru": "📅 СВОДКА ЗА ДЕНЬ\n\n🟢 Вошло: {total_in}\n🔴 Вышло: {total_out}\n📊 Сейчас в хлеву: {current}",
    "kk": "📅 КҮНДІК ЕСЕП\n\n🟢 Кірді: {total_in}\n🔴 Шықты: {total_out}\n📊 Қазір қорада: {current}",
    "en": "📅 DAILY SUMMARY\n\n🟢 Entered: {total_in}\n🔴 Left: {total_out}\n📊 Currently in barn: {current}",
    "tr": "📅 GÜNLÜK ÖZET\n\n🟢 Giren: {total_in}\n🔴 Çıkan: {total_out}\n📊 Ahırda mevcut: {current}",
}


def _t(table: dict, language: str) -> dict:
    return table.get(language, table["ru"])


def format_notification(direction: str, count: int, current: int, camera: str, language: str = "ru", at: datetime | None = None) -> str:
    t = _t(TEXT, language); sign = "+" if direction == "IN" else "-"
    at = at or datetime.now()
    return f"{t[direction.lower()]}\n\n{sign}{count} {t['animals']}\n\n{t['current']}: {current}\n\n🕐 {at:%H:%M:%S}\n{t['camera']}: {camera}"


def format_alert(key: str, language: str, **kw) -> str:
    return _t(ALERT, language)[key].format(**kw)


def format_digest(total_in: int, total_out: int, current: int, language: str = "ru") -> str:
    return _t(DIGEST, language).format(total_in=total_in, total_out=total_out, current=current)


@dataclass
class Pending:
    count: int = 0
    current: int = 0
    camera: str = ""


class NotificationAggregator:
    """Collapses a burst of crossings in the same direction into one message."""

    def __init__(self, seconds: float, flush_cb):
        self.seconds, self.flush_cb = seconds, flush_cb
        self.pending = defaultdict(Pending)
        self.tasks: dict[str, asyncio.Task] = {}

    async def add(self, direction: str, current: int, camera: str) -> None:
        item = self.pending[direction]; item.count += 1; item.current = current; item.camera = camera
        if direction not in self.tasks or self.tasks[direction].done():
            self.tasks[direction] = asyncio.create_task(self._flush_later(direction))

    async def _flush_later(self, direction: str) -> None:
        await asyncio.sleep(self.seconds)
        item = self.pending.pop(direction)
        await self.flush_cb(direction, item.count, item.current, item.camera)


class Notifier:
    """Process-local holder so the vision worker can fire notifications without
    knowing how (or whether) Telegram is configured. A no-op until ``configure``d.

    ``send`` is ``async (chat_id, text) -> None``; ``recipients`` is
    ``async () -> list[(chat_id, language)]`` and is re-read for every message so
    a chat registered after startup still gets alerts.
    """

    def __init__(self):
        self._agg: NotificationAggregator | None = None
        self._send = None
        self._recipients = None

    def configure(self, seconds: float, send, recipients) -> None:
        self._send, self._recipients = send, recipients
        self._agg = NotificationAggregator(seconds, self._fanout_crossing) if send else None

    async def add(self, direction: str, current: int, camera: str) -> None:
        if self._agg is not None:
            await self._agg.add(direction, current, camera)

    async def alert(self, build) -> None:
        """``build(language) -> str`` — send an immediate (non-aggregated) message."""
        if self._send is None:
            return
        for chat_id, lang in await self._recipients():
            await self._deliver(chat_id, build(lang))

    async def _fanout_crossing(self, direction: str, count: int, current: int, camera: str) -> None:
        for chat_id, lang in await self._recipients():
            await self._deliver(chat_id, format_notification(direction, count, current, camera, lang))

    async def _deliver(self, chat_id: str, text: str) -> None:
        for attempt in range(4):
            try:
                await self._send(chat_id, text)
                return
            except Exception:
                logger.exception("telegram_send_failed attempt=%s chat=%s", attempt + 1, chat_id)
                await asyncio.sleep(2 ** attempt)


notifier = Notifier()
