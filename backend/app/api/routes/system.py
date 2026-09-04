import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text

from app.api.deps import get_current_user, require_admin
from app.core.i18n import SUPPORTED_LANGUAGES
from app.db.database import SessionLocal

router = APIRouter(tags=["system"])

_FRAME_STALE_SECONDS = 30.0


async def _db_ok() -> bool:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@router.get("/health")
async def health(request: Request):
    """Liveness: always 200 while the process serves; carries a quick diagnostic payload."""
    supervisor = getattr(request.app.state, "supervisor", None)
    return {
        "status": "ok",
        "db": await _db_ok(),
        "worker": supervisor.state if supervisor else "stopped",
    }


@router.get("/status", dependencies=[Depends(get_current_user)])
async def system_status(request: Request):
    supervisor = getattr(request.app.state, "supervisor", None)
    return {
        "camera": supervisor.camera_status if supervisor else "OFFLINE",
        "ai": "ACTIVE" if supervisor and supervisor.running else "IDLE",
        "worker": supervisor.state if supervisor else "stopped",
        "restarts": supervisor.restarts if supervisor else 0,
        "last_error": supervisor.last_error if supervisor else None,
        "languages": list(SUPPORTED_LANGUAGES),
    }


@router.get("/ready")
async def ready(response: Response, request: Request):
    checks = {"db": await _db_ok(), "worker": False}

    supervisor = getattr(request.app.state, "supervisor", None)
    if supervisor is None:
        checks["worker"] = True  # no model configured on this box; not a readiness failure
    else:
        fresh = supervisor.last_frame_at is not None and time.time() - supervisor.last_frame_at < _FRAME_STALE_SECONDS
        checks["worker"] = supervisor.state in {"running", "stopped"} and (supervisor.state == "stopped" or fresh)

    if not all(checks.values()):
        response.status_code = 503
    return {"ready": all(checks.values()), "checks": checks}


@router.get("/worker", dependencies=[Depends(get_current_user)])
async def worker_info(request: Request):
    supervisor = getattr(request.app.state, "supervisor", None)
    if supervisor is None:
        return {"state": "stopped", "restarts": 0, "last_error": None, "camera": "OFFLINE"}
    return {
        "state": supervisor.state,
        "restarts": supervisor.restarts,
        "last_error": supervisor.last_error,
        "camera": supervisor.camera_status,
    }


@router.post("/worker/restart", dependencies=[Depends(require_admin)])
async def worker_restart(request: Request):
    supervisor = getattr(request.app.state, "supervisor", None)
    if supervisor is None:
        raise HTTPException(status_code=409, detail="No vision worker is running")
    supervisor.request_restart()
    return {"restarting": True}


@router.get("/video")
async def source_video():
    raise HTTPException(status_code=410, detail="Removed — use /api/stream/mjpeg or /api/stream/snapshot")
