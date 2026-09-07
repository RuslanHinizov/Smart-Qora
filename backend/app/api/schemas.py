from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

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
    is_active: bool = False
    line_p1_x: int | None = None
    line_p1_y: int | None = None
    line_p2_x: int | None = None
    line_p2_y: int | None = None
    line2_p1_x: int | None = None
    line2_p1_y: int | None = None
    line2_p2_x: int | None = None
    line2_p2_y: int | None = None
    inside_direction: LineDirection | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    iou: float | None = Field(default=None, ge=0, le=1)
    frame_skip: int | None = Field(default=None, ge=0)
    stream_fps: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valid_geometry(self):
        from app.vision.counter import LineCrossingCounter
        line = (self.line_p1_x, self.line_p1_y, self.line_p2_x, self.line_p2_y)
        other = (self.line2_p1_x, self.line2_p1_y, self.line2_p2_x, self.line2_p2_y)
        for coords in (line, other):
            if any(v is not None for v in coords) and any(v is None for v in coords):
                raise ValueError("Set all four line coordinates or clear the line")
            if all(v is not None for v in coords) and coords[:2] == coords[2:]:
                raise ValueError("Line endpoints must differ")
        if other[0] is not None and line[0] is None:
            raise ValueError("Set the first line before adding a second line")
        if line[0] is not None:
            LineCrossingCounter(line[:2], line[2:], (self.inside_direction or LineDirection.DOWN).value,
                                line2=(other[:2], other[2:]) if other[0] is not None else None)
        return self


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
    telegram_digest_hour: int | None
    telegram_idle_hours: int | None
    default_confidence: float | None
    default_iou: float | None
    default_frame_skip: int | None
    stream_fps: int | None


class SettingsUpdate(BaseModel):
    default_language: str | None = Field(default=None, pattern="^(ru|kk|en|tr)$")
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_aggregation_seconds: int | None = Field(default=None, gt=0)
    telegram_digest_hour: int | None = Field(default=None, ge=0, le=23)
    telegram_idle_hours: int | None = Field(default=None, ge=1, le=168)
    default_confidence: float | None = Field(default=None, ge=0, le=1)
    default_iou: float | None = Field(default=None, ge=0, le=1)
    default_frame_skip: int | None = Field(default=None, ge=0)
    stream_fps: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def nonnullable_fields(self):
        for field in ("default_language", "telegram_bot_token", "telegram_chat_id", "telegram_aggregation_seconds"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class HerdCalibrate(BaseModel):
    current_inside: int = Field(ge=0)
