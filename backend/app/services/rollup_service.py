"""O(1) statistics: an in-memory running total plus incremental DB rollups.

Replaces the per-event full-table ``SUM(CASE ...)`` aggregate. ``seed_running_totals``
runs once when the worker starts; every crossing then updates memory and upserts a
single ``daily_statistics`` row + the ``herd_state`` singleton in the event's transaction.
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import engine
from app.db.models import AnimalEvent, DailyStatistic, HerdState


@dataclass
class RunningTotals:
    total_in: int = 0
    total_out: int = 0
    per_type_in: dict[str, int] = field(default_factory=dict)
    per_type_out: dict[str, int] = field(default_factory=dict)

    def apply(self, direction: str, animal_type: str) -> None:
        if direction == "IN":
            self.total_in += 1
            self.per_type_in[animal_type] = self.per_type_in.get(animal_type, 0) + 1
        else:
            self.total_out += 1
            self.per_type_out[animal_type] = self.per_type_out.get(animal_type, 0) + 1


async def seed_running_totals(session: AsyncSession) -> RunningTotals:
    rows = (await session.execute(
        select(AnimalEvent.animal_type, AnimalEvent.direction, func.count())
        .group_by(AnimalEvent.animal_type, AnimalEvent.direction)
    )).all()
    totals = RunningTotals()
    for animal_type, direction, count in rows:
        value = direction.value if hasattr(direction, "value") else str(direction)
        if value == "IN":
            totals.total_in += count
            totals.per_type_in[animal_type] = count
        else:
            totals.total_out += count
            totals.per_type_out[animal_type] = count
    return totals


def _insert():
    if engine.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert


async def upsert_daily(session: AsyncSession, day: date, animal_type: str, d_in: int, d_out: int) -> None:
    insert = _insert()
    stmt = insert(DailyStatistic).values(
        date=day, animal_type=animal_type, total_in=d_in, total_out=d_out, current_count=d_in - d_out,
    ).on_conflict_do_update(
        index_elements=["date", "animal_type"],
        set_={
            "total_in": DailyStatistic.total_in + d_in,
            "total_out": DailyStatistic.total_out + d_out,
            "current_count": DailyStatistic.current_count + (d_in - d_out),
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)


async def bump_herd_state(session: AsyncSession, delta: int) -> int:
    await session.execute(
        update(HerdState).where(HerdState.id == 1)
        .values(current_inside=HerdState.current_inside + delta, updated_at=func.now())
    )
    return await session.scalar(select(HerdState.current_inside).where(HerdState.id == 1))
