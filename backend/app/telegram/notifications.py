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


def format_notification(direction: str, count: int, current: int, camera: str, language: str = "ru", at: datetime | None = None) -> str:
    t = TEXT.get(language, TEXT["ru"]); sign = "+" if direction == "IN" else "-"
    at = at or datetime.now()
    return f"{t[direction.lower()]}\n\n{sign}{count} {t['animals']}\n\n{t['current']}: {current}\n\n🕐 {at:%H:%M:%S}\n{t['camera']}: {camera}"


@dataclass
class Pending:
    count: int = 0
    current: int = 0
    camera: str = ""


class NotificationAggregator:
    def __init__(self, seconds: float, sender, language: str = "ru"):
        self.seconds, self.sender, self.language = seconds, sender, language
        self.pending = defaultdict(Pending)
        self.tasks: dict[str, asyncio.Task] = {}

    async def add(self, direction: str, current: int, camera: str) -> None:
        item = self.pending[direction]; item.count += 1; item.current = current; item.camera = camera
        if direction not in self.tasks or self.tasks[direction].done():
            self.tasks[direction] = asyncio.create_task(self._flush_later(direction))

    async def _flush_later(self, direction: str) -> None:
        await asyncio.sleep(self.seconds)
        item = self.pending.pop(direction)
        message = format_notification(direction, item.count, item.current, item.camera, self.language)
        for attempt in range(4):
            try:
                await self.sender(message); return
            except Exception:
                logger.exception("telegram_notification_failed attempt=%s", attempt + 1)
                await asyncio.sleep(2 ** attempt)


class Notifier:
    """Process-local holder so the vision worker can fire notifications without
    knowing how (or whether) Telegram is configured. A no-op until ``configure``d."""

    def __init__(self):
        self._aggregator: NotificationAggregator | None = None

    def configure(self, seconds: float, sender, language: str) -> None:
        self._aggregator = NotificationAggregator(seconds, sender, language) if sender else None

    async def add(self, direction: str, current: int, camera: str) -> None:
        if self._aggregator is not None:
            await self._aggregator.add(direction, current, camera)


notifier = Notifier()
