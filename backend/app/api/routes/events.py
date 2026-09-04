from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import EventRead
from app.db.database import get_session
from app.db.models import AnimalEvent, Direction

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[EventRead])
async def list_events(
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    camera_id: int | None = None,
    direction: Direction | None = None,
    animal_type: str | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
    session: AsyncSession = Depends(get_session),
):
    filters = []
    if camera_id is not None:
        filters.append(AnimalEvent.camera_id == camera_id)
    if direction is not None:
        filters.append(AnimalEvent.direction == direction)
    if animal_type:
        filters.append(AnimalEvent.animal_type == animal_type)
    if from_ is not None:
        filters.append(AnimalEvent.timestamp >= from_)
    if to is not None:
        filters.append(AnimalEvent.timestamp <= to)

    total = await session.scalar(select(func.count()).select_from(AnimalEvent).where(*filters))
    response.headers["X-Total-Count"] = str(total or 0)
    query = (select(AnimalEvent).where(*filters)
             .order_by(AnimalEvent.timestamp.desc()).limit(limit).offset(offset))
    return (await session.scalars(query)).all()
