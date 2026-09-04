import pytest

from app.core.config import Settings


def _settings(**overrides):
    base = dict(_env_file=None, SECRET_KEY="x")
    base.update(overrides)
    return Settings(**base)


def test_defaults_are_valid():
    assert _settings().confidence == 0.25


@pytest.mark.parametrize("field,value", [
    ("CONFIDENCE", 1.5),
    ("IOU", -0.1),
    ("IMG_SIZE", 700),          # not a multiple of 32
    ("IMG_SIZE", 64),           # below range
    ("FRAME_SKIP", -1),
    ("STREAM_FPS", 0),
    ("TELEGRAM_AGGREGATION_SECONDS", 0),
])
def test_out_of_range_rejected(field, value):
    with pytest.raises(ValueError):
        _settings(**{field: value})


def test_wildcard_cors_rejected():
    with pytest.raises(ValueError):
        _settings(CORS_ORIGINS="*")


def test_zero_length_line_rejected():
    with pytest.raises(ValueError):
        _settings(COUNT_LINE_P1_X=10, COUNT_LINE_P1_Y=10, COUNT_LINE_P2_X=10, COUNT_LINE_P2_Y=10)


def test_csv_fields_still_parse():
    settings = _settings(ALLOWED_CLASSES="cow, sheep ,goat", CORS_ORIGINS="http://a,http://b")
    assert settings.allowed_classes == ["cow", "sheep", "goat"]
    assert settings.cors_origins == ["http://a", "http://b"]
