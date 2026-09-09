import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import AnimalGroup, FarmZone
from app.db.seed import ensure_default_camera, ensure_default_farm


@pytest.mark.asyncio
async def test_ensure_default_farm_seeds_zones_groups_and_links_the_camera(session, clean_db):
    """Faz 2.4 — a fresh box must not present an empty Dashboard/Farm page,
    and the bootstrap camera should already be wired to zones."""
    camera = await ensure_default_camera(session, get_settings())
    await ensure_default_farm(session, camera)

    zones = {z.name: z for z in (await session.scalars(select(FarmZone))).all()}
    groups = {g.species for g in (await session.scalars(select(AnimalGroup))).all()}
    assert {"Outside", "Main Pen", "Pasture"} <= zones.keys()
    assert {"sheep", "cattle", "goat", "horse"} <= groups

    await session.refresh(camera)
    assert camera.inside_zone_id == zones["Main Pen"].id
    assert camera.outside_zone_id == zones["Outside"].id


@pytest.mark.asyncio
async def test_ensure_default_farm_is_idempotent_and_does_not_touch_a_configured_camera(session, clean_db):
    """Seeding must run at most once: a restart after zones already exist
    must neither duplicate them nor override a zone link an admin has since
    changed on the camera (even clearing it back to unlinked)."""
    camera = await ensure_default_camera(session, get_settings())
    await ensure_default_farm(session, camera)
    zone_count_first = len((await session.scalars(select(FarmZone))).all())

    camera.inside_zone_id = None
    camera.outside_zone_id = None
    await session.commit()

    await ensure_default_farm(session, camera)
    await session.refresh(camera)
    zone_count_second = len((await session.scalars(select(FarmZone))).all())
    assert zone_count_second == zone_count_first
    assert camera.inside_zone_id is None and camera.outside_zone_id is None
