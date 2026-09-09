import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, text,
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


class ZoneKind(str, enum.Enum):
    PEN = "PEN"
    PASTURE = "PASTURE"
    QUARANTINE = "QUARANTINE"
    EXTERNAL = "EXTERNAL"


class MovementKind(str, enum.Enum):
    INITIAL = "INITIAL"
    CAMERA = "CAMERA"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    TRANSFER = "TRANSFER"


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        Index(
            "uq_camera_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    line_p1_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_p1_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_p2_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_p2_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line2_p1_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line2_p1_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line2_p2_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line2_p2_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inside_direction: Mapped[LineDirection | None] = mapped_column(Enum(LineDirection), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    iou: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_skip: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream_fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inside_zone_id: Mapped[int | None] = mapped_column(ForeignKey("farm_zones.id", ondelete="RESTRICT"), nullable=True)
    outside_zone_id: Mapped[int | None] = mapped_column(ForeignKey("farm_zones.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    events: Mapped[list["AnimalEvent"]] = relationship(back_populates="camera")


class FarmZone(Base):
    __tablename__ = "farm_zones"
    __table_args__ = (UniqueConstraint("name", name="uq_farm_zone_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[ZoneKind] = mapped_column(Enum(ZoneKind), default=ZoneKind.PEN)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnimalGroup(Base):
    __tablename__ = "animal_groups"
    __table_args__ = (
        UniqueConstraint("name", name="uq_animal_group_name"),
        # At most one default group per species (e.g. "Sheep" over "Lambs"),
        # so a camera detection can still auto-route when several active
        # groups share a species — see app.services.inventory_service.group_for_detection.
        Index(
            "uq_animal_group_default_species",
            "species",
            unique=True,
            postgresql_where=text("is_default_for_species = true"),
            sqlite_where=text("is_default_for_species = 1"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    species: Mapped[str] = mapped_column(String(80))
    is_default_for_species: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    zone_id: Mapped[int] = mapped_column(ForeignKey("farm_zones.id", ondelete="RESTRICT"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("animal_groups.id", ondelete="RESTRICT"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_inventory_movement_positive_quantity"),
        UniqueConstraint("source_event_id", name="uq_inventory_movement_source_event"),
        Index("ix_inventory_movement_created_at", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("animal_groups.id", ondelete="RESTRICT"))
    from_zone_id: Mapped[int | None] = mapped_column(ForeignKey("farm_zones.id", ondelete="RESTRICT"), nullable=True)
    to_zone_id: Mapped[int | None] = mapped_column(ForeignKey("farm_zones.id", ondelete="RESTRICT"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    kind: Mapped[MovementKind] = mapped_column(Enum(MovementKind))
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey("animal_events.id", ondelete="RESTRICT"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class InventoryReconciliation(Base):
    __tablename__ = "inventory_reconciliations"
    __table_args__ = (CheckConstraint("physical_quantity >= 0", name="ck_reconciliation_nonnegative"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("farm_zones.id", ondelete="RESTRICT"))
    group_id: Mapped[int] = mapped_column(ForeignKey("animal_groups.id", ondelete="RESTRICT"))
    expected_quantity: Mapped[int] = mapped_column(Integer)
    physical_quantity: Mapped[int] = mapped_column(Integer)
    difference: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnimalEvent(Base):
    __tablename__ = "animal_events"
    __table_args__ = (
        Index("ix_event_timestamp", "timestamp"), Index("ix_event_camera_id", "camera_id"),
        Index("ix_event_direction", "direction"), Index("ix_event_animal_type", "animal_type"),
        Index("ix_event_camera_ts", "camera_id", "timestamp"),
        UniqueConstraint("camera_id", "session_id", "tracking_id", "direction", "crossing_sequence", name="uq_event_crossing"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"))
    animal_type: Mapped[str] = mapped_column(String(80))
    tracking_id: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[str] = mapped_column(String(64), default="legacy", server_default="legacy")
    crossing_sequence: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[Direction] = mapped_column(Enum(Direction))
    confidence: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    camera: Mapped[Camera] = relationship(back_populates="events")


class RecordingProgress(Base):
    """A recording is counted once; subsequent playback is preview-only."""
    __tablename__ = "recording_progress"
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_frame: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


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
    telegram_digest_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telegram_idle_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_iou: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_frame_skip: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream_fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TelegramChat(Base):
    """A Telegram chat that receives alerts / uses the bot. Authorisation is the
    CSV in ``AppSettings.telegram_chat_id``; this row only holds the chat's
    language preference (``/dil``), defaulting to Russian."""

    __tablename__ = "telegram_chats"
    chat_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(2), default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
