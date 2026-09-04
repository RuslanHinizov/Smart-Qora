"""Per-chat Telegram language + digest / idle-alert settings."""
from alembic import op
import sqlalchemy as sa

revision = "0005"; down_revision = "0004"; branch_labels = None; depends_on = None


def upgrade():
    op.create_table(
        "telegram_chats",
        sa.Column("chat_id", sa.String(64), primary_key=True),
        sa.Column("language", sa.String(2), nullable=False, server_default="ru"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    with op.batch_alter_table("app_settings") as batch:
        batch.add_column(sa.Column("telegram_digest_hour", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("telegram_idle_hours", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("app_settings") as batch:
        batch.drop_column("telegram_idle_hours")
        batch.drop_column("telegram_digest_hour")
    op.drop_table("telegram_chats")
