from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.schemas import CameraCreate, CameraRead
from app.core.config import get_settings
from app.core.i18n import normalize_language, translate
from app.db.database import get_session
from app.db.models import Camera

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_user)])
_admin = [Depends(require_admin)]


def lang(request: Request):
    return normalize_language(request.query_params.get("lang") or request.headers.get("accept-language"), get_settings().default_language)


@router.get("", response_model=list[CameraRead])
async def list_cameras(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(Camera).order_by(Camera.id))).all()


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def create_camera(payload: CameraCreate, session: AsyncSession = Depends(get_session)):
    camera = Camera(**payload.model_dump())
    session.add(camera); await session.commit(); await session.refresh(camera)
    return camera


async def camera_or_404(camera_id: int, request: Request, session: AsyncSession):
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(404, translate("not_found", lang(request)))
    return camera


@router.put("/{camera_id}", response_model=CameraRead, dependencies=_admin)
async def update_camera(camera_id: int, payload: CameraCreate, request: Request, session: AsyncSession = Depends(get_session)):
    camera = await camera_or_404(camera_id, request, session)
    for key, value in payload.model_dump().items(): setattr(camera, key, value)
    await session.commit(); await session.refresh(camera)
    active_id = await session.scalar(select(Camera.id).order_by(Camera.id).limit(1))
    supervisor = getattr(request.app.state, "supervisor", None)
    if supervisor is not None and active_id == camera_id:
        supervisor.request_restart()
    return camera


@router.delete("/{camera_id}", status_code=204, dependencies=_admin)
async def delete_camera(camera_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    camera = await camera_or_404(camera_id, request, session)
    await session.delete(camera); await session.commit()
