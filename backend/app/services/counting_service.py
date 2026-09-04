import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import AnimalEvent, Direction, HerdState
from app.db.seed import ensure_default_camera
from app.services.frame_bus import frame_bus
from app.services.rollup_service import RunningTotals, bump_herd_state, seed_running_totals, upsert_daily
from app.services.websocket_manager import websockets
from app.telegram.notifications import notifier
from app.vision.annotator import annotate_jpeg
from app.vision.camera import CameraStream
from app.vision.classes import canonical
from app.vision.counter import CrossingEvent, LineCrossingCounter
from app.vision.detector import LivestockDetector
from app.vision.tracker import CenterSmoother

logger = logging.getLogger(__name__)


class CountingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.camera_id = 1
        self.camera_name = ""
        self.stream: CameraStream | None = None
        self.counter: LineCrossingCounter | None = None
        self.smoother = CenterSmoother()
        self.detector = None
        self.totals = RunningTotals()
        self.current_inside = 0
        self.line: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0))
        self.running = False
        self.last_frame_at: float | None = None

    async def run(self) -> None:
        self.running = True
        try:
            async with SessionLocal() as session:
                camera = await ensure_default_camera(session, self.settings)
                self.camera_id = camera.id
                self.camera_name = camera.name
                self.totals = await seed_running_totals(session)
                self.current_inside = await session.scalar(
                    select(HerdState.current_inside).where(HerdState.id == 1)) or 0

            source = camera.source or str(self.settings.video_source)
            source = int(source) if source.isdigit() else source
            (p1, p2), inside = self._resolve_line(camera)
            self.line = (p1, p2)
            stream_fps = max(camera.stream_fps or self.settings.stream_fps, 1)
            confidence = camera.confidence if camera.confidence is not None else self.settings.confidence
            iou = camera.iou if camera.iou is not None else self.settings.iou
            frame_skip = camera.frame_skip or self.settings.frame_skip

            self.detector = await asyncio.to_thread(
                LivestockDetector, self.settings.model_path, self.settings.device, confidence, iou,
                self.settings.img_size, self.settings.tracker, self.settings.allowed_classes,
                self.settings.require_cuda, self.settings.half_precision,
            )

            is_file = isinstance(source, str) and Path(source).is_file()
            loop_file = is_file and self.settings.video_loop
            frame_number = 0
            last_publish = 0.0
            while self.running:
                # Fresh counting session each pass so a looped recording does not
                # inflate totals (same animals, same crossing_sequence -> deduped).
                self.stream = CameraStream(source)
                self.counter = LineCrossingCounter(
                    p1, p2, inside,
                    min_track_updates=self.settings.count_min_track_updates,
                    entry_zone=self.settings.count_entry_zone_rect,
                )
                self.smoother = CenterSmoother()
                self.detector.reset_tracker()
                async for frame in self.stream.frames():
                    if not self.running:
                        break
                    frame_number += 1
                    self.last_frame_at = time.time()
                    if frame_number % (frame_skip + 1):
                        continue
                    result = await asyncio.to_thread(self.detector.track, frame)
                    if result.boxes is not None:
                        for box in result.boxes:
                            if box.id is None:
                                continue
                            track_id = int(box.id.item())
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            center = self.smoother.update(track_id, ((x1 + x2) // 2, (y1 + y2) // 2))
                            crossing = self.counter.update(track_id, center)
                            if crossing:
                                raw = result.names[int(box.cls.item())]
                                await self._save_event(
                                    track_id, canonical(raw) or raw, crossing, float(box.conf.item()))
                        self.counter.prune()
                    now = time.time()
                    if frame_bus.has_subscribers and now - last_publish >= 1.0 / stream_fps:
                        last_publish = now
                        await self._publish_frame(frame, result)
                self.stream.close()
                if not loop_file:
                    break
        finally:
            self.running = False
            if self.stream is not None:
                self.stream.close()

    async def _publish_frame(self, frame, result) -> None:
        tally = f"IN {self.totals.total_in}   OUT {self.totals.total_out}   INSIDE {self.current_inside}"
        try:
            jpeg = await asyncio.to_thread(annotate_jpeg, frame, result, self.line, tally)
            frame_bus.publish(jpeg)
        except Exception:  # noqa: BLE001 - a preview failure must never stop counting
            logger.exception("frame_publish_failed")

    def _resolve_line(self, camera):
        coords = (camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y)
        inside = camera.inside_direction.value if camera.inside_direction else self.settings.inside_direction
        if None in coords:
            return self.settings.count_line, inside
        return ((coords[0], coords[1]), (coords[2], coords[3])), inside

    async def _save_event(self, track_id: int, animal_type: str, crossing: CrossingEvent, confidence: float) -> None:
        now = datetime.now(timezone.utc)
        d_in, d_out = (1, 0) if crossing.direction == "IN" else (0, 1)
        async with SessionLocal() as session:
            event = AnimalEvent(
                camera_id=self.camera_id, animal_type=animal_type, tracking_id=track_id,
                crossing_sequence=crossing.sequence, direction=Direction(crossing.direction),
                confidence=confidence, timestamp=now,
            )
            session.add(event)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                logger.warning("duplicate_crossing_skipped", extra={
                    "tracking_id": track_id, "direction": crossing.direction, "sequence": crossing.sequence})
                return
            await upsert_daily(session, now.date(), animal_type, d_in, d_out)
            current = await bump_herd_state(session, 1 if crossing.direction == "IN" else -1)
            await session.commit()
            event_id = event.id

        self.current_inside = current
        self.totals.apply(crossing.direction, animal_type)
        camera_status = self.stream.status if self.stream else "OFFLINE"
        await websockets.broadcast({
            "type": "statistics", "in": self.totals.total_in, "out": self.totals.total_out,
            "current": current, "camera": camera_status, "ai": "ACTIVE",
        })
        await websockets.broadcast({
            "type": "event", "event": {
                "id": event_id, "camera_id": self.camera_id, "animal_type": animal_type,
                "tracking_id": track_id, "direction": crossing.direction, "confidence": confidence,
                "timestamp": now.isoformat(),
            },
        })
        await notifier.add(crossing.direction, current, self.camera_name)
        logger.info("animal_crossing", extra={
            "direction": crossing.direction, "tracking_id": track_id, "animal_type": animal_type,
            "sequence": crossing.sequence})

    def stop(self) -> None:
        self.running = False
        if self.stream is not None:
            self.stream.close()
