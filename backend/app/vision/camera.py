import asyncio
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)


class CameraStream:
    def __init__(self, source: int | str, max_backoff: float = 30.0):
        self.source = source
        self.max_backoff = max_backoff
        self.status = "OFFLINE"
        self.fps = 30.0
        self._capture = None
        self._closed = False

    async def frames(self) -> AsyncIterator:
        backoff = 1.0
        is_video_file = isinstance(self.source, str) and Path(self.source).is_file()
        playback_started = None
        frame_number = 0
        while not self._closed:
            if self._capture is None or not self._capture.isOpened():
                self.status = "RECONNECTING"
                self._capture = await asyncio.to_thread(cv2.VideoCapture, self.source)
                if not self._capture.isOpened():
                    self.status = "OFFLINE"
                    logger.warning("camera_connection_failed retry_seconds=%s", backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.max_backoff)
                    continue
                getter = getattr(self._capture, "get", None)
                reported = getter(cv2.CAP_PROP_FPS) if getter else 0.0
                self.fps = reported if 1.0 <= reported <= 120.0 else 30.0
                self.status, backoff = "ONLINE", 1.0
                logger.info("camera_connected")
                if is_video_file:
                    playback_started = time.monotonic()
                    frame_number = 0
            ok, frame = await asyncio.to_thread(self._capture.read)
            if not ok:
                self.status = "OFFLINE"
                self._capture.release(); self._capture = None
                if is_video_file:
                    logger.info("video_file_completed")
                    break
                logger.warning("camera_disconnected")
                continue
            if is_video_file and playback_started is not None:
                target = playback_started + frame_number / self.fps
                delay = target - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                frame_number += 1
            yield frame

    def close(self) -> None:
        self._closed = True
        if self._capture is not None:
            self._capture.release()
