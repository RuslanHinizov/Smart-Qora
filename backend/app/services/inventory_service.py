"""Atomic, auditable zone inventory operations."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnimalGroup, FarmZone, InventoryBalance, InventoryMovement, MovementKind, ZoneKind
from app.vision.classes import canonical


@dataclass(frozen=True)
class AppliedMovement:
    movement: InventoryMovement
    duplicate: bool = False


async def _locked_balance(
    session: AsyncSession, zone_id: int, group_id: int, *, create: bool = True
) -> InventoryBalance | None:
    balance = await session.scalar(
        select(InventoryBalance)
        .where(InventoryBalance.zone_id == zone_id, InventoryBalance.group_id == group_id)
        .with_for_update()
    )
    if balance is None and create:
        balance = InventoryBalance(zone_id=zone_id, group_id=group_id, quantity=0)
        session.add(balance)
        await session.flush()
    return balance


async def apply_movement(
    session: AsyncSession,
    *,
    group_id: int,
    quantity: int,
    kind: MovementKind,
    from_zone_id: int | None = None,
    to_zone_id: int | None = None,
    source_event_id: int | None = None,
    note: str = "",
    created_by_user_id: int | None = None,
) -> AppliedMovement:
    """Apply one movement and its balances in the caller's transaction.

    A source zone of kind ``EXTERNAL`` (the farm boundary) is exempt from the
    non-negative check: the real number of animals outside the farm is never
    tracked, so a fresh setup with only the pen's starting count entered must
    still be able to record the first camera ``IN``. Its balance is allowed
    to go negative; that number simply reads as "net animals brought in from
    outside" rather than a real headcount.
    """
    if quantity <= 0:
        raise HTTPException(422, "Quantity must be greater than zero")
    if from_zone_id is None and to_zone_id is None:
        raise HTTPException(422, "Choose a source or destination zone")
    if from_zone_id == to_zone_id and from_zone_id is not None:
        raise HTTPException(422, "Source and destination zones must differ")
    if source_event_id is not None:
        existing = await session.scalar(
            select(InventoryMovement).where(InventoryMovement.source_event_id == source_event_id)
        )
        if existing is not None:
            return AppliedMovement(existing, duplicate=True)

    if from_zone_id is not None:
        # Look, don't create: a failed check must not leave a phantom zero-quantity
        # balance row behind (the worker path commits even after catching this).
        source = await _locked_balance(session, from_zone_id, group_id, create=False)
        current_quantity = source.quantity if source is not None else 0
        source_zone = await session.get(FarmZone, from_zone_id)
        unlimited_source = source_zone is not None and source_zone.kind is ZoneKind.EXTERNAL
        if not unlimited_source and current_quantity < quantity:
            raise HTTPException(409, "Insufficient animals in the source zone; physical verification required")
        if source is None:
            source = await _locked_balance(session, from_zone_id, group_id)
        source.quantity -= quantity
    if to_zone_id is not None:
        destination = await _locked_balance(session, to_zone_id, group_id)
        destination.quantity += quantity

    movement = InventoryMovement(
        group_id=group_id, from_zone_id=from_zone_id, to_zone_id=to_zone_id,
        quantity=quantity, kind=kind, source_event_id=source_event_id,
        note=note.strip(), created_by_user_id=created_by_user_id,
    )
    session.add(movement)
    await session.flush()
    return AppliedMovement(movement)


async def group_for_detection(session: AsyncSession, animal_type: str) -> AnimalGroup | None:
    """Resolve a detector label only when exactly one active group owns that species."""
    species = canonical(animal_type)
    if species is None:
        return None
    groups = (await session.scalars(
        select(AnimalGroup).where(AnimalGroup.is_active, AnimalGroup.species == species)
    )).all()
    return groups[0] if len(groups) == 1 else None
