"""add letterheads, report_templates, generated_report_logs

Revision ID: 0071
Revises: 0070
Create Date: 2026-08-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Letterheads table
    op.create_table(
        "letterheads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("asset_file_id", sa.Integer(), sa.ForeignKey("asset_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("margin_top_mm", sa.Numeric(6, 2), nullable=False, server_default=sa.text("20.0")),
        sa.Column("margin_bottom_mm", sa.Numeric(6, 2), nullable=False, server_default=sa.text("20.0")),
        sa.Column("margin_left_mm", sa.Numeric(6, 2), nullable=False, server_default=sa.text("20.0")),
        sa.Column("margin_right_mm", sa.Numeric(6, 2), nullable=False, server_default=sa.text("20.0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Report templates table
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("letterhead_id", sa.Integer(), sa.ForeignKey("letterheads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("data_source_type", sa.String(50), nullable=False, server_default="job"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Generated report logs table
    op.create_table(
        "generated_report_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("asset_file_id", sa.Integer(), sa.ForeignKey("asset_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("format", sa.String(10), nullable=False, server_default="pdf"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_generated_report_logs_entity", "generated_report_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_report_logs_entity", table_name="generated_report_logs")
    op.drop_table("generated_report_logs")
    op.drop_table("report_templates")
    op.drop_table("letterheads")
