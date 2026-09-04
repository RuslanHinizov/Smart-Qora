"""Optional second counting line per camera (dual-tripwire counting)."""
from alembic import op
import sqlalchemy as sa

revision = "0006"; down_revision = "0005"; branch_labels = None; depends_on = None

_COLS = ("line2_p1_x", "line2_p1_y", "line2_p2_x", "line2_p2_y")


def upgrade():
    with op.batch_alter_table("cameras") as batch:
        for col in _COLS:
            batch.add_column(sa.Column(col, sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("cameras") as batch:
        for col in reversed(_COLS):
            batch.drop_column(col)
