"""Default animal group per species, so a camera can still auto-route a
detection when more than one group shares a species (e.g. "Sheep" and
"Lambs", both species=sheep)."""
from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "animal_groups",
        sa.Column("is_default_for_species", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "uq_animal_group_default_species", "animal_groups", ["species"], unique=True,
        postgresql_where=sa.text("is_default_for_species = true"),
        sqlite_where=sa.text("is_default_for_species = 1"),
    )


def downgrade():
    op.drop_index("uq_animal_group_default_species", table_name="animal_groups")
    op.drop_column("animal_groups", "is_default_for_species")
