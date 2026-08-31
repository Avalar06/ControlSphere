"""0014_threat_exposure_governance - Phase 14 Continuous Threat Exposure & Vulnerability Governance (EXPOSURE-GRC)
Revision ID: 0014
Revises: 0013
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. vulnerability_exposures ───────────────────────────────────────────
    op.create_table(
        "vulnerability_exposures",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("cve_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("cwe_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cvss_vector", sa.String(length=150), nullable=True),
        sa.Column("epss_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cisa_kev", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "severity",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "INFORMATIONAL",
                name="exposureseverityenum",
            ),
            nullable=False,
            server_default="MEDIUM",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "UNDER_INVESTIGATION",
                "REMEDIATING",
                "EXCEPTION_REQUESTED",
                "EXCEPTION_APPROVED",
                "EXCEPTION_REJECTED",
                "RESOLVED",
                name="exposurestatusenum",
            ),
            nullable=False,
            server_default="OPEN",
            index=True,
        ),
        sa.Column("exposure_index", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("remediation_sla_due", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "cvss_score >= 0.0 AND cvss_score <= 10.0",
            name="chk_exposure_cvss_bounds",
        ),
        sa.CheckConstraint(
            "epss_score >= 0.0 AND epss_score <= 1.0",
            name="chk_exposure_epss_bounds",
        ),
        sa.CheckConstraint(
            "exposure_index >= 0.0 AND exposure_index <= 100.0",
            name="chk_exposure_index_bounds",
        ),
    )

    # ── 2. exposure_asset_links ──────────────────────────────────────────────
    op.create_table(
        "exposure_asset_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "exposure_id",
            sa.Integer(),
            sa.ForeignKey("vulnerability_exposures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("asset_identifier", sa.String(length=255), nullable=False, index=True),
        sa.Column(
            "asset_type",
            sa.Enum(
                "SERVER",
                "DATABASE",
                "CLOUD_SERVICE",
                "NETWORK_DEVICE",
                "APPLICATION",
                name="assettypeenum",
            ),
            nullable=False,
            server_default="SERVER",
        ),
        sa.Column(
            "environment",
            sa.Enum(
                "PRODUCTION",
                "STAGING",
                "DEVELOPMENT",
                name="environmentenum",
            ),
            nullable=False,
            server_default="PRODUCTION",
        ),
        sa.Column(
            "process_id",
            sa.Integer(),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("vendors.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "control_id",
            sa.Integer(),
            sa.ForeignKey("organization_controls.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "exposure_id",
            "asset_identifier",
            "process_id",
            "vendor_id",
            "control_id",
            name="uq_exposure_asset_link",
        ),
    )

    # ── 3. exposure_exceptions ───────────────────────────────────────────────
    op.create_table(
        "exposure_exceptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "exposure_id",
            sa.Integer(),
            sa.ForeignKey("vulnerability_exposures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "requested_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "EXPIRED",
                name="exceptionapprovalstatusenum",
            ),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("original_sla_due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_sla_due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("compensating_controls", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "requested_by_id != approved_by_id",
            name="chk_exposure_exception_four_eyes",
        ),
    )


def downgrade() -> None:
    op.drop_table("exposure_exceptions")
    op.drop_table("exposure_asset_links")
    op.drop_table("vulnerability_exposures")
