"""0013_operational_resilience - Phase 13 Operational Resilience & Business Impact Analysis (RESILIENCE-GRC)
Revision ID: 0013
Revises: 0012
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. business_processes ────────────────────────────────────────────────
    op.create_table(
        "business_processes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "criticality_tier",
            sa.Enum(
                "TIER_1",
                "TIER_2",
                "TIER_3",
                "TIER_4",
                name="criticalitytierenum",
            ),
            nullable=False,
            server_default="TIER_3",
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "name",
            name="uq_business_process_org_name",
        ),
    )

    # ── 2. business_impact_analyses ──────────────────────────────────────────
    op.create_table(
        "business_impact_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "SUPERSEDED",
                "ARCHIVED",
                name="biastatusenum",
            ),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rto_hours", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("rpo_hours", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("mtd_hours", sa.Float(), nullable=False, server_default="24.0"),
        sa.Column(
            "hourly_downtime_cost",
            sa.Float(),
            nullable=False,
            server_default="10000.0",
        ),
        sa.Column(
            "fixed_outage_cost",
            sa.Float(),
            nullable=False,
            server_default="5000.0",
        ),
        sa.Column(
            "requested_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.CheckConstraint("rto_hours <= mtd_hours", name="chk_bia_rto_lte_mtd"),
        sa.CheckConstraint("rto_hours >= 0.0", name="chk_bia_rto_nonneg"),
        sa.CheckConstraint("rpo_hours >= 0.0", name="chk_bia_rpo_nonneg"),
        sa.CheckConstraint("mtd_hours >= 0.0", name="chk_bia_mtd_nonneg"),
        sa.CheckConstraint(
            "hourly_downtime_cost >= 0.0", name="chk_bia_hourly_cost_nonneg"
        ),
        sa.CheckConstraint(
            "fixed_outage_cost >= 0.0", name="chk_bia_fixed_cost_nonneg"
        ),
        sa.UniqueConstraint(
            "process_id",
            "version",
            name="uq_bia_process_version",
        ),
    )

    # ── 3. process_dependencies ──────────────────────────────────────────────
    op.create_table(
        "process_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "dependency_type",
            sa.Enum("VENDOR", "CONTROL", name="dependencytypeenum"),
            nullable=False,
            index=True,
        ),
        sa.Column("dependency_id", sa.Integer(), nullable=False, index=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.UniqueConstraint(
            "process_id",
            "dependency_type",
            "dependency_id",
            name="uq_process_dependency",
        ),
    )


def downgrade() -> None:
    op.drop_table("process_dependencies")
    op.drop_table("business_impact_analyses")
    op.drop_table("business_processes")
