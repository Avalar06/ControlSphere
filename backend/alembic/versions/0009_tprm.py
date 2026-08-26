"""0009_tprm - Phase 9 Third-Party & Vendor Risk Management (TPRM)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. vendors ────────────────────────────────────────────────────────────
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("vendor_code", sa.String(length=50), nullable=False, index=True),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column(
            "vendor_status",
            sa.Enum(
                "PROSPECT",
                "DUE_DILIGENCE",
                "APPROVED",
                "ACTIVE",
                "UNDER_REVIEW",
                "OFFBOARDED",
                "TERMINATED",
                name="vendorstatusenum",
            ),
            nullable=False,
            server_default="PROSPECT",
            index=True,
        ),
        sa.Column("calculated_inherent_risk", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "calculated_tier",
            sa.Enum(
                "TIER_1_CRITICAL",
                "TIER_2_SIGNIFICANT",
                "TIER_3_MODERATE",
                "TIER_4_LOW",
                name="vendortierenum",
            ),
            nullable=False,
            server_default="TIER_4_LOW",
            index=True,
        ),
        sa.Column(
            "override_tier",
            sa.Enum(
                "TIER_1_CRITICAL",
                "TIER_2_SIGNIFICANT",
                "TIER_3_MODERATE",
                "TIER_4_LOW",
                name="vendortierenum",
            ),
            nullable=True,
        ),
        sa.Column("tier_override_reason", sa.Text(), nullable=True),
        sa.Column(
            "tier_overridden_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tier_overridden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("residual_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "risk_band",
            sa.Enum(
                "LOW",
                "MODERATE",
                "HIGH",
                "CRITICAL",
                name="vendorriskbandenum",
            ),
            nullable=False,
            server_default="LOW",
            index=True,
        ),
        sa.Column(
            "business_owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
        sa.UniqueConstraint("organization_id", "vendor_code", name="uq_vendor_org_code"),
        sa.CheckConstraint(
            "calculated_inherent_risk >= 0.0 AND calculated_inherent_risk <= 100.0",
            name="chk_vendor_inherent_risk",
        ),
        sa.CheckConstraint(
            "residual_risk_score >= 0.0 AND residual_risk_score <= 100.0",
            name="chk_vendor_residual_risk",
        ),
    )

    # ── 2. vendor_engagements ─────────────────────────────────────────────────
    op.create_table(
        "vendor_engagements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("vendors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("engagement_code", sa.String(length=50), nullable=False, index=True),
        sa.Column("engagement_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PROPOSED",
                "SCOPING",
                "ACTIVE",
                "INACTIVE",
                "TERMINATED",
                name="engagementstatusenum",
            ),
            nullable=False,
            server_default="PROPOSED",
            index=True,
        ),
        sa.Column(
            "criticality",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                name="businesscriticalityenum",
            ),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column(
            "data_classification",
            sa.Enum(
                "RESTRICTED",
                "CONFIDENTIAL",
                "INTERNAL",
                "PUBLIC",
                name="dataclassificationenum",
            ),
            nullable=False,
            server_default="INTERNAL",
        ),
        sa.Column(
            "hosting_model",
            sa.Enum(
                "MULTI_TENANT_SAAS",
                "DEDICATED_CLOUD",
                "ON_PREMISE",
                name="hostingmodelenum",
            ),
            nullable=False,
            server_default="MULTI_TENANT_SAAS",
        ),
        sa.Column(
            "network_connectivity",
            sa.Enum(
                "DIRECT_API_VPN_DB",
                "CORPORATE_SSO",
                "ISOLATED_NO_CONNECTION",
                name="networkconnectivityenum",
            ),
            nullable=False,
            server_default="ISOLATED_NO_CONNECTION",
        ),
        sa.Column(
            "pii_access",
            sa.Enum(
                "DIRECT_PCI_PII_PHI",
                "METADATA_ONLY",
                "NONE",
                name="piifinancialaccessenum",
            ),
            nullable=False,
            server_default="NONE",
        ),
        sa.Column("calculated_risk_score", sa.Float(), nullable=False, server_default="0.0"),
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
        sa.UniqueConstraint("organization_id", "engagement_code", name="uq_engagement_org_code"),
        sa.CheckConstraint(
            "calculated_risk_score >= 0.0 AND calculated_risk_score <= 100.0",
            name="chk_engagement_risk_score",
        ),
    )

    # ── 3. vendor_assessments ─────────────────────────────────────────────────
    op.create_table(
        "vendor_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("vendors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "engagement_id",
            sa.Integer(),
            sa.ForeignKey("vendor_engagements.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("assessment_code", sa.String(length=50), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "assessment_type",
            sa.Enum(
                "INITIAL_DUE_DILIGENCE",
                "ANNUAL_REASSESSMENT",
                "TRIGGERED_BY_INCIDENT",
                name="vendorassessmenttypeenum",
            ),
            nullable=False,
            server_default="INITIAL_DUE_DILIGENCE",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "SUBMITTED",
                "IN_REVIEW",
                "APPROVED",
                "REJECTED",
                "SUPERSEDED",
                name="vendorassessmentstatusenum",
            ),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column(
            "assessor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("calculated_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("organization_id", "assessment_code", name="uq_assessment_org_code"),
        sa.CheckConstraint(
            "calculated_score >= 0.0 AND calculated_score <= 100.0",
            name="chk_assessment_score",
        ),
    )

    # ── 4. vendor_assessment_items ────────────────────────────────────────────
    op.create_table(
        "vendor_assessment_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            sa.ForeignKey("vendor_assessments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "rationalized_common_control_id",
            sa.Integer(),
            sa.ForeignKey("rationalized_common_controls.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("question_key", sa.String(length=100), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "response_status",
            sa.Enum(
                "COMPLIANT",
                "PARTIALLY_COMPLIANT",
                "NON_COMPLIANT",
                "NOT_APPLICABLE",
                name="vendorresponsestatusenum",
            ),
            nullable=False,
            server_default="NOT_APPLICABLE",
        ),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vendor_response_text", sa.Text(), nullable=True),
        sa.Column("assessor_notes", sa.Text(), nullable=True),
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
    )

    # ── 5. vendor_evidence_links ──────────────────────────────────────────────
    op.create_table(
        "vendor_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("vendors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_type",
            sa.Enum(
                "SOC2_TYPE2",
                "ISO27001_CERT",
                "PENTEST_SUMMARY",
                "DPA_CONTRACT",
                "SIG_QUESTIONNAIRE",
                "OTHER",
                name="vendordocumenttypeenum",
            ),
            nullable=False,
            server_default="OTHER",
        ),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "verified_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("vendor_id", "evidence_id", name="uq_vendor_evidence_link"),
    )


def downgrade() -> None:
    op.drop_table("vendor_evidence_links")
    op.drop_table("vendor_assessment_items")
    op.drop_table("vendor_assessments")
    op.drop_table("vendor_engagements")
    op.drop_table("vendors")
