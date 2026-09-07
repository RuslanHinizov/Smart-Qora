"""Clear incomplete or degenerate legacy second counting lines."""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
        UPDATE cameras SET
            line2_p1_x = NULL, line2_p1_y = NULL,
            line2_p2_x = NULL, line2_p2_y = NULL
        WHERE (line2_p1_x IS NULL OR line2_p1_y IS NULL OR line2_p2_x IS NULL OR line2_p2_y IS NULL)
           OR (line2_p1_x = line2_p2_x AND line2_p1_y = line2_p2_y)
    """)


def downgrade():
    pass
