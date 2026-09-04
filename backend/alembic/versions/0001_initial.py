"""Initial Smart Qora schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001"; down_revision = None; branch_labels = None; depends_on = None

def upgrade():
    direction = sa.Enum("IN", "OUT", name="direction")
    op.create_table("cameras", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("rtsp_url", sa.Text(), nullable=False), sa.Column("location", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("animal_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False), sa.Column("animal_type", sa.String(80), nullable=False), sa.Column("tracking_id", sa.Integer(), nullable=False), sa.Column("direction", direction, nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("camera_id", "tracking_id", "direction", "timestamp", name="uq_event_crossing"))
    for column in ("timestamp", "camera_id", "direction", "animal_type"): op.create_index(f"ix_event_{column}", "animal_events", [column])
    op.create_table("daily_statistics", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("date", sa.Date(), nullable=False), sa.Column("animal_type", sa.String(80), nullable=False), sa.Column("total_in", sa.Integer(), nullable=False), sa.Column("total_out", sa.Integer(), nullable=False), sa.Column("current_count", sa.Integer(), nullable=False), sa.UniqueConstraint("date", "animal_type", name="uq_daily_animal"))

def downgrade():
    op.drop_table("daily_statistics"); op.drop_table("animal_events"); op.drop_table("cameras"); sa.Enum(name="direction").drop(op.get_bind())
