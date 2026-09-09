import pytest


async def _zone(client, headers, name, kind):
    response = await client.post("/api/farm/zones", headers=headers, json={"name": name, "kind": kind})
    assert response.status_code == 201, response.text
    return response.json()


async def _group(client, headers, name, species):
    response = await client.post("/api/farm/groups", headers=headers, json={"name": name, "species": species})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_inventory_setup_transfer_and_reconciliation(client, clean_db, admin_token, auth):
    headers = auth(admin_token)
    pen = await _zone(client, headers, "Main Pen", "PEN")
    pasture = await _zone(client, headers, "Pasture", "PASTURE")
    sheep = await _group(client, headers, "Sheep", "sheep")
    cattle = await _group(client, headers, "Cattle", "cattle")

    initial = await client.post("/api/inventory/initialise", headers=headers, json={
        "zone_id": pen["id"], "entries": [
            {"group_id": sheep["id"], "quantity": 50},
            {"group_id": cattle["id"], "quantity": 40},
        ],
    })
    assert initial.status_code == 201, initial.text

    moved = await client.post("/api/inventory/transfer", headers=headers, json={
        "group_id": sheep["id"], "from_zone_id": pen["id"], "to_zone_id": pasture["id"],
        "quantity": 3, "note": "Morning pasture move",
    })
    assert moved.status_code == 201, moved.text

    summary = await client.get("/api/inventory/summary", headers=headers)
    values = {(row["zone_name"], row["group_name"]): row["quantity"] for row in summary.json()}
    assert values == {("Main Pen", "Sheep"): 47, ("Main Pen", "Cattle"): 40, ("Pasture", "Sheep"): 3}

    reconciled = await client.post("/api/inventory/reconcile", headers=headers, json={
        "zone_id": pen["id"], "group_id": sheep["id"], "physical_quantity": 46,
        "note": "Evening physical count",
    })
    assert reconciled.status_code == 201, reconciled.text
    assert reconciled.json()["difference"] == -1
    after = await client.get("/api/inventory/summary", headers=headers)
    after_values = {(row["zone_name"], row["group_name"]): row["quantity"] for row in after.json()}
    assert after_values[("Main Pen", "Sheep")] == 46

    movements = await client.get("/api/inventory/movements", headers=headers)
    assert [row["kind"] for row in movements.json()] == ["MANUAL_ADJUSTMENT", "TRANSFER", "INITIAL", "INITIAL"]


@pytest.mark.asyncio
async def test_inventory_rejects_overdraw_and_viewer_writes(client, clean_db, admin_token, viewer_token, auth):
    admin = auth(admin_token)
    viewer = auth(viewer_token)
    assert (await client.post("/api/farm/zones", headers=viewer, json={"name": "No", "kind": "PEN"})).status_code == 403
    pen = await _zone(client, admin, "Main Pen", "PEN")
    pasture = await _zone(client, admin, "Pasture", "PASTURE")
    sheep = await _group(client, admin, "Sheep", "sheep")
    await client.post("/api/inventory/initialise", headers=admin, json={
        "zone_id": pen["id"], "entries": [{"group_id": sheep["id"], "quantity": 2}],
    })
    overdraw = await client.post("/api/inventory/transfer", headers=admin, json={
        "group_id": sheep["id"], "from_zone_id": pen["id"], "to_zone_id": pasture["id"],
        "quantity": 3, "note": "Invalid move",
    })
    assert overdraw.status_code == 409


@pytest.mark.asyncio
async def test_apply_movement_is_idempotent_per_source_event(session, clean_db):
    """Plan acceptance: 'Aynı kamera olayı ikinci kez stok değiştiremez.'"""
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.db.models import (
        AnimalEvent, AnimalGroup, Direction, FarmZone, InventoryBalance, InventoryMovement, MovementKind, ZoneKind,
    )
    from app.db.seed import ensure_default_camera
    from app.services.inventory_service import apply_movement

    camera = await ensure_default_camera(session, get_settings())
    pen = FarmZone(name="Pen", kind=ZoneKind.PEN)
    outside = FarmZone(name="Outside", kind=ZoneKind.EXTERNAL)
    group = AnimalGroup(name="Sheep", species="sheep")
    event = AnimalEvent(camera_id=camera.id, animal_type="sheep", tracking_id=1,
                        direction=Direction.IN, confidence=0.9)
    session.add_all([pen, outside, group, event])
    await session.flush()

    for _ in range(2):
        await apply_movement(
            session, group_id=group.id, quantity=1, kind=MovementKind.CAMERA,
            from_zone_id=outside.id, to_zone_id=pen.id, source_event_id=event.id,
        )
    await session.commit()

    movements = (await session.scalars(select(InventoryMovement))).all()
    assert len(movements) == 1
    balance = await session.get(InventoryBalance, (pen.id, group.id))
    assert balance.quantity == 1  # the retry did not double-apply


@pytest.mark.asyncio
async def test_group_for_detection_resolution(session, clean_db):
    """Faz 2.2 — a species with two active groups (e.g. 'Sheep' and 'Lambs')
    is ambiguous unless one of them is marked as that species' default."""
    from app.db.models import AnimalGroup
    from app.services.inventory_service import group_for_detection

    assert await group_for_detection(session, "sheep") is None  # no group at all

    sheep = AnimalGroup(name="Sheep", species="sheep")
    session.add(sheep)
    await session.flush()
    assert (await group_for_detection(session, "sheep")).id == sheep.id  # sole active group

    lambs = AnimalGroup(name="Lambs", species="sheep")
    session.add(lambs)
    await session.flush()
    assert await group_for_detection(session, "sheep") is None  # now ambiguous

    lambs.is_default_for_species = True
    await session.flush()
    assert (await group_for_detection(session, "sheep")).id == lambs.id  # default breaks the tie


@pytest.mark.asyncio
async def test_group_default_species_conflict_is_409(client, clean_db, admin_token, auth):
    headers = auth(admin_token)
    await _group(client, headers, "Sheep", "sheep")
    default = await client.post("/api/farm/groups", headers=headers,
                                json={"name": "Lambs", "species": "sheep", "is_default_for_species": True})
    assert default.status_code == 201, default.text

    conflict = await client.post("/api/farm/groups", headers=headers,
                                 json={"name": "Rams", "species": "sheep", "is_default_for_species": True})
    assert conflict.status_code == 409, conflict.text

    # a different species may have its own default at the same time
    other = await client.post("/api/farm/groups", headers=headers,
                              json={"name": "Cattle", "species": "cattle", "is_default_for_species": True})
    assert other.status_code == 201, other.text
