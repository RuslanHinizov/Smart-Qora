import asyncio
import logging
import time
import hashlib
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from sqlalchemy import select, update

from app.db.database import SessionLocal
from app.db.models import AnimalEvent, AppSettings, Camera, Direction, RecordingProgress
from app.core.calendar import site_day
from app.services.frame_bus import frame_bus
from app.services.rollup_service import RunningTotals, bump_herd_state, upsert_daily
from app.services.statistics_service import today_totals
from app.services.websocket_manager import websockets
from app.telegram.notifications import notifier
from app.vision.annotator import annotate_jpeg
from app.vision.camera import CameraStream
from app.vision.classes import canonical
from app.vision.counter import CrossingEvent, LineCrossingCounter
from app.vision.detector import LivestockDetector
from app.vision.tracker import CenterSmoother

logger = logging.getLogger(__name__)


def recording_fingerprint(source):
    digest = hashlib.sha256()
    with open(source, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        self.line2: tuple[tuple[int, int], tuple[int, int]] | None = None
        self.running = False
        self.last_frame_at: float | None = None
        self.session_id = uuid4().hex
        self.recording_key = None
        self.resume_frame = 0
        self.preview_only = False
        self.frame_number = 0

    def _set_totals(self, totals):
        self.totals.total_in = totals["total_in"]
        self.totals.total_out = totals["total_out"]
        self.current_inside = totals["current"]

    async def run(self) -> None:
        self.running = True
        try:
            async with SessionLocal() as session:
                camera = await session.scalar(select(Camera).where(Camera.is_active.is_(True)))
                if camera is None:
                    return
                self.camera_id = camera.id
                self.camera_name = camera.name
                self._set_totals(await today_totals(session))
                defaults = await session.get(AppSettings, 1)

            source = camera.source or str(self.settings.video_source)
            source = int(source) if source.isdigit() else source
            (p1, p2), inside, line2 = self._resolve_line(camera)
            self.line = (p1, p2)
            self.line2 = line2
            def effective(value, name, fallback):
                default = getattr(defaults, name, None)
                return value if value is not None else default if default is not None else fallback
            stream_fps = effective(camera.stream_fps, "stream_fps", self.settings.stream_fps)
            confidence = effective(camera.confidence, "default_confidence", self.settings.confidence)
            iou = effective(camera.iou, "default_iou", self.settings.iou)
            frame_skip = effective(camera.frame_skip, "default_frame_skip", self.settings.frame_skip)

            self.detector = await asyncio.to_thread(
                LivestockDetector, self.settings.model_path, self.settings.device, confidence, iou,
                self.settings.img_size, self.settings.tracker, self.settings.allowed_classes,
                self.settings.require_cuda, self.settings.half_precision,
            )

            is_file = isinstance(source, str) and Path(source).is_file()
            loop_file = is_file and self.settings.video_loop
            if is_file:
                self.recording_key = await asyncio.to_thread(recording_fingerprint, source)
                self.session_id = self.recording_key
                async with SessionLocal() as session:
                    progress = await session.get(RecordingProgress, (self.camera_id, self.recording_key))
                    if progress is None:
                        progress = RecordingProgress(camera_id=self.camera_id, fingerprint=self.recording_key)
                        session.add(progress)
                        await session.commit()
                    self.resume_frame = progress.last_frame
                    self.preview_only = progress.completed
            last_publish = 0.0
            last_totals = 0.0
            while self.running:
                # Rebuild the tracker even in preview; counting is explicitly disabled
                # after completion and is not dependent on repeated tracker IDs.
                self.frame_number = 0
                self.stream = CameraStream(source)
                try:
                    self.counter = LineCrossingCounter(
                        p1, p2, inside,
                        min_track_updates=self.settings.count_min_track_updates,
                        entry_zone=self.settings.count_entry_zone_rect,
                        line2=line2,
                    )
                except ValueError:
                    if line2 is None:
                        raise
                    logger.warning("invalid_second_counting_line_ignored", exc_info=True)
                    line2 = self.line2 = None
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
                    self.frame_number += 1
                    self.last_frame_at = time.time()
                    if self.frame_number % (frame_skip + 1):
                        continue
                    # video-time clock, not wall-clock: the counter's cooldown /
                    # TTL are in "seconds of footage", and a file may be processed
                    # faster or slower than real time.
                    now_v = self.frame_number / (getattr(self.stream, "fps", 30.0) or 30.0) if is_file else time.monotonic()
                    result = await asyncio.to_thread(self.detector.track, frame)
                    if result.boxes is not None:
                        for box in result.boxes:
                            if box.id is None:
                                continue
                            track_id = int(box.id.item())
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            center = self.smoother.update(track_id, ((x1 + x2) // 2, (y1 + y2) // 2))
                            crossing = self.counter.update(track_id, center, now=now_v)
                            if crossing and not self.preview_only and self.frame_number > self.resume_frame:
                                raw = result.names[int(box.cls.item())]
                                await self._save_event(
                                    track_id, canonical(raw) or raw, crossing, float(box.conf.item()))
                        self.counter.prune(now=now_v)
                        self.smoother.prune(self.counter.tracks)
                    checkpoint_frames = max(int(getattr(self.stream, "fps", 30.0) or 30.0), 1)
                    if (is_file and not self.preview_only and self.frame_number > self.resume_frame
                            and self.frame_number % checkpoint_frames == 0):
                        async with SessionLocal() as session:
                            await session.execute(update(RecordingProgress).where(
                                RecordingProgress.camera_id == self.camera_id,
                                RecordingProgress.fingerprint == self.recording_key,
                            ).values(last_frame=self.frame_number))
                            await session.commit()
                    now = time.time()
                    if now - last_totals >= 1.0:
                        async with SessionLocal() as session:
                            self._set_totals(await today_totals(session))
                        last_totals = now
                    if frame_bus.has_subscribers and now - last_publish >= 1.0 / stream_fps:
                        last_publish = now
                        await self._publish_frame(frame, result)
                self.stream.close()
                if self.running and is_file and not self.preview_only:
                    async with SessionLocal() as session:
                        await session.execute(update(RecordingProgress).where(
                            RecordingProgress.camera_id == self.camera_id,
                            RecordingProgress.fingerprint == self.recording_key,
                        ).values(completed=True, last_frame=self.frame_number))
                        await session.commit()
                    self.preview_only = True
                if not loop_file:
                    break
        finally:
            self.running = False
            if self.stream is not None:
                self.stream.close()

    async def _publish_frame(self, frame, result) -> None:
        tally = f"IN {self.totals.total_in}   OUT {self.totals.total_out}   INSIDE {self.current_inside}"
        try:
            jpeg = await asyncio.to_thread(annotate_jpeg, frame, result, self.line, tally, self.line2)
            frame_bus.publish(jpeg)
        except Exception:  # noqa: BLE001 - a preview failure must never stop counting
            logger.exception("frame_publish_failed")

    def _resolve_line(self, camera):
        coords = (camera.line_p1_x, camera.line_p1_y, camera.line_p2_x, camera.line_p2_y)
        inside = camera.inside_direction.value if camera.inside_direction else self.settings.inside_direction
        line = self.settings.count_line if None in coords else ((coords[0], coords[1]), (coords[2], coords[3]))
        c2 = (camera.line2_p1_x, camera.line2_p1_y, camera.line2_p2_x, camera.line2_p2_y)
        line2 = None if None in c2 else ((c2[0], c2[1]), (c2[2], c2[3]))
        return line, inside, line2

    async def _save_event(self, track_id: int, animal_type: str, crossing: CrossingEvent, confidence: float) -> None:
        now = datetime.now(timezone.utc)
        d_in, d_out = (1, 0) if crossing.direction == "IN" else (0, 1)
        async with SessionLocal() as session:
            event = AnimalEvent(
                camera_id=self.camera_id, animal_type=animal_type, tracking_id=track_id,
                crossing_sequence=crossing.sequence, direction=Direction(crossing.direction),
                session_id=self.session_id,
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
            await upsert_daily(session, site_day(now), animal_type, d_in, d_out)
            current = await bump_herd_state(session, 1 if crossing.direction == "IN" else -1)
            if self.recording_key:
                await session.execute(update(RecordingProgress).where(
                    RecordingProgress.camera_id == self.camera_id,
                    RecordingProgress.fingerprint == self.recording_key,
                ).values(last_frame=self.frame_number))
            await session.commit()
            event_id = event.id
            self._set_totals(await today_totals(session))

        self.current_inside = current
        camera_status = self.stream.status if self.stream else "OFFLINE"
        await websockets.broadcast({
            "type": "statistics", "in": self.totals.total_in, "out": self.totals.total_out,
            "current": current, "camera": camera_status, "ai": "ACTIVE",
        })
        await websockets.broadcast({
            "type": "event", "event": {
                "id": event_id, "camera_id": self.camera_id, "animal_type": animal_type,
                "tracking_id": track_id, "direction": crossing.direction, "confidence": confidence,
                "crossing_sequence": crossing.sequence,
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
