"""Scope track IDs to sessions; preserve completed recording playback and active camera."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table("animal_events") as batch:
        batch.add_column(sa.Column("session_id", sa.String(64), nullable=False, server_default="legacy"))
        batch.drop_constraint("uq_event_crossing", type_="unique")
        batch.create_unique_constraint("uq_event_crossing", ["camera_id", "session_id", "tracking_id", "direction", "crossing_sequence"])
    op.create_table("recording_progress",
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), primary_key=True),
        sa.Column("fingerprint", sa.String(64), primary_key=True),
        sa.Column("last_frame", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE cameras SET is_active = false WHERE id <> (SELECT MIN(id) FROM cameras WHERE is_active = true)")
    op.create_index("uq_camera_active", "cameras", ["is_active"], unique=True,
                    postgresql_where=sa.text("is_active = true"), sqlite_where=sa.text("is_active = 1"))


def downgrade():
    # Never silently discard newer sessions to make the old unique key fit.
    duplicates = op.get_bind().execute(sa.text(
        "SELECT 1 FROM animal_events GROUP BY camera_id, tracking_id, direction, crossing_sequence HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError("Cannot downgrade session-scoped events without losing data; restore the pre-upgrade backup instead")
    op.drop_index("uq_camera_active", table_name="cameras")
    op.drop_table("recording_progress")
    with op.batch_alter_table("animal_events") as batch:
        batch.drop_constraint("uq_event_crossing", type_="unique")
        batch.drop_column("session_id")
        batch.create_unique_constraint("uq_event_crossing", ["camera_id", "tracking_id", "direction", "crossing_sequence"])
