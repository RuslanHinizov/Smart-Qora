"""Users table for app-level authentication."""
from alembic import op
import sqlalchemy as sa

revision = "0004"; down_revision = "0003"; branch_labels = None; depends_on = None

role = sa.Enum("admin", "viewer", name="role")


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(120), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", role, nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("users")
    sa.Enum(name="role").drop(op.get_bind(), checkfirst=True)
