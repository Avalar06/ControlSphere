"""0019_executive_grc - Phase 20 (EXECUTIVE-GRC)
Revision ID: 0019
Revises: 0018
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. executive_snapshots ────────────────────────────────────────────────
    op.create_table(
        "executive_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("snapshot_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("overall_posture_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("inherent_risk_index", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("residual_risk_index", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("financial_exposure_ale", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("var_95_exposure", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("audit_readiness_index", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("remediation_sla_health_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("framework_compliance_summary", sa.JSON(), nullable=False),
        sa.Column("domain_posture_breakdown", sa.JSON(), nullable=False),
        sa.Column("top_risks_snapshot", sa.JSON(), nullable=False),
        sa.Column("critical_findings_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_manifest", sa.JSON(), nullable=False),
        sa.Column("data_hash_sha256", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.UniqueConstraint("organization_id", "snapshot_code", name="uq_executive_snapshot_org_code"),
    )

    # ── 2. executive_dossiers ─────────────────────────────────────────────────
    op.create_table(
        "executive_dossiers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("dossier_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "dossier_type",
            sa.Enum(
                "BOARD_SUMMARY",
                "REGULATORY_SUBMISSION",
                "ANNUAL_COMPLIANCE",
                "TARGETED_AUDIT_PACKAGE",
                name="dossiertypeenum",
            ),
            nullable=False,
            server_default="BOARD_SUMMARY",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "COMPILED",
                "UNDER_REVIEW",
                "FINALIZED",
                "ARCHIVED",
                name="dossierstatusenum",
            ),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column("scope_framework_ids", sa.JSON(), nullable=False),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("executive_snapshots.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("regulatory_commentary", sa.Text(), nullable=True),
        sa.Column("compiled_sections", sa.JSON(), nullable=True),
        sa.Column("compiled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "compiled_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "finalized_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organization_id", "dossier_code", name="uq_executive_dossier_org_code"),
    )

    # ── 3. executive_briefings ────────────────────────────────────────────────
    op.create_table(
        "executive_briefings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("briefing_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reporting_period_start", sa.Date(), nullable=False, index=True),
        sa.Column("reporting_period_end", sa.Date(), nullable=False, index=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "SUBMITTED_FOR_REVIEW",
                "APPROVED",
                "REJECTED",
                "SUPERSEDED",
                name="briefingstatusenum",
            ),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("executive_snapshots.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("key_achievements", sa.JSON(), nullable=False),
        sa.Column("emerging_risks", sa.JSON(), nullable=False),
        sa.Column("strategic_recommendations", sa.Text(), nullable=True),
        sa.Column("period_over_period_deltas", sa.JSON(), nullable=False),
        sa.Column(
            "generated_by_id",
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
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organization_id", "briefing_code", name="uq_executive_briefing_org_code"),
    )

    # ── 4. executive_export_artifacts ─────────────────────────────────────────
    op.create_table(
        "executive_export_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("export_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "export_format",
            sa.Enum("PDF", "JSON", name="exportformatenum"),
            nullable=False,
            server_default="PDF",
            index=True,
        ),
        sa.Column(
            "artifact_type",
            sa.Enum(
                "DOSSIER_PACKAGE",
                "EXECUTIVE_BRIEFING",
                "POSTURE_SNAPSHOT",
                name="artifacttypeenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "dossier_id",
            sa.Integer(),
            sa.ForeignKey("executive_dossiers.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "briefing_id",
            sa.Integer(),
            sa.ForeignKey("executive_briefings.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("executive_snapshots.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "generated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.UniqueConstraint("organization_id", "export_code", name="uq_executive_export_org_code"),
    )


def downgrade() -> None:
    op.drop_table("executive_export_artifacts")
    op.drop_table("executive_briefings")
    op.drop_table("executive_dossiers")
    op.drop_table("executive_snapshots")
