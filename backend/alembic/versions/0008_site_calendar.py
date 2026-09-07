"""Rebuild derived daily rollups using the site's calendar; allow inherited camera settings."""
import os
from collections import defaultdict
from datetime import timezone
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = depends_on = None


def rebuild(zone):
    bind = op.get_bind()
    events = sa.table("animal_events", sa.column("timestamp", sa.DateTime()),
                      sa.column("animal_type", sa.String()), sa.column("direction", sa.String()))
    daily = sa.table("daily_statistics", sa.column("date", sa.Date()), sa.column("animal_type", sa.String()),
                     sa.column("total_in", sa.Integer()), sa.column("total_out", sa.Integer()),
                     sa.column("current_count", sa.Integer()))
    buckets = defaultdict(lambda: [0, 0])
    for timestamp, animal, direction in bind.execute(sa.select(events)).yield_per(1000):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        buckets[timestamp.astimezone(zone).date(), animal][0 if direction == "IN" else 1] += 1
    bind.execute(daily.delete())
    for (day, animal), (ins, outs) in buckets.items():
        bind.execute(daily.insert().values(date=day, animal_type=animal, total_in=ins, total_out=outs, current_count=ins-outs))


def upgrade():
    with op.batch_alter_table("cameras") as batch:
        for name in ("frame_skip", "stream_fps"):
            batch.alter_column(name, existing_type=sa.Integer(), nullable=True)
    rebuild(ZoneInfo(os.environ.get("TZ", "Asia/Almaty")))


def downgrade():
    op.execute("UPDATE cameras SET frame_skip = 0 WHERE frame_skip IS NULL")
    op.execute("UPDATE cameras SET stream_fps = 12 WHERE stream_fps IS NULL")
    with op.batch_alter_table("cameras") as batch:
        for name in ("frame_skip", "stream_fps"):
            batch.alter_column(name, existing_type=sa.Integer(), nullable=False)
    rebuild(timezone.utc)
