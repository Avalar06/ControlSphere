"""0008_multi_framework_harmonization - Phase 8 Multi-Framework Harmonization & Control Rationalization

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. framework_crosswalk_mappings (GLOBAL) ──────────────────────────────
    op.create_table(
        "framework_crosswalk_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "source_subcategory_id",
            sa.Integer(),
            sa.ForeignKey("framework_subcategories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_subcategory_id",
            sa.Integer(),
            sa.ForeignKey("framework_subcategories.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "mapping_type",
            sa.Enum(
                "EXACT",
                "SUBSET",
                "SUPERSET",
                "PARTIAL",
                "CORRELATED",
                name="mappingtypeenum",
            ),
            nullable=False,
            server_default="EXACT",
            index=True,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("bidirectional", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_subcategory_id",
            "target_subcategory_id",
            name="uq_crosswalk_source_target",
        ),
    )

    # ── 2. rationalized_common_controls (TENANT) ─────────────────────────────
    op.create_table(
        "rationalized_common_controls",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("common_control_code", sa.String(64), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "IDENTITY_ACCESS",
                "CRYPTOGRAPHY",
                "DATA_PROTECTION",
                "INCIDENT_MANAGEMENT",
                "VULNERABILITY_MANAGEMENT",
                "BUSINESS_CONTINUITY",
                "GOVERNANCE_RISK",
                "PHYSICAL_SECURITY",
                "OTHER",
                name="commoncontroldomainenum",
            ),
            nullable=False,
            server_default="GOVERNANCE_RISK",
            index=True,
        ),
        sa.Column(
            "rationalization_status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "RETIRED",
                name="rationalizationstatusenum",
            ),
            nullable=False,
            server_default="ACTIVE",
            index=True,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("deprecation_reason", sa.Text(), nullable=True),
        sa.Column(
            "inherited_health_score",
            sa.Float(),
            nullable=False,
            server_default="100.0",
        ),
        sa.Column(
            "inherited_health_status",
            sa.Enum(
                "HEALTHY",
                "DEGRADED",
                "AT_RISK",
                "FAILING",
                name="controlhealthstatusenum",
            ),
            nullable=False,
            server_default="HEALTHY",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "common_control_code",
            name="uq_org_common_control_code",
        ),
    )

    # ── 3. common_control_mappings (TENANT) ──────────────────────────────────
    op.create_table(
        "common_control_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "rationalized_common_control_id",
            sa.Integer(),
            sa.ForeignKey("rationalized_common_controls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_control_id",
            sa.Integer(),
            sa.ForeignKey("organization_controls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "rationalized_common_control_id",
            "organization_control_id",
            name="uq_cc_org_control",
        ),
    )

    # ── 4. framework_compliance_snapshots (TENANT) ───────────────────────────
    op.create_table(
        "framework_compliance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "framework_id",
            sa.Integer(),
            sa.ForeignKey("frameworks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "calculation_version",
            sa.String(20),
            nullable=False,
            server_default="v1.0",
        ),
        sa.Column("coverage_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("compliance_health_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_subcategories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("covered_subcategories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmapped_subcategories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("framework_compliance_snapshots")
    op.drop_table("common_control_mappings")
    op.drop_table("rationalized_common_controls")
    op.drop_table("framework_crosswalk_mappings")
