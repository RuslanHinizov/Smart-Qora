"""Herd-state and app-settings singletons; daily_statistics.updated_at."""
from alembic import op
import sqlalchemy as sa

revision = "0003"; down_revision = "0002"; branch_labels = None; depends_on = None


def upgrade():
    op.create_table(
        "herd_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("current_inside", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("baseline", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_herd_state_singleton"),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("default_language", sa.String(2), nullable=False, server_default="ru"),
        sa.Column("telegram_bot_token", sa.Text(), nullable=False, server_default=""),
        sa.Column("telegram_chat_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("telegram_aggregation_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("default_confidence", sa.Float(), nullable=True),
        sa.Column("default_iou", sa.Float(), nullable=True),
        sa.Column("default_frame_skip", sa.Integer(), nullable=True),
        sa.Column("stream_fps", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_app_settings_singleton"),
    )
    op.execute("INSERT INTO herd_state (id, current_inside, baseline) VALUES (1, 0, 0)")
    op.execute("INSERT INTO app_settings (id) VALUES (1)")

    with op.batch_alter_table("daily_statistics") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                                   server_default=sa.func.now()))


def downgrade():
    with op.batch_alter_table("daily_statistics") as batch:
        batch.drop_column("updated_at")
    op.drop_table("app_settings")
    op.drop_table("herd_state")
