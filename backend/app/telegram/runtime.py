"""Apply the Telegram config (aggregating notifier + command bot) from the
current AppSettings, falling back to env. Called once at startup and again
whenever an admin edits the Telegram / language settings, so changes take effect
without a backend restart.
"""

import logging

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import AppSettings
from app.telegram.bot import TelegramSender, command_bot
from app.telegram.chats import recipients
from app.telegram.notifications import notifier

logger = logging.getLogger(__name__)

# settings fields that, when changed, require re-applying the Telegram config
TELEGRAM_KEYS = {"telegram_bot_token", "telegram_chat_id", "telegram_aggregation_seconds"}

# set once by main.py so the command bot can report live camera / AI status
_status_provider = lambda: {"camera": "OFFLINE", "ai": "IDLE"}  # noqa: E731


def set_status_provider(fn) -> None:
    global _status_provider
    _status_provider = fn


async def _config() -> tuple[str, int]:
    settings = get_settings()
    async with SessionLocal() as session:
        row = await session.get(AppSettings, 1)
    token = (row.telegram_bot_token if row else "") or settings.telegram_bot_token
    seconds = (row.telegram_aggregation_seconds if row else 0) or settings.telegram_aggregation_seconds
    return token, seconds


async def _recipients() -> list[tuple[str, str]]:
    async with SessionLocal() as session:
        return await recipients(session)


async def apply_telegram_config(*, restart_bot: bool = True) -> None:
    token, seconds = await _config()
    sender = TelegramSender(token) if token else None
    notifier.configure(seconds, sender.send if sender else None, _recipients)
    if restart_bot:
        await command_bot.stop()          # start() is a no-op while an app is running
        await command_bot.start(token, SessionLocal, _status_provider)
    logger.info("telegram_config_applied", extra={"telegram": bool(sender)})
