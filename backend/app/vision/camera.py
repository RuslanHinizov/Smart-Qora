import asyncio
import logging
import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)


class LatestFrameReader:
    """Drains a live capture on its own thread and keeps only the newest frame.

    Inference is slower than a 25-30 fps camera, and OpenCV queues what is not
    read, so reading frame by frame makes the picture fall further and further
    behind real time. Here stale frames are dropped instead: ``read`` always
    returns the most recent one that has not been handed out yet.
    """

    def __init__(self, capture):
        self._capture = capture
        self._cond = threading.Condition()
        self._frame = None
        self._ended = False
        self._stopped = False
        self._thread = threading.Thread(target=self._run, name="camera-reader", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stopped:
                ok, frame = self._capture.read()
                if not ok:
                    break
                with self._cond:
                    self._frame = frame
                    self._cond.notify_all()
        finally:
            # Released here, on the thread that reads, so it never races a read().
            self._capture.release()
            with self._cond:
                self._ended = True
                self._cond.notify_all()

    def read(self):
        """Block until a new frame arrives; ``(False, None)`` once the feed is gone."""
        with self._cond:
            while self._frame is None and not self._ended and not self._stopped:
                self._cond.wait(timeout=0.5)
            frame, self._frame = self._frame, None
        return frame is not None, frame

    def stop(self) -> None:
        self._stopped = True
        with self._cond:
            self._cond.notify_all()


class CameraStream:
    def __init__(self, source: int | str, max_backoff: float = 30.0):
        self.source = source
        self.max_backoff = max_backoff
        self.status = "OFFLINE"
        self.fps = 30.0
        self._capture = None
        self._reader: LatestFrameReader | None = None
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
                else:
                    self._reader = LatestFrameReader(self._capture)
            read = self._reader.read if self._reader is not None else self._capture.read
            ok, frame = await asyncio.to_thread(read)
            if not ok:
                self.status = "OFFLINE"
                self._release()
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

    def _release(self) -> None:
        if self._reader is not None:
            self._reader.stop()  # its thread releases the capture
        elif self._capture is not None:
            self._capture.release()
        self._reader = self._capture = None

    def close(self) -> None:
        self._closed = True
        self._release()
