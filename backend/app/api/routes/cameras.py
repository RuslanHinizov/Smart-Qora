from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.schemas import CameraCreate, CameraRead, mask_credentials
from app.core.config import get_settings
from app.core.i18n import normalize_language, translate
from app.db.database import get_session
from app.db.models import Camera, AnimalEvent, RecordingProgress
from app.services.frame_bus import frame_bus

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_user)])
_admin = [Depends(require_admin)]


def restart_camera(request):
    frame_bus.clear()
    supervisor = getattr(request.app.state, "supervisor", None)
    if supervisor is not None:
        supervisor.request_restart()


async def commit_camera(session):
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Camera configuration changed concurrently; reload and retry") from None


def lang(request: Request):
    return normalize_language(request.query_params.get("lang") or request.headers.get("accept-language"), get_settings().default_language)


@router.get("", response_model=list[CameraRead])
async def list_cameras(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(Camera).order_by(Camera.id))).all()


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def create_camera(payload: CameraCreate, request: Request, session: AsyncSession = Depends(get_session)):
    if "***" in payload.source:
        raise HTTPException(422, "Enter actual camera credentials for a new source")
    if payload.is_active:
        await session.execute(update(Camera).values(is_active=False))
    camera = Camera(**payload.model_dump())
    session.add(camera); await commit_camera(session); await session.refresh(camera)
    if camera.is_active:
        restart_camera(request)
    return camera


async def camera_or_404(camera_id: int, request: Request, session: AsyncSession):
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(404, translate("not_found", lang(request)))
    return camera


@router.put("/{camera_id}", response_model=CameraRead, dependencies=_admin)
async def update_camera(camera_id: int, payload: CameraCreate, request: Request, session: AsyncSession = Depends(get_session)):
    camera = await camera_or_404(camera_id, request, session)
    was_active = camera.is_active
    changed = payload.model_dump()
    if changed["source"] == mask_credentials(camera.source):
        changed["source"] = camera.source
    elif "***" in changed["source"]:
        raise HTTPException(422, "Enter credentials when changing the camera source")
    if payload.is_active:
        await session.execute(update(Camera).where(Camera.id != camera_id).values(is_active=False))
    for key, value in changed.items(): setattr(camera, key, value)
    await commit_camera(session); await session.refresh(camera)
    if was_active or camera.is_active:
        restart_camera(request)
    return camera


@router.delete("/{camera_id}", status_code=204, dependencies=_admin)
async def delete_camera(camera_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    camera = await camera_or_404(camera_id, request, session)
    if await session.scalar(select(AnimalEvent.id).where(AnimalEvent.camera_id == camera_id).limit(1)):
        raise HTTPException(409, "This camera has counting history. Deactivate it to preserve the records.")
    was_active = camera.is_active
    await session.execute(delete(RecordingProgress).where(RecordingProgress.camera_id == camera_id))
    await session.delete(camera); await session.commit()
    if was_active:
        restart_camera(request)
