import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Direction(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"


class LineDirection(str, enum.Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class Role(str, enum.Enum):
    admin = "admin"
    viewer = "viewer"


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    line_p1_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_p1_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_p2_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_p2_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inside_direction: Mapped[LineDirection | None] = mapped_column(Enum(LineDirection), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    iou: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_skip: Mapped[int] = mapped_column(Integer, default=0)
    stream_fps: Mapped[int] = mapped_column(Integer, default=12)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    events: Mapped[list["AnimalEvent"]] = relationship(back_populates="camera")


class AnimalEvent(Base):
    __tablename__ = "animal_events"
    __table_args__ = (
        Index("ix_event_timestamp", "timestamp"), Index("ix_event_camera", "camera_id"),
        Index("ix_event_direction", "direction"), Index("ix_event_animal", "animal_type"),
        Index("ix_event_camera_ts", "camera_id", "timestamp"),
        UniqueConstraint("camera_id", "tracking_id", "direction", "crossing_sequence", name="uq_event_crossing"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"))
    animal_type: Mapped[str] = mapped_column(String(80))
    tracking_id: Mapped[int] = mapped_column(Integer)
    crossing_sequence: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[Direction] = mapped_column(Enum(Direction))
    confidence: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    camera: Mapped[Camera] = relationship(back_populates="events")


class DailyStatistic(Base):
    __tablename__ = "daily_statistics"
    __table_args__ = (UniqueConstraint("date", "animal_type", name="uq_daily_animal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    animal_type: Mapped[str] = mapped_column(String(80))
    total_in: Mapped[int] = mapped_column(Integer, default=0)
    total_out: Mapped[int] = mapped_column(Integer, default=0)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class HerdState(Base):
    __tablename__ = "herd_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_herd_state_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    current_inside: Mapped[int] = mapped_column(Integer, default=0)
    baseline: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_app_settings_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    default_language: Mapped[str] = mapped_column(String(2), default="ru")
    telegram_bot_token: Mapped[str] = mapped_column(Text, default="")
    telegram_chat_id: Mapped[str] = mapped_column(Text, default="")
    telegram_aggregation_seconds: Mapped[int] = mapped_column(Integer, default=5)
    default_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_iou: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_frame_skip: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream_fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
