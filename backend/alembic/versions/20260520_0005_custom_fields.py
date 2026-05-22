"""add custom field definitions and values

Revision ID: 20260520_0005
Revises: 20260520_0004
Create Date: 2026-05-20 12:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0005"
down_revision = "20260520_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("value_type", sa.String(length=16), nullable=False, server_default="text"),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entity_type", "key", name="uq_custom_field_definition_entity_key"),
    )
    op.create_index(
        "ix_custom_field_definitions_entity_type",
        "custom_field_definitions",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_custom_field_definitions_key",
        "custom_field_definitions",
        ["key"],
        unique=False,
    )

    op.create_table(
        "custom_field_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_definition_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_definition_id"],
            ["custom_field_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "field_definition_id",
            "entity_type",
            "entity_id",
            name="uq_custom_field_values_field_entity",
        ),
    )
    op.create_index(
        "ix_custom_field_values_field_definition_id",
        "custom_field_values",
        ["field_definition_id"],
        unique=False,
    )
    op.create_index(
        "ix_custom_field_values_entity_type",
        "custom_field_values",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_custom_field_values_entity_id",
        "custom_field_values",
        ["entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_custom_field_values_entity_id", table_name="custom_field_values")
    op.drop_index("ix_custom_field_values_entity_type", table_name="custom_field_values")
    op.drop_index("ix_custom_field_values_field_definition_id", table_name="custom_field_values")
    op.drop_table("custom_field_values")

    op.drop_index("ix_custom_field_definitions_key", table_name="custom_field_definitions")
    op.drop_index("ix_custom_field_definitions_entity_type", table_name="custom_field_definitions")
    op.drop_table("custom_field_definitions")
