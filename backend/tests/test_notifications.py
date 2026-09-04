import asyncio
from datetime import datetime

from app.telegram.notifications import NotificationAggregator, format_alert, format_digest, format_notification


def test_telegram_formatting_in_four_languages():
    at = datetime(2026, 1, 1, 20, 43, 12)
    for code, phrase in (("ru", "ВОШЛИ"), ("kk", "КІРДІ"), ("en", "ENTERED"), ("tr", "GİRDİ")):
        message = format_notification("IN", 5, 127, "Main Gate", code, at)
        assert phrase in message and "+5" in message and "20:43:12" in message


def test_alert_and_digest_localised():
    assert "остановлен" in format_alert("worker_down", "ru")
    assert "durdu" in format_alert("worker_down", "tr")
    assert "3h" in format_alert("idle", "en", hours=3)
    assert "Giren: 7" in format_digest(7, 2, 5, "tr")


def test_aggregation_combines_same_direction():
    async def scenario():
        flushes = []
        async def flush(direction, count, current, camera): flushes.append((direction, count, current, camera))
        aggregator = NotificationAggregator(0.01, flush)
        await aggregator.add("IN", 10, "Gate")
        await aggregator.add("IN", 11, "Gate")
        await asyncio.sleep(0.03)
        assert flushes == [("IN", 2, 11, "Gate")]
    asyncio.run(scenario())


def test_aggregation_separates_directions():
    async def scenario():
        flushes = []
        async def flush(direction, count, current, camera): flushes.append(direction)
        aggregator = NotificationAggregator(0.01, flush)
        await aggregator.add("IN", 5, "Gate"); await aggregator.add("OUT", 4, "Gate")
        await asyncio.sleep(0.03)
        assert sorted(flushes) == ["IN", "OUT"]
    asyncio.run(scenario())
