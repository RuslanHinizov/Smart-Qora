from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.schemas import (
    InventoryBalanceRead, InventoryInitialise, InventoryMovementRead,
    InventoryReconcile, InventoryReconciliationRead, InventoryTransfer,
)
from app.db.database import get_session
from app.db.models import AnimalGroup, FarmZone, InventoryBalance, InventoryMovement, InventoryReconciliation, MovementKind, User
from app.services.inventory_service import apply_movement

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])
_admin = [Depends(require_admin)]


async def _require_zone_and_group(session: AsyncSession, zone_id: int, group_id: int) -> None:
    if await session.get(FarmZone, zone_id) is None:
        raise HTTPException(404, "Farm zone not found")
    if await session.get(AnimalGroup, group_id) is None:
        raise HTTPException(404, "Animal group not found")


@router.get("/summary", response_model=list[InventoryBalanceRead])
async def summary(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(InventoryBalance, FarmZone, AnimalGroup)
        .join(FarmZone, FarmZone.id == InventoryBalance.zone_id)
        .join(AnimalGroup, AnimalGroup.id == InventoryBalance.group_id)
        .order_by(FarmZone.sort_order, FarmZone.name, AnimalGroup.sort_order, AnimalGroup.name)
    )).all()
    return [InventoryBalanceRead(zone_id=balance.zone_id, zone_name=zone.name, group_id=balance.group_id,
                                 group_name=group.name, species=group.species, quantity=balance.quantity)
            for balance, zone, group in rows]


@router.get("/movements", response_model=list[InventoryMovementRead])
async def movements(limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_session)):
    return (await session.scalars(
        select(InventoryMovement).order_by(InventoryMovement.created_at.desc()).limit(limit)
    )).all()


@router.post("/initialise", response_model=list[InventoryMovementRead], status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def initialise(payload: InventoryInitialise, user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    if len({entry.group_id for entry in payload.entries}) != len(payload.entries):
        raise HTTPException(422, "Each animal group may appear only once")
    if await session.get(FarmZone, payload.zone_id) is None:
        raise HTTPException(404, "Farm zone not found")
    movements: list[InventoryMovement] = []
    for entry in payload.entries:
        if await session.get(AnimalGroup, entry.group_id) is None:
            raise HTTPException(404, "Animal group not found")
        existing = await session.get(InventoryBalance, (payload.zone_id, entry.group_id))
        if existing is not None:
            raise HTTPException(409, "Initial inventory already exists for this zone and group; use reconciliation")
        applied = await apply_movement(session, group_id=entry.group_id, to_zone_id=payload.zone_id,
                                       quantity=entry.quantity, kind=MovementKind.INITIAL,
                                       note=payload.note, created_by_user_id=user.id)
        movements.append(applied.movement)
    await session.commit()
    return movements


@router.post("/transfer", response_model=InventoryMovementRead, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def transfer(payload: InventoryTransfer, user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    for zone_id in (payload.from_zone_id, payload.to_zone_id):
        if zone_id is not None:
            await _require_zone_and_group(session, zone_id, payload.group_id)
    applied = await apply_movement(session, group_id=payload.group_id, from_zone_id=payload.from_zone_id,
                                   to_zone_id=payload.to_zone_id, quantity=payload.quantity,
                                   kind=MovementKind.TRANSFER, note=payload.note, created_by_user_id=user.id)
    await session.commit()
    return applied.movement


@router.post("/reconcile", response_model=InventoryReconciliationRead, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def reconcile(payload: InventoryReconcile, user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    await _require_zone_and_group(session, payload.zone_id, payload.group_id)
    balance = await session.get(InventoryBalance, (payload.zone_id, payload.group_id))
    expected = balance.quantity if balance is not None else 0
    difference = payload.physical_quantity - expected
    reconciliation = InventoryReconciliation(zone_id=payload.zone_id, group_id=payload.group_id,
                                             expected_quantity=expected, physical_quantity=payload.physical_quantity,
                                             difference=difference, note=payload.note, created_by_user_id=user.id)
    session.add(reconciliation)
    if difference:
        await apply_movement(session, group_id=payload.group_id,
                             from_zone_id=payload.zone_id if difference < 0 else None,
                             to_zone_id=payload.zone_id if difference > 0 else None,
                             quantity=abs(difference), kind=MovementKind.MANUAL_ADJUSTMENT,
                             note=payload.note, created_by_user_id=user.id)
    await session.commit()
    await session.refresh(reconciliation)
    return reconciliation
