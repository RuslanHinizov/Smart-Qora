"""Farm zones, animal groups and auditable inventory movements."""
from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = depends_on = None


zone_kind = sa.Enum("PEN", "PASTURE", "QUARANTINE", "EXTERNAL", name="zonekind")
movement_kind = sa.Enum("INITIAL", "CAMERA", "MANUAL_ADJUSTMENT", "TRANSFER", name="movementkind")


def upgrade():
    op.create_table(
        "farm_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", zone_kind, nullable=False, server_default="PEN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_farm_zone_name"),
    )
    op.create_table(
        "animal_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("species", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_animal_group_name"),
    )
    op.create_table(
        "inventory_balances",
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("farm_zones.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("animal_groups.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("animal_groups.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_zone_id", sa.Integer(), sa.ForeignKey("farm_zones.id", ondelete="RESTRICT")),
        sa.Column("to_zone_id", sa.Integer(), sa.ForeignKey("farm_zones.id", ondelete="RESTRICT")),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("kind", movement_kind, nullable=False),
        sa.Column("source_event_id", sa.Integer(), sa.ForeignKey("animal_events.id", ondelete="RESTRICT")),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_movement_positive_quantity"),
        sa.UniqueConstraint("source_event_id", name="uq_inventory_movement_source_event"),
    )
    op.create_index("ix_inventory_movement_created_at", "inventory_movements", ["created_at"])
    op.create_table(
        "inventory_reconciliations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("farm_zones.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("animal_groups.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("expected_quantity", sa.Integer(), nullable=False),
        sa.Column("physical_quantity", sa.Integer(), nullable=False),
        sa.Column("difference", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("physical_quantity >= 0", name="ck_reconciliation_nonnegative"),
    )
    with op.batch_alter_table("cameras") as batch:
        batch.add_column(sa.Column("inside_zone_id", sa.Integer()))
        batch.add_column(sa.Column("outside_zone_id", sa.Integer()))
        batch.create_foreign_key("fk_camera_inside_zone", "farm_zones", ["inside_zone_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_camera_outside_zone", "farm_zones", ["outside_zone_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    with op.batch_alter_table("cameras") as batch:
        batch.drop_constraint("fk_camera_outside_zone", type_="foreignkey")
        batch.drop_constraint("fk_camera_inside_zone", type_="foreignkey")
        batch.drop_column("outside_zone_id")
        batch.drop_column("inside_zone_id")
    op.drop_table("inventory_reconciliations")
    op.drop_index("ix_inventory_movement_created_at", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_table("inventory_balances")
    op.drop_table("animal_groups")
    op.drop_table("farm_zones")
    zone_kind.drop(op.get_bind(), checkfirst=True)
    movement_kind.drop(op.get_bind(), checkfirst=True)
