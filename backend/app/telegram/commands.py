from datetime import date

from app.services.statistics_service import statistics

STATUS_TEXT = {
    "ru": "🐄 СОСТОЯНИЕ ХЛЕВА\n\nСейчас: {current}\nСегодня:\n🟢 Вошло: {total_in}\n🔴 Вышло: {total_out}\n\n📷 Камера: {camera}\n🤖 ИИ: {ai}",
    "kk": "🐄 ҚОРА ЖАҒДАЙЫ\n\nҚазір: {current} мал\nБүгін:\n🟢 Кірді: {total_in}\n🔴 Шықты: {total_out}\n\n📷 Камера: {camera}\n🤖 ЖИ: {ai}",
    "en": "🐄 BARN STATUS\n\nCurrent: {current}\nToday:\n🟢 Entered: {total_in}\n🔴 Left: {total_out}\n\n📷 Camera: {camera}\n🤖 AI: {ai}",
    "tr": "🐄 AHIR DURUMU\n\nMevcut: {current}\nBugün:\n🟢 Giren: {total_in}\n🔴 Çıkan: {total_out}\n\n📷 Kamera: {camera}\n🤖 Yapay zeka: {ai}",
}


def format_status(values: dict[str, int], language: str, camera: str = "ONLINE", ai: str = "ACTIVE") -> str:
    return STATUS_TEXT.get(language, STATUS_TEXT["ru"]).format(**values, camera=camera, ai=ai)


def build_handlers(session_factory, language: str = "ru"):
    from telegram.ext import CommandHandler

    async def status_command(update, context):
        async with session_factory() as session:
            totals = await statistics(session, date.today())
        await update.message.reply_text(format_status(totals, language))

    async def start_command(update, context):
        await update.message.reply_text("Smart Qora — /status /today /help")

    return [CommandHandler("start", start_command), CommandHandler("status", status_command),
            CommandHandler("today", status_command), CommandHandler("help", start_command)]
