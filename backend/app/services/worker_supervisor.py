import asyncio
import logging
from time import monotonic

from app.core.config import Settings
from app.services.counting_service import CountingService

logger = logging.getLogger(__name__)

_MAX_BACKOFF = 60.0
_STABLE_SECONDS = 60.0


class WorkerSupervisor:
    """Owns the vision worker task and restarts it with backoff after a crash.

    On every (re)start a fresh :class:`CountingService` is built, so it re-reads the
    camera row + settings from the DB. A clean return from ``run()`` (video file ended)
    stops the supervisor; an exception restarts it.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.state = "stopped"
        self.restarts = 0
        self.last_error: str | None = None
        self._task: asyncio.Task | None = None
        self._service: CountingService | None = None
        self._stopped = False
        self._restart_requested = False

    @property
    def running(self) -> bool:
        return self.state == "running"

    @property
    def camera_status(self) -> str:
        stream = getattr(self._service, "stream", None)
        return stream.status if stream is not None else "OFFLINE"

    @property
    def last_frame_at(self) -> float | None:
        return getattr(self._service, "last_frame_at", None)

    def start(self) -> None:
        self._stopped = False
        self._task = asyncio.create_task(self._run_forever(), name="vision-worker")

    def request_restart(self) -> None:
        """Cycle a live worker, or revive one that already exited (e.g. a finished video file)."""
        self._restart_requested = True
        if self._service is not None:
            self._service.stop()
        if self._task is None or self._task.done():
            self._restart_requested = False
            self.restarts += 1
            logger.info("vision_worker_restart", extra={"reason": "revive", "restarts": self.restarts})
            self.start()

    async def stop(self) -> None:
        self._stopped = True
        if self._service is not None:
            self._service.stop()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self.state = "stopped"

    async def _run_forever(self) -> None:
        backoff = 1.0
        while not self._stopped:
            self.state = "restarting" if self.restarts else "starting"
            started = monotonic()
            try:
                self._service = CountingService(self.settings)
                self.state = "running"
                await self._service.run()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - supervisor must survive anything
                self.last_error = repr(exc)
                self.restarts += 1
                self.state = "failed"
                logger.error("vision_worker_crashed", extra={"restarts": self.restarts}, exc_info=exc)
                if monotonic() - started >= _STABLE_SECONDS:
                    backoff = 1.0
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                logger.info("vision_worker_restart", extra={"restarts": self.restarts, "backoff": backoff})
                continue
            finally:
                if self._service is not None:
                    self._service.stop()
            if self._restart_requested and not self._stopped:
                self._restart_requested = False
                self.restarts += 1
                logger.info("vision_worker_restart", extra={"reason": "requested", "restarts": self.restarts})
                continue
            break
        self.state = "stopped"
        logger.info("vision_worker_stopped")
