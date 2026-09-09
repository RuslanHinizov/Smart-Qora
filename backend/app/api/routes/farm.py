from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.schemas import AnimalGroupCreate, AnimalGroupRead, FarmZoneCreate, FarmZoneRead
from app.db.database import get_session
from app.db.models import AnimalGroup, FarmZone

router = APIRouter(prefix="/farm", tags=["farm"], dependencies=[Depends(get_current_user)])
_admin = [Depends(require_admin)]


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "A zone or group with this name already exists") from None


async def _reject_default_species_conflict(
    session: AsyncSession, payload: AnimalGroupCreate, group_id: int | None
) -> None:
    """A proactive check ahead of the DB's partial unique index, so the 409
    names the actual conflict instead of the generic name-clash message."""
    if not payload.is_default_for_species:
        return
    query = select(AnimalGroup.id).where(
        AnimalGroup.species == payload.species, AnimalGroup.is_default_for_species.is_(True),
    )
    if group_id is not None:
        query = query.where(AnimalGroup.id != group_id)
    if await session.scalar(query) is not None:
        raise HTTPException(409, f"Another group is already the default for species '{payload.species}'")


@router.get("/zones", response_model=list[FarmZoneRead])
async def list_zones(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(FarmZone).order_by(FarmZone.sort_order, FarmZone.name))).all()


@router.post("/zones", response_model=FarmZoneRead, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def create_zone(payload: FarmZoneCreate, session: AsyncSession = Depends(get_session)):
    zone = FarmZone(**payload.model_dump())
    session.add(zone)
    await _commit(session)
    await session.refresh(zone)
    return zone


@router.put("/zones/{zone_id}", response_model=FarmZoneRead, dependencies=_admin)
async def update_zone(zone_id: int, payload: FarmZoneCreate, session: AsyncSession = Depends(get_session)):
    zone = await session.get(FarmZone, zone_id)
    if zone is None:
        raise HTTPException(404, "Farm zone not found")
    for key, value in payload.model_dump().items():
        setattr(zone, key, value)
    await _commit(session)
    await session.refresh(zone)
    return zone


@router.get("/groups", response_model=list[AnimalGroupRead])
async def list_groups(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(AnimalGroup).order_by(AnimalGroup.sort_order, AnimalGroup.name))).all()


@router.post("/groups", response_model=AnimalGroupRead, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def create_group(payload: AnimalGroupCreate, session: AsyncSession = Depends(get_session)):
    await _reject_default_species_conflict(session, payload, group_id=None)
    group = AnimalGroup(**payload.model_dump())
    session.add(group)
    await _commit(session)
    await session.refresh(group)
    return group


@router.put("/groups/{group_id}", response_model=AnimalGroupRead, dependencies=_admin)
async def update_group(group_id: int, payload: AnimalGroupCreate, session: AsyncSession = Depends(get_session)):
    group = await session.get(AnimalGroup, group_id)
    if group is None:
        raise HTTPException(404, "Animal group not found")
    await _reject_default_species_conflict(session, payload, group_id=group_id)
    for key, value in payload.model_dump().items():
        setattr(group, key, value)
    await _commit(session)
    await session.refresh(group)
    return group
