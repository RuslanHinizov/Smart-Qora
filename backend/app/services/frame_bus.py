"""Process-local pub/sub for the latest annotated JPEG frame.

The vision worker publishes only while at least one client is subscribed, so the
extra ``result.plot()`` + JPEG encode cost is zero when nobody is watching.
"""
import asyncio
from time import monotonic


class FrameBus:
    def __init__(self):
        self.latest_jpeg: bytes | None = None
        self.latest_ts: float = 0.0
        self._subscribers: set[asyncio.Queue[bytes]] = set()

    @property
    def has_subscribers(self) -> bool:
        return bool(self._subscribers)

    def is_fresh(self, max_age: float = 5.0) -> bool:
        return self.latest_jpeg is not None and monotonic() - self.latest_ts < max_age

    def publish(self, jpeg: bytes) -> None:
        self.latest_jpeg = jpeg
        self.latest_ts = monotonic()
        for queue in self._subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(jpeg)

    def subscribe(self) -> asyncio.Queue[bytes]:
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        if self.latest_jpeg is not None:
            queue.put_nowait(self.latest_jpeg)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[bytes]) -> None:
        self._subscribers.discard(queue)


frame_bus = FrameBus()
