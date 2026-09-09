"""The camera -> inventory path (docs/FARM-INVENTORY-COMPLETION-PLAN.md, Faz 1).

test_inventory.py covers the API-driven zone/group/transfer/reconcile flow;
this file covers the path nothing else touches: a real crossing produced by
CountingService actually moving stock between farm zones (or correctly
refusing to, with an alert).
"""
import asyncio

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.db.models import (
    AnimalGroup, FarmZone, InventoryBalance, InventoryMovement, LineDirection, MovementKind, ZoneKind,
)
from app.db.seed import ensure_default_camera
from app.services import counting_service as cs
from app.telegram.notifications import notifier
from fakes import FakeCameraStream, FakeDetector, straight_crossing_script

NAMES = {0: "sheep"}


async def _farm(outside_kind: ZoneKind = ZoneKind.EXTERNAL) -> tuple[int, int, int]:
    async with SessionLocal() as db:
        pen = FarmZone(name="Main Pen", kind=ZoneKind.PEN)
        outside = FarmZone(name="Outside", kind=outside_kind)
        group = AnimalGroup(name="Sheep", species="sheep")
        db.add_all([pen, outside, group])
        await db.flush()
        pen_id, outside_id, group_id = pen.id, outside.id, group.id
        await db.commit()
    return pen_id, outside_id, group_id


async def _camera_with_zones(inside_zone_id: int | None, outside_zone_id: int | None) -> None:
    async with SessionLocal() as db:
        camera = await ensure_default_camera(db, get_settings())
        camera.source = "fake"
        camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y = 0, 50, 100, 50
        camera.inside_direction = LineDirection.DOWN
        camera.confidence = 0.1
        camera.frame_skip = 0
        camera.inside_zone_id = inside_zone_id
        camera.outside_zone_id = outside_zone_id
        await db.commit()


def _install_fakes(monkeypatch, script):
    monkeypatch.setattr(cs, "CameraStream", lambda source: FakeCameraStream(source, len(script)))
    monkeypatch.setattr(cs, "LivestockDetector", lambda *a, **k: FakeDetector(script, NAMES))


@pytest.mark.asyncio
async def test_in_crossing_draws_from_an_external_zone_with_no_recorded_stock(monkeypatch, clean_db):
    """Faz 1.1 — the common fresh-setup case: only the pen's starting count was
    entered; the outside zone has never been counted (quantity 0). The first IN
    crossing must still move the animal instead of being rejected as insufficient
    stock, and the pen + outside totals must both change by the same amount."""
    pen_id, outside_id, _ = await _farm()
    await _camera_with_zones(pen_id, outside_id)
    service = cs.CountingService(get_settings())
    _install_fakes(monkeypatch, straight_crossing_script(track_id=1, cls_index=0))
    await service.run()

    async with SessionLocal() as db:
        balances = {row.zone_id: row.quantity for row in (await db.scalars(select(InventoryBalance))).all()}
        assert balances[pen_id] == 1
        assert balances[outside_id] == -1  # net animals brought in from outside the farm
        movements = (await db.scalars(select(InventoryMovement))).all()
        assert len(movements) == 1
        assert movements[0].kind == MovementKind.CAMERA
        assert movements[0].from_zone_id == outside_id and movements[0].to_zone_id == pen_id
    assert service.inventory_health == "ok"


@pytest.mark.asyncio
async def test_camera_without_zones_configured_leaves_inventory_untouched(monkeypatch, clean_db):
    """Plan acceptance criterion: 'Kamera bağlantısı eksikken otomatik stok
    değişmez' — the crossing is still counted, the farm inventory is not."""
    await _camera_with_zones(None, None)
    service = cs.CountingService(get_settings())
    _install_fakes(monkeypatch, straight_crossing_script(track_id=1, cls_index=0))
    await service.run()

    async with SessionLocal() as db:
        assert (await db.scalars(select(InventoryBalance))).all() == []
        assert (await db.scalars(select(InventoryMovement))).all() == []
    assert service.inventory_health == "ok"


@pytest.mark.asyncio
async def test_insufficient_pasture_stock_skips_movement_without_a_phantom_balance(monkeypatch, clean_db):
    """Faz 1.1 boundary + 1.5: a non-EXTERNAL source zone still enforces the
    non-negative rule, and a rejected movement must not leave behind a
    zero-quantity balance row (the worker path commits even after catching
    the rejection, so a naive create-then-check would leak one)."""
    pen_id, pasture_id, _ = await _farm(outside_kind=ZoneKind.PASTURE)
    await _camera_with_zones(pen_id, pasture_id)
    service = cs.CountingService(get_settings())
    _install_fakes(monkeypatch, straight_crossing_script(track_id=1, cls_index=0))
    await service.run()

    async with SessionLocal() as db:
        assert (await db.scalars(select(InventoryBalance))).all() == []
        assert (await db.scalars(select(InventoryMovement))).all() == []
    assert service.inventory_health == "mismatch"


@pytest.mark.asyncio
async def test_inventory_mismatch_sends_one_rate_limited_telegram_alert(monkeypatch, clean_db):
    """Faz 1.4: a persistent inventory problem must reach an operator, but a
    burst of crossings collapses into a single message instead of flooding."""
    pen_id, pasture_id, _ = await _farm(outside_kind=ZoneKind.PASTURE)
    await _camera_with_zones(pen_id, pasture_id)

    sent: list[tuple[str, str]] = []

    async def fake_send(chat_id, text):
        sent.append((chat_id, text))

    async def recipients():
        return [("10", "en")]

    notifier.configure(0, fake_send, recipients)
    try:
        script = straight_crossing_script(track_id=1, cls_index=0) + straight_crossing_script(track_id=2, cls_index=0)
        _install_fakes(monkeypatch, script)
        await cs.CountingService(get_settings()).run()
        await asyncio.sleep(0.05)
    finally:
        notifier.configure(0, None, recipients)

    # Each crossing still fires its own aggregated "ENTERED" notification (that
    # path is unrelated and already covered by test_telegram_wiring.py); what
    # matters here is the inventory-mismatch alert specifically, which must
    # collapse the two failed movements into a single message.
    mismatch_alerts = [text for _, text in sent if "Physical verification" in text]
    assert len(mismatch_alerts) == 1
    assert "'Outside'" in mismatch_alerts[0]


@pytest.mark.asyncio
async def test_default_group_resolves_a_species_shared_by_two_groups(monkeypatch, clean_db):
    """Faz 2.2 — 'Sheep' and 'Lambs' both have species=sheep; without a marked
    default the crossing would be unconfigured (see the previous test)."""
    pen_id, outside_id, adults_group_id = await _farm()
    async with SessionLocal() as db:
        db.add(AnimalGroup(name="Lambs", species="sheep", is_default_for_species=True))
        await db.commit()
    await _camera_with_zones(pen_id, outside_id)
    service = cs.CountingService(get_settings())
    _install_fakes(monkeypatch, straight_crossing_script(track_id=1, cls_index=0))
    await service.run()

    async with SessionLocal() as db:
        movement = (await db.scalars(select(InventoryMovement))).one()
        lambs_id = await db.scalar(select(AnimalGroup.id).where(AnimalGroup.name == "Lambs"))
        assert movement.group_id == lambs_id
        assert movement.group_id != adults_group_id  # the non-default group was not picked
    assert service.inventory_health == "ok"
