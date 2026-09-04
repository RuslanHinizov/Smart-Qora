from datetime import date, datetime, time, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnimalEvent, DailyStatistic, Direction, HerdState


async def today_totals(session: AsyncSession) -> dict[str, int]:
    """Dashboard totals: today's IN/OUT from the rollup (live-event fallback on first run)
    plus the calibratable ``herd_state`` count as ``current``."""
    day = date.today()
    agg = (await session.execute(
        select(func.coalesce(func.sum(DailyStatistic.total_in), 0),
               func.coalesce(func.sum(DailyStatistic.total_out), 0))
        .where(DailyStatistic.date == day)
    )).one()
    total_in, total_out = int(agg[0]), int(agg[1])
    if total_in == 0 and total_out == 0:
        live = await statistics(session, day)
        total_in, total_out = live["total_in"], live["total_out"]
    current = await session.scalar(select(HerdState.current_inside).where(HerdState.id == 1))
    return {"total_in": total_in, "total_out": total_out, "current": int(current or 0)}


async def statistics(session: AsyncSession, day: date | None = None) -> dict[str, int]:
    query = select(
        func.coalesce(func.sum(case((AnimalEvent.direction == Direction.IN, 1), else_=0)), 0),
        func.coalesce(func.sum(case((AnimalEvent.direction == Direction.OUT, 1), else_=0)), 0),
    )
    if day is not None:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        query = query.where(AnimalEvent.timestamp.between(start, end))
    total_in, total_out = (await session.execute(query)).one()
    return {"total_in": int(total_in), "total_out": int(total_out), "current": int(total_in - total_out)}
