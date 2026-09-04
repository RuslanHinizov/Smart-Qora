import logging

logger = logging.getLogger(__name__)


class TelegramSender:
    def __init__(self, token: str, chat_id: str):
        self.token, self.chat_id = token, chat_id

    async def send(self, text: str) -> None:
        if not self.token or not self.chat_id:
            return
        from telegram import Bot
        await Bot(self.token).send_message(chat_id=self.chat_id, text=text)


class CommandBot:
    """Long-polling bot for the /start /status /today /help commands.

    A no-op until :meth:`start` is called with a token; failures to reach Telegram
    are logged and swallowed so they never block application startup.
    """

    def __init__(self):
        self._application = None

    async def start(self, token: str, session_factory, language: str) -> None:
        if not token or self._application is not None:
            return
        try:
            from telegram.ext import Application

            from app.telegram.commands import build_handlers

            application = Application.builder().token(token).build()
            application.add_handlers(build_handlers(session_factory, language))
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
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
