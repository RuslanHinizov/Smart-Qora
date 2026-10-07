import asyncio

from app.vision.camera import CameraStream


class FakeCapture:
    def __init__(self, source):
        self.reads = 0

    def isOpened(self):
        return True

    def read(self):
        self.reads += 1
        return (True, "frame") if self.reads == 1 else (False, None)

    def release(self):
        pass


def test_video_file_stops_at_end_instead_of_reconnecting(tmp_path, monkeypatch):
    video = tmp_path / "test.mp4"
    video.touch()
    monkeypatch.setattr("app.vision.camera.cv2.VideoCapture", FakeCapture)
    stream = CameraStream(str(video))

    async def collect_frames():
        return [frame async for frame in stream.frames()]

    frames = asyncio.run(collect_frames())

    assert frames == ["frame"]
    assert stream.status == "OFFLINE"


class LiveCapture:
    """A camera that produces frames faster than they are consumed, then drops."""

    def __init__(self, source=None, total=200):
        self.produced = 0
        self.total = total
        self.released = False

    def isOpened(self):
        return not self.released

    def get(self, _prop):
        return 30.0

    def read(self):
        import time
        if self.produced >= self.total:
            return False, None
        time.sleep(0.002)  # coarse OS timers stretch this; the tests only need "faster than the consumer"
        self.produced += 1
        return True, self.produced

    def release(self):
        self.released = True


def test_latest_frame_reader_drops_stale_frames_for_a_slow_consumer():
    import time

    from app.vision.camera import LatestFrameReader

    capture = LiveCapture(total=120)
    reader = LatestFrameReader(capture)
    seen = []
    while True:
        ok, frame = reader.read()
        if not ok:
            break
        seen.append(frame)
        time.sleep(0.1)  # "inference" far slower than the camera

    assert seen == sorted(set(seen))  # never repeats, never goes back in time
    assert len(seen) < 60  # most frames were skipped instead of queued
    assert seen[-1] == 120  # and the consumer still ended up at the live edge
    reader._thread.join(timeout=2)
    assert capture.released


def test_live_source_reads_through_the_latest_frame_reader_and_releases_on_close(monkeypatch):
    captures = []

    def open_capture(source):
        captures.append(LiveCapture(source, total=10_000))
        return captures[-1]

    monkeypatch.setattr("app.vision.camera.cv2.VideoCapture", open_capture)
    stream = CameraStream("rtsp://camera.invalid/stream")

    async def take(count):
        frames = []
        async for frame in stream.frames():
            frames.append(frame)
            await asyncio.sleep(0.1)
            if len(frames) == count:
                stream.close()
        return frames

    frames = asyncio.run(take(5))
    assert len(frames) == 5 and frames == sorted(set(frames))
    assert frames[-1] > 5  # frames arriving during the slow consumer were dropped
    import time
    deadline = time.time() + 2
    while not captures[0].released and time.time() < deadline:
        time.sleep(0.01)
    assert captures[0].released and len(captures) == 1
