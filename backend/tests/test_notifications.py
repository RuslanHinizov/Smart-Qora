import asyncio
from datetime import datetime

from app.telegram.notifications import NotificationAggregator, format_notification


def test_telegram_formatting_in_four_languages():
    at = datetime(2026, 1, 1, 20, 43, 12)
    for code, phrase in (("ru", "ВОШЛИ"), ("kk", "КІРДІ"), ("en", "ENTERED"), ("tr", "GİRDİ")):
        message = format_notification("IN", 5, 127, "Main Gate", code, at)
        assert phrase in message and "+5" in message and "20:43:12" in message


def test_aggregation_combines_same_direction():
    async def scenario():
        messages = []
        async def sender(message): messages.append(message)
        aggregator = NotificationAggregator(0.01, sender, "en")
        await aggregator.add("IN", 10, "Gate")
        await aggregator.add("IN", 11, "Gate")
        await asyncio.sleep(0.03)
        assert len(messages) == 1 and "+2 animals" in messages[0] and "11" in messages[0]
    asyncio.run(scenario())


def test_aggregation_separates_directions():
    async def scenario():
        messages = []
        async def sender(message): messages.append(message)
        aggregator = NotificationAggregator(0.01, sender, "en")
        await aggregator.add("IN", 5, "Gate"); await aggregator.add("OUT", 4, "Gate")
        await asyncio.sleep(0.03)
        assert len(messages) == 2
    asyncio.run(scenario())
