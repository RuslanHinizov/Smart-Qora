"""Apply the Telegram config (aggregating notifier + command bot) from the
current AppSettings row, falling back to env. Called once at startup and again
whenever an admin edits the Telegram / language settings, so changes take effect
without a backend restart.
"""

import logging

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import AppSettings
from app.telegram.bot import TelegramSender, command_bot
from app.telegram.notifications import notifier

logger = logging.getLogger(__name__)

# settings fields that, when changed, require re-applying the Telegram config
TELEGRAM_KEYS = {"telegram_bot_token", "telegram_chat_id", "telegram_aggregation_seconds", "default_language"}


async def _resolve() -> tuple[str, str, int, str]:
    settings = get_settings()
    async with SessionLocal() as session:
        row = await session.get(AppSettings, 1)
    token = (row.telegram_bot_token if row else "") or settings.telegram_bot_token
    chat_id = (row.telegram_chat_id if row else "") or settings.telegram_chat_id
    seconds = (row.telegram_aggregation_seconds if row else 0) or settings.telegram_aggregation_seconds
    language = (row.default_language if row else "") or settings.default_language
    return token, chat_id, seconds, language


async def apply_telegram_config(*, restart_bot: bool = True) -> None:
    token, chat_id, seconds, language = await _resolve()
    sender = TelegramSender(token, chat_id).send if token and chat_id else None
    notifier.configure(seconds, sender, language)
    if restart_bot:
        await command_bot.stop()          # start() is a no-op while an app is running
        await command_bot.start(token, SessionLocal, language)
    logger.info("telegram_config_applied", extra={"telegram": bool(sender)})
