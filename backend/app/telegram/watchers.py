"""Background tasks that push Telegram messages: fault alerts, an idle-gate
warning, and a daily digest. All are no-ops until Telegram is configured
(``notifier`` has recipients).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.database import SessionLocal
from app.db.models import AnimalEvent, AppSettings
from app.services.statistics_service import today_totals
from app.telegram.notifications import format_alert, format_digest
from app.telegram.notifications import notifier

logger = logging.getLogger(__name__)


async def _last_event_at(session) -> datetime | None:
    return await session.scalar(select(func.max(AnimalEvent.timestamp)))


async def health_watcher(app, interval: float = 30.0) -> None:
    """Alert on AI-worker / camera transitions and on a long gate silence."""
    last = "ok"
    idle_alerted = False
    while True:
        await asyncio.sleep(interval)
        try:
            sup = getattr(app.state, "supervisor", None)
            if sup is None or sup.state == "failed":
                state = "worker_down"
            elif sup.running and sup.camera_status == "OFFLINE":
                state = "camera_offline"
            else:
                state = "ok"

            if state != last:
                if state == "ok":
                    await notifier.alert(lambda l: format_alert("recovered", l))
                else:
                    await notifier.alert(lambda l, s=state: format_alert(s, l))
                last = state

            # idle-gate warning (opt-in via telegram_idle_hours)
            async with SessionLocal() as session:
                row = await session.get(AppSettings, 1)
                idle_hours = row.telegram_idle_hours if row else None
                last_at = await _last_event_at(session) if idle_hours else None
            if idle_hours and last_at is not None:
                silent = datetime.now(timezone.utc) - last_at
                if silent >= timedelta(hours=idle_hours) and state == "ok":
                    if not idle_alerted:
                        await notifier.alert(lambda l, h=idle_hours: format_alert("idle", l, hours=h))
                        idle_alerted = True
                else:
                    idle_alerted = False
        except Exception:  # noqa: BLE001 - a watcher must never die
            logger.exception("health_watcher_iteration_failed")


async def digest_loop(app, interval: float = 60.0) -> None:
    """Once per day at ``telegram_digest_hour`` (container local time) send a summary."""
    sent_on = None
    while True:
        await asyncio.sleep(interval)
        try:
            async with SessionLocal() as session:
                row = await session.get(AppSettings, 1)
                hour = row.telegram_digest_hour if row else None
                if hour is None:
                    continue
                now = datetime.now()
                if now.hour != hour or now.date() == sent_on:
                    continue
                totals = await today_totals(session)
            sent_on = now.date()
            await notifier.alert(lambda l: format_digest(
                totals["total_in"], totals["total_out"], totals["current"], l))
        except Exception:  # noqa: BLE001
            logger.exception("digest_loop_iteration_failed")
