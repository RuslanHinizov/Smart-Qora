"""Per-camera config columns and crossing-sequence idempotency."""
from alembic import op
import sqlalchemy as sa

revision = "0002"; down_revision = "0001"; branch_labels = None; depends_on = None

line_direction = sa.Enum("UP", "DOWN", "LEFT", "RIGHT", name="linedirection", create_type=False)


def upgrade():
    line_direction.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table("cameras") as batch:
        batch.add_column(sa.Column("source", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("line_p1_x", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("line_p1_y", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("line_p2_x", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("line_p2_y", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("inside_direction", line_direction, nullable=True))
        batch.add_column(sa.Column("confidence", sa.Float(), nullable=True))
        batch.add_column(sa.Column("iou", sa.Float(), nullable=True))
        batch.add_column(sa.Column("frame_skip", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("stream_fps", sa.Integer(), nullable=False, server_default="12"))
    op.execute("UPDATE cameras SET source = rtsp_url")
    with op.batch_alter_table("cameras") as batch:
        batch.drop_column("rtsp_url")

    with op.batch_alter_table("animal_events") as batch:
        batch.add_column(sa.Column("crossing_sequence", sa.Integer(), nullable=False, server_default="0"))
        batch.drop_constraint("uq_event_crossing", type_="unique")
        batch.create_unique_constraint(
            "uq_event_crossing", ["camera_id", "tracking_id", "direction", "crossing_sequence"]
        )
        batch.create_index("ix_event_camera_ts", ["camera_id", "timestamp"])


def downgrade():
    with op.batch_alter_table("animal_events") as batch:
        batch.drop_index("ix_event_camera_ts")
        batch.drop_constraint("uq_event_crossing", type_="unique")
        batch.create_unique_constraint(
            "uq_event_crossing", ["camera_id", "tracking_id", "direction", "timestamp"]
        )
        batch.drop_column("crossing_sequence")

    with op.batch_alter_table("cameras") as batch:
        batch.add_column(sa.Column("rtsp_url", sa.Text(), nullable=False, server_default=""))
    op.execute("UPDATE cameras SET rtsp_url = source")
    with op.batch_alter_table("cameras") as batch:
        for column in ("stream_fps", "frame_skip", "iou", "confidence", "inside_direction",
                       "line_p2_y", "line_p2_x", "line_p1_y", "line_p1_x", "source"):
            batch.drop_column(column)
    line_direction.drop(op.get_bind(), checkfirst=True)
