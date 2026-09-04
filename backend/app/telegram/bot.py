import logging

logger = logging.getLogger(__name__)


class TelegramSender:
    """Low-level Telegram client. ``token`` only — the chat is passed per call so
    one sender fans out to every authorised chat."""

    def __init__(self, token: str):
        self.token = token

    def _bot(self):
        from telegram import Bot
        return Bot(self.token)

    async def send(self, chat_id: str, text: str) -> None:
        if not self.token or not chat_id:
            return
        await self._bot().send_message(chat_id=chat_id, text=text)

    async def send_photo(self, chat_id: str, photo: bytes, caption: str | None = None) -> None:
        if not self.token or not chat_id:
            return
        await self._bot().send_photo(chat_id=chat_id, photo=photo, caption=caption)


class CommandBot:
    """Long-polling bot for the /start /status /today /week /photo /dil /help commands.

    A no-op until :meth:`start` is called with a token; failures to reach Telegram
    are logged and swallowed so they never block application startup.
    """

    def __init__(self):
        self._application = None

    async def start(self, token: str, session_factory, status_provider) -> None:
        if not token or self._application is not None:
            return
        try:
            from telegram import BotCommand
            from telegram.ext import Application

            from app.telegram.commands import build_handlers

            application = Application.builder().token(token).build()
            application.add_handlers(build_handlers(session_factory, status_provider))
            await application.initialize()
            await application.bot.set_my_commands([
                BotCommand("status", "текущее состояние хлева"),
                BotCommand("today", "сводка за сегодня"),
                BotCommand("week", "сводка за 7 дней"),
                BotCommand("photo", "снимок с камеры"),
                BotCommand("dil", "язык: /dil ru|kk|en|tr"),
                BotCommand("help", "список команд"),
            ])
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            self._application = application
            logger.info("telegram_command_bot_started")
        except Exception:
            logger.exception("telegram_command_bot_start_failed")

    async def stop(self) -> None:
        application, self._application = self._application, None
        if application is None:
            return
        try:
            if application.updater is not None:
                await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("telegram_command_bot_stopped")
        except Exception:
            logger.exception("telegram_command_bot_stop_failed")


command_bot = CommandBot()
