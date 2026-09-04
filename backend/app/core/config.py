from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=False, enable_decoding=False
    )

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/smart_qora"
    model_path: str = "models/best.pt"
    device: str = "0"
    require_cuda: bool = False
    half_precision: bool = True
    confidence: float = 0.25
    iou: float = 0.70
    img_size: int = 1280
    frame_skip: int = 0
    stream_fps: int = 12
    video_loop: bool = True
    tracker: Literal["botsort.yaml", "bytetrack.yaml"] = "botsort.yaml"
    # Defaults point at the bundled demo clip so a fresh clone counts out of the
    # box; override VIDEO_SOURCE + COUNT_LINE_* in .env for a real camera.
    video_source: str = "videos/crop_23.11.23-12.MP4"
    count_line_p1_x: int = 0
    count_line_p1_y: int = 594
    count_line_p2_x: int = 1440
    count_line_p2_y: int = 594
    inside_direction: Literal["UP", "DOWN", "LEFT", "RIGHT"] = "DOWN"
    allowed_classes: list[str] = ["sheep", "cattle", "goat", "horse"]
    default_language: Literal["ru", "kk", "en", "tr"] = "ru"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_aggregation_seconds: int = 5
    cors_origins: list[str] = ["http://localhost:5173"]

    secret_key: str = "change-me-in-production"
    admin_username: str = "admin"
    admin_password: str = "admin"
    access_token_ttl_hours: int = 12
    default_camera_name: str = "Gate 01"
    default_camera_source: str = ""

    @field_validator("allowed_classes", "cors_origins", mode="before")
    @classmethod
    def split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("confidence", "iou")
    @classmethod
    def unit_interval(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("must be between 0 and 1")
        return value

    @field_validator("img_size")
    @classmethod
    def valid_img_size(cls, value: int) -> int:
        if not 320 <= value <= 1920 or value % 32:
            raise ValueError("must be a multiple of 32 between 320 and 1920")
        return value

    @field_validator("frame_skip")
    @classmethod
    def non_negative_skip(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("stream_fps", "telegram_aggregation_seconds", "access_token_ttl_hours")
    @classmethod
    def positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("cors_origins")
    @classmethod
    def no_wildcard_origin(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError('CORS_ORIGINS cannot be "*" while credentials are allowed; list explicit origins')
        return value

    @model_validator(mode="after")
    def line_endpoints_differ(self):
        if (self.count_line_p1_x, self.count_line_p1_y) == (self.count_line_p2_x, self.count_line_p2_y):
            raise ValueError("counting line endpoints must differ")
        return self

    @property
    def video_source_value(self) -> int | str:
        return int(self.video_source) if self.video_source.isdigit() else self.video_source

    @property
    def count_line(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return ((self.count_line_p1_x, self.count_line_p1_y), (self.count_line_p2_x, self.count_line_p2_y))


@lru_cache
def get_settings() -> Settings:
    return Settings()
