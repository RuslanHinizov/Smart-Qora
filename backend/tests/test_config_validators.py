import pytest

from app.core.config import Settings


def _settings(**overrides):
    # lowercase field names — env-alias (UPPERCASE) kwargs are not populated by
    # pydantic-settings' __init__ and would be silently dropped by extra="ignore".
    return Settings(_env_file=None, secret_key="x", **overrides)


def test_defaults_are_valid():
    assert _settings().confidence == 0.25


@pytest.mark.parametrize("field,value", [
    ("confidence", 1.5),
    ("iou", -0.1),
    ("img_size", 700),          # not a multiple of 32
    ("img_size", 64),           # below range
    ("frame_skip", -1),
    ("count_min_track_updates", -1),
    ("count_entry_zone", "10,20,30"),   # needs 4 values
    ("stream_fps", 0),
    ("telegram_aggregation_seconds", 0),
])
def test_out_of_range_rejected(field, value):
    with pytest.raises(ValueError):
        _settings(**{field: value})


def test_wildcard_cors_rejected():
    with pytest.raises(ValueError):
        _settings(cors_origins="*")


def test_zero_length_line_rejected():
    with pytest.raises(ValueError):
        _settings(count_line_p1_x=10, count_line_p1_y=10, count_line_p2_x=10, count_line_p2_y=10)


def test_csv_fields_still_parse():
    settings = _settings(allowed_classes="cow, sheep ,goat", cors_origins="http://a,http://b")
    assert settings.allowed_classes == ["cow", "sheep", "goat"]
    assert settings.cors_origins == ["http://a", "http://b"]
