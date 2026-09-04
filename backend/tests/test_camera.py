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
