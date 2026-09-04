from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import HistoryRow, StatisticsRead
from app.db.database import get_session
from app.db.models import DailyStatistic
from app.services.statistics_service import statistics, today_totals

router = APIRouter(prefix="/statistics", tags=["statistics"], dependencies=[Depends(get_current_user)])


@router.get("/today", response_model=StatisticsRead)
async def today(session: AsyncSession = Depends(get_session)):
    return await today_totals(session)


@router.get("/daily", response_model=StatisticsRead)
async def daily(day: date = Query(default_factory=date.today), session: AsyncSession = Depends(get_session)):
    return await statistics(session, day)


def _period_start(day: date, group: str) -> date:
    if group == "week":
        return day - timedelta(days=day.weekday())  # Monday of that ISO week
    if group == "month":
        return day.replace(day=1)
    return day


@router.get("/history", response_model=list[HistoryRow])
async def history(
    from_: date = Query(alias="from"),
    to: date = Query(default_factory=date.today),
    group: Literal["day", "week", "month"] = "day",
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.scalars(
        select(DailyStatistic).where(DailyStatistic.date.between(from_, to))
        .order_by(DailyStatistic.date, DailyStatistic.animal_type)
    )).all()
    if group == "day":
        return [HistoryRow(date=r.date, animal_type=r.animal_type, total_in=r.total_in,
                           total_out=r.total_out, net=r.total_in - r.total_out) for r in rows]

    buckets: dict[tuple[date, str], list[int]] = {}
    for row in rows:
        bucket = buckets.setdefault((_period_start(row.date, group), row.animal_type), [0, 0])
        bucket[0] += row.total_in
        bucket[1] += row.total_out
    return [
        HistoryRow(date=day, animal_type=animal, total_in=t_in, total_out=t_out, net=t_in - t_out)
        for (day, animal), (t_in, t_out) in sorted(buckets.items())
    ]
