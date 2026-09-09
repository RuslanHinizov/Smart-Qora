"""Idempotent first-boot seeding: the default camera row and the admin user."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import AnimalGroup, Camera, FarmZone, LineDirection, Role, User, ZoneKind

logger = logging.getLogger(__name__)


async def ensure_default_camera(session: AsyncSession, settings: Settings) -> Camera:
    camera = await session.scalar(select(Camera).order_by(Camera.id).limit(1))
    if camera is not None:
        return camera
    (p1x, p1y), (p2x, p2y) = settings.count_line
    l2 = settings.count_line2_pts
    camera = Camera(
        name=settings.default_camera_name,
        source=settings.default_camera_source or str(settings.video_source),
        line_p1_x=p1x, line_p1_y=p1y, line_p2_x=p2x, line_p2_y=p2y,
        line2_p1_x=l2[0][0] if l2 else None, line2_p1_y=l2[0][1] if l2 else None,
        line2_p2_x=l2[1][0] if l2 else None, line2_p2_y=l2[1][1] if l2 else None,
        inside_direction=LineDirection(settings.inside_direction),
        frame_skip=settings.frame_skip, stream_fps=settings.stream_fps,
    )
    session.add(camera)
    await session.commit()
    await session.refresh(camera)
    logger.info("default_camera_seeded", extra={"camera_id": camera.id})
    return camera


async def ensure_default_farm(session: AsyncSession, camera: Camera | None = None) -> None:
    """First-boot only: seed a starter set of farm zones + animal groups so a
    fresh box has something to link the default camera to and the Dashboard
    and Farm page aren't empty. Starting quantities are deliberately NOT
    seeded here — the admin enters those from the Farm page (step 3), since
    only they know the real headcount."""
    if await session.scalar(select(FarmZone.id).limit(1)) is not None:
        return
    outside = FarmZone(name="Outside", kind=ZoneKind.EXTERNAL, sort_order=0)
    pen = FarmZone(name="Main Pen", kind=ZoneKind.PEN, sort_order=1)
    pasture = FarmZone(name="Pasture", kind=ZoneKind.PASTURE, sort_order=2)
    session.add_all([
        outside, pen, pasture,
        AnimalGroup(name="Sheep", species="sheep", sort_order=0),
        AnimalGroup(name="Cattle", species="cattle", sort_order=1),
        AnimalGroup(name="Goats", species="goat", sort_order=2),
        AnimalGroup(name="Horses", species="horse", sort_order=3),
    ])
    await session.flush()
    if camera is not None and camera.inside_zone_id is None and camera.outside_zone_id is None:
        camera.inside_zone_id = pen.id
        camera.outside_zone_id = outside.id
    await session.commit()
    logger.info("default_farm_seeded")


async def ensure_admin(session: AsyncSession, settings: Settings) -> None:
    exists = await session.scalar(select(User.id).limit(1))
    if exists is not None:
        return
    session.add(User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        role=Role.admin,
    ))
    await session.commit()
    logger.info("admin_user_seeded", extra={"username": settings.admin_username})
