from app.core.config import Settings


def test_class_filter_csv_and_camera_source():
    settings = Settings(ALLOWED_CLASSES="cow,sheep,goat", VIDEO_SOURCE="0")
    assert settings.allowed_classes == ["cow", "sheep", "goat"]
    assert settings.video_source_value == 0


def test_file_camera_source():
    assert Settings(VIDEO_SOURCE="videos/test.mp4").video_source_value == "videos/test.mp4"


def test_csv_and_gpu_flags_from_environment(monkeypatch):
    monkeypatch.setenv("ALLOWED_CLASSES", "Cattle,Goat,Sheep,Horse")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
    monkeypatch.setenv("REQUIRE_CUDA", "true")
    monkeypatch.setenv("HALF_PRECISION", "true")

    settings = Settings(_env_file=None)

    assert settings.allowed_classes == ["Cattle", "Goat", "Sheep", "Horse"]
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:4173"]
    assert settings.require_cuda is True
    assert settings.half_precision is True
