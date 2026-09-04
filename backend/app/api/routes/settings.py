from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.schemas import HerdCalibrate, SettingsRead, SettingsUpdate
from app.db.database import get_session
from app.db.models import AppSettings, HerdState

router = APIRouter(tags=["settings"])


async def _get_settings_row(session: AsyncSession) -> AppSettings:
    row = await session.get(AppSettings, 1)
    if row is None:  # defensive: migration 0003 seeds it
        row = AppSettings(id=1)
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


@router.get("/settings", response_model=SettingsRead, dependencies=[Depends(get_current_user)])
async def read_settings(session: AsyncSession = Depends(get_session)):
    row = await _get_settings_row(session)
    return SettingsRead(
        default_language=row.default_language,
        telegram_configured=bool(row.telegram_bot_token and row.telegram_chat_id),
        telegram_aggregation_seconds=row.telegram_aggregation_seconds,
        default_confidence=row.default_confidence,
        default_iou=row.default_iou,
        default_frame_skip=row.default_frame_skip,
        stream_fps=row.stream_fps,
    )


@router.put("/settings", response_model=SettingsRead, dependencies=[Depends(require_admin)])
async def update_settings(payload: SettingsUpdate, session: AsyncSession = Depends(get_session)):
    row = await _get_settings_row(session)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await session.commit()
    return await read_settings(session)


@router.post("/herd/calibrate", dependencies=[Depends(require_admin)])
async def calibrate_herd(payload: HerdCalibrate, session: AsyncSession = Depends(get_session)):
    await session.execute(update(HerdState).where(HerdState.id == 1).values(current_inside=payload.current_inside))
    await session.commit()
    return {"current_inside": payload.current_inside}
