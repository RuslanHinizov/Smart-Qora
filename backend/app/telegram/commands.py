"""Telegram bot command handlers.

Every command is gated on the chat being in ``AppSettings.telegram_chat_id``
(see :mod:`app.telegram.chats`). Replies use the chat's language (``/dil``),
defaulting to Russian.
"""

import asyncio
from datetime import date, timedelta

from sqlalchemy import func, select

from app.db.models import DailyStatistic
from app.services.statistics_service import today_totals
from app.telegram.chats import LANGS, chat_language, is_authorized, set_chat_language

T = {
    "ru": {
        "denied": "⛔️ Этот чат не авторизован.\nВаш Chat ID: {chat_id}\nПопросите администратора добавить его в настройках.",
        "help": "Команды:\n/status — состояние хлева\n/today — сводка за сегодня\n/week — сводка за 7 дней\n/photo — снимок с камеры\n/dil ru|kk|en|tr — язык\n/help — эта справка",
        "welcome": "🐄 Smart Qora на связи. Язык: {lang}. /help — список команд.",
        "status": "🐄 СОСТОЯНИЕ ХЛЕВА\n\nСейчас: {current}\nСегодня:\n🟢 Вошло: {total_in}\n🔴 Вышло: {total_out}\n\n📷 Камера: {camera}\n🤖 ИИ: {ai}",
        "today": "📅 СЕГОДНЯ\n\n🟢 Вошло: {total_in}\n🔴 Вышло: {total_out}\n📊 Сейчас в хлеву: {current}",
        "week": "🗓 ЗА 7 ДНЕЙ\n\n🟢 Вошло: {total_in}\n🔴 Вышло: {total_out}",
        "lang_usage": "Использование: /dil ru|kk|en|tr",
        "lang_set": "✅ Язык переключён на «{lang}».",
        "no_photo": "📷 Кадр с камеры сейчас недоступен.",
        "photo_caption": "📷 {camera} · сейчас в хлеву: {current}",
    },
    "kk": {
        "denied": "⛔️ Бұл чат рұқсат етілмеген.\nСіздің Chat ID: {chat_id}\nӘкімшіден оны параметрлерге қосуын сұраңыз.",
        "help": "Командалар:\n/status — қора жағдайы\n/today — бүгінгі есеп\n/week — 7 күндік есеп\n/photo — камера суреті\n/dil ru|kk|en|tr — тіл\n/help — осы анықтама",
        "welcome": "🐄 Smart Qora байланыста. Тіл: {lang}. /help — командалар.",
        "status": "🐄 ҚОРА ЖАҒДАЙЫ\n\nҚазір: {current}\nБүгін:\n🟢 Кірді: {total_in}\n🔴 Шықты: {total_out}\n\n📷 Камера: {camera}\n🤖 ЖИ: {ai}",
        "today": "📅 БҮГІН\n\n🟢 Кірді: {total_in}\n🔴 Шықты: {total_out}\n📊 Қазір қорада: {current}",
        "week": "🗓 7 КҮН\n\n🟢 Кірді: {total_in}\n🔴 Шықты: {total_out}",
        "lang_usage": "Қолдану: /dil ru|kk|en|tr",
        "lang_set": "✅ Тіл «{lang}» болып ауыстырылды.",
        "no_photo": "📷 Камера кадры қазір қолжетімсіз.",
        "photo_caption": "📷 {camera} · қазір қорада: {current}",
    },
    "en": {
        "denied": "⛔️ This chat is not authorised.\nYour Chat ID: {chat_id}\nAsk an admin to add it in the settings.",
        "help": "Commands:\n/status — barn state\n/today — today's summary\n/week — 7-day summary\n/photo — camera snapshot\n/dil ru|kk|en|tr — language\n/help — this help",
        "welcome": "🐄 Smart Qora is online. Language: {lang}. /help for commands.",
        "status": "🐄 BARN STATUS\n\nCurrent: {current}\nToday:\n🟢 Entered: {total_in}\n🔴 Left: {total_out}\n\n📷 Camera: {camera}\n🤖 AI: {ai}",
        "today": "📅 TODAY\n\n🟢 Entered: {total_in}\n🔴 Left: {total_out}\n📊 Currently in barn: {current}",
        "week": "🗓 LAST 7 DAYS\n\n🟢 Entered: {total_in}\n🔴 Left: {total_out}",
        "lang_usage": "Usage: /dil ru|kk|en|tr",
        "lang_set": "✅ Language switched to \"{lang}\".",
        "no_photo": "📷 No camera frame available right now.",
        "photo_caption": "📷 {camera} · currently in barn: {current}",
    },
    "tr": {
        "denied": "⛔️ Bu chat yetkili değil.\nChat ID'niz: {chat_id}\nYöneticiden bunu ayarlara eklemesini isteyin.",
        "help": "Komutlar:\n/status — ahır durumu\n/today — bugünün özeti\n/week — 7 günlük özet\n/photo — kamera görüntüsü\n/dil ru|kk|en|tr — dil\n/help — bu yardım",
        "welcome": "🐄 Smart Qora bağlandı. Dil: {lang}. Komutlar için /help.",
        "status": "🐄 AHIR DURUMU\n\nMevcut: {current}\nBugün:\n🟢 Giren: {total_in}\n🔴 Çıkan: {total_out}\n\n📷 Kamera: {camera}\n🤖 Yapay zeka: {ai}",
        "today": "📅 BUGÜN\n\n🟢 Giren: {total_in}\n🔴 Çıkan: {total_out}\n📊 Ahırda mevcut: {current}",
        "week": "🗓 SON 7 GÜN\n\n🟢 Giren: {total_in}\n🔴 Çıkan: {total_out}",
        "lang_usage": "Kullanım: /dil ru|kk|en|tr",
        "lang_set": "✅ Dil \"{lang}\" olarak değiştirildi.",
        "no_photo": "📷 Şu an kamera görüntüsü alınamıyor.",
        "photo_caption": "📷 {camera} · ahırda mevcut: {current}",
    },
}


def _tr(lang: str) -> dict:
    return T.get(lang, T["ru"])


async def _week_totals(session) -> dict[str, int]:
    since = date.today() - timedelta(days=6)
    row = (await session.execute(
        select(func.coalesce(func.sum(DailyStatistic.total_in), 0),
               func.coalesce(func.sum(DailyStatistic.total_out), 0))
        .where(DailyStatistic.date >= since))).one()
    return {"total_in": int(row[0]), "total_out": int(row[1])}


def build_handlers(session_factory, status_provider):
    from telegram.ext import CommandHandler

    async def _authorised(update):
        """Return (chat_id, lang) if allowed, else reply 'denied' and return None."""
        chat_id = str(update.effective_chat.id)
        async with session_factory() as session:
            ok = await is_authorized(session, chat_id)
            lang = await chat_language(session, chat_id) if ok else "ru"
        if not ok:
            await update.message.reply_text(_tr(lang)["denied"].format(chat_id=chat_id))
            return None
        return chat_id, lang

    async def start_command(update, context):
        got = await _authorised(update)
        if got:
            await update.message.reply_text(_tr(got[1])["welcome"].format(lang=got[1]))

    async def help_command(update, context):
        got = await _authorised(update)
        if got:
            await update.message.reply_text(_tr(got[1])["help"])

    async def status_command(update, context):
        got = await _authorised(update)
        if not got:
            return
        async with session_factory() as session:
            totals = await today_totals(session)
        st = status_provider()
        await update.message.reply_text(_tr(got[1])["status"].format(
            current=totals["current"], total_in=totals["total_in"], total_out=totals["total_out"],
            camera=st["camera"], ai=st["ai"]))

    async def today_command(update, context):
        got = await _authorised(update)
        if not got:
            return
        async with session_factory() as session:
            totals = await today_totals(session)
        await update.message.reply_text(_tr(got[1])["today"].format(**totals))

    async def week_command(update, context):
        got = await _authorised(update)
        if not got:
            return
        async with session_factory() as session:
            totals = await _week_totals(session)
        await update.message.reply_text(_tr(got[1])["week"].format(**totals))

    async def photo_command(update, context):
        got = await _authorised(update)
        if not got:
            return
        from app.services.frame_bus import frame_bus
        queue = frame_bus.subscribe()
        try:
            jpeg = await asyncio.wait_for(queue.get(), timeout=4.0)
        except asyncio.TimeoutError:
            jpeg = frame_bus.latest_jpeg if frame_bus.is_fresh(30.0) else None
        finally:
            frame_bus.unsubscribe(queue)
        if not jpeg:
            await update.message.reply_text(_tr(got[1])["no_photo"])
            return
        async with session_factory() as session:
            totals = await today_totals(session)
        st = status_provider()
        await update.message.reply_photo(jpeg, caption=_tr(got[1])["photo_caption"].format(
            camera=st["camera"], current=totals["current"]))

    async def lang_command(update, context):
        got = await _authorised(update)
        if not got:
            return
        chat_id, lang = got
        arg = (context.args[0].lower() if context.args else "")
        if arg not in LANGS:
            await update.message.reply_text(_tr(lang)["lang_usage"])
            return
        async with session_factory() as session:
            await set_chat_language(session, chat_id, arg)
        await update.message.reply_text(_tr(arg)["lang_set"].format(lang=arg))

    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("status", status_command),
        CommandHandler("today", today_command),
        CommandHandler("week", week_command),
        CommandHandler(["photo", "foto", "kamera"], photo_command),
        CommandHandler(["dil", "lang", "language"], lang_command),
    ]
