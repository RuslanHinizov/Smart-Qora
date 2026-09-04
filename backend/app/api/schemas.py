from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.db.models import LineDirection, Role


def mask_credentials(value: str) -> str:
    parts = urlsplit(value)
    if not parts.password:
        return value
    netloc = f"{parts.username}:***@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source: str = ""
    location: str = ""
    is_active: bool = True
    line_p1_x: int | None = None
    line_p1_y: int | None = None
    line_p2_x: int | None = None
    line_p2_y: int | None = None
    inside_direction: LineDirection | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    iou: float | None = Field(default=None, ge=0, le=1)
    frame_skip: int = Field(default=0, ge=0)
    stream_fps: int = Field(default=12, gt=0)


class CameraRead(CameraCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

    @field_serializer("source")
    def _mask_source(self, value: str) -> str:
        return mask_credentials(value)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: int
    animal_type: str
    tracking_id: int
    crossing_sequence: int
    direction: str
    confidence: float
    timestamp: datetime


class StatisticsRead(BaseModel):
    total_in: int
    total_out: int
    current: int


class HistoryRow(BaseModel):
    date: date
    animal_type: str
    total_in: int
    total_out: int
    net: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: Role
    is_active: bool


class SettingsRead(BaseModel):
    default_language: str
    telegram_configured: bool
    telegram_aggregation_seconds: int
    default_confidence: float | None
    default_iou: float | None
    default_frame_skip: int | None
    stream_fps: int | None


class SettingsUpdate(BaseModel):
    default_language: str | None = Field(default=None, pattern="^(ru|kk|en|tr)$")
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_aggregation_seconds: int | None = Field(default=None, gt=0)
    default_confidence: float | None = Field(default=None, ge=0, le=1)
    default_iou: float | None = Field(default=None, ge=0, le=1)
    default_frame_skip: int | None = Field(default=None, ge=0)
    stream_fps: int | None = Field(default=None, gt=0)


class HerdCalibrate(BaseModel):
    current_inside: int = Field(ge=0)
