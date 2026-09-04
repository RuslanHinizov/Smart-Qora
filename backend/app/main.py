from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

import jwt
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import AccessLogMiddleware
from app.api.routes import (
    auth, cameras, events, settings as settings_routes, statistics, stream, system,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import decode_token
from app.db.database import SessionLocal
from app.db.seed import ensure_admin, ensure_default_camera
from app.services.websocket_manager import websockets
from app.services.worker_supervisor import WorkerSupervisor
from app.telegram.bot import command_bot
from app.telegram.runtime import apply_telegram_config

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if int(os.getenv("WEB_CONCURRENCY", "1")) != 1:
        logger.critical("multiple_web_workers_unsupported: the in-process vision worker and "
                        "WebSocket broadcaster require WEB_CONCURRENCY=1")
    async with SessionLocal() as session:
        await ensure_admin(session, settings)
        await ensure_default_camera(session, settings)

    await apply_telegram_config()

    supervisor = None
    app.state.supervisor = None
    if Path(settings.model_path).exists():
        supervisor = WorkerSupervisor(settings)
        app.state.supervisor = supervisor
        supervisor.start()
    else:
        logger.warning("vision_worker_not_started", extra={"model_path": settings.model_path})
    yield
    if supervisor is not None:
        await supervisor.stop()
    await command_bot.stop()
    app.state.supervisor = None


app = FastAPI(title="Smart Qora API", version="0.1.0", lifespan=lifespan)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["X-Request-ID", "X-Total-Count"])
for router in (system.router, auth.router, settings_routes.router, cameras.router, events.router,
               statistics.router, stream.router):
    app.include_router(router, prefix="/api")


@app.websocket("/ws/live")
async def live(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        int(decode_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websockets.connect(websocket)
    try:
        await websocket.send_json(await _initial_state(websocket.app))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websockets.disconnect(websocket)


async def _initial_state(app: FastAPI) -> dict:
    from app.services.statistics_service import today_totals
    async with SessionLocal() as session:
        totals = await today_totals(session)
    supervisor = getattr(app.state, "supervisor", None)
    return {
        "type": "statistics",
        "in": totals["total_in"], "out": totals["total_out"], "current": totals["current"],
        "camera": supervisor.camera_status if supervisor else "OFFLINE",
        "ai": "ACTIVE" if supervisor and supervisor.running else "IDLE",
    }
