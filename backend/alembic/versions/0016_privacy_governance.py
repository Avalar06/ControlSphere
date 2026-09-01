"""0016_privacy_governance - Phase 16 Privacy Governance & Data Protection (PRIVACY-GRC)
Revision ID: 0016
Revises: 0015
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. data_assets ────────────────────────────────────────────────────────
    op.create_table(
        "data_assets",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("asset_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "data_sensitivity_level",
            sa.Enum(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "RESTRICTED_PII",
                "SPECIAL_CATEGORY_SENSITIVE_PHI",
                name="datasensitivitylevel",
            ),
            nullable=False,
            server_default="INTERNAL",
        ),
        sa.Column("data_volume_range", sa.String(length=64), nullable=False, server_default="LOW"),
        sa.Column("storage_type", sa.String(length=64), nullable=False, server_default="POSTGRES_DB"),
        sa.Column("hosting_jurisdiction", sa.String(length=64), nullable=False, server_default="EU_EEA"),
        sa.Column("is_encrypted_at_rest", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_encrypted_in_transit", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_pseudonymized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retention_period_months", sa.Integer(), nullable=True, server_default="12"),
        # Cross-Module Lineage
        sa.Column(
            "business_process_id",
            sa.Integer(),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "ai_system_id",
            sa.Integer(),
            sa.ForeignKey("ai_systems.id", ondelete="SET NULL"),
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
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "asset_code", name="uq_data_asset_org_code"),
    )

    # ── 2. processing_activities (RoPA) ──────────────────────────────────────
    op.create_table(
        "processing_activities",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("activity_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("purpose_description", sa.Text(), nullable=False),
        sa.Column(
            "legal_basis",
            sa.Enum(
                "CONSENT",
                "CONTRACT_PERFORMANCE",
                "LEGAL_OBLIGATION",
                "VITAL_INTERESTS",
                "PUBLIC_TASK",
                "LEGITIMATE_INTERESTS",
                name="processinglegalbasis",
            ),
            nullable=False,
        ),
        sa.Column("data_subject_categories", sa.Text(), nullable=False),
        sa.Column("personal_data_categories", sa.Text(), nullable=False),
        sa.Column("is_special_category_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_automated_decision_making", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_large_scale_monitoring", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_vulnerable_subjects", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_cross_border_transfer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "transfer_mechanism",
            sa.Enum(
                "ADEQUACY_DECISION",
                "STANDARD_CONTRACTUAL_CLAUSES_SCC",
                "BINDING_CORPORATE_RULES_BCR",
                "DEROGATION_EXPLICIT_CONSENT",
                "NONE_INTRA_EEA",
                name="transfermechanism",
            ),
            nullable=False,
            server_default="NONE_INTRA_EEA",
        ),
        sa.Column("destination_country", sa.String(length=64), nullable=True),
        sa.Column("security_measures_summary", sa.Text(), nullable=True),
        sa.Column(
            "lifecycle_state",
            sa.Enum(
                "DRAFT",
                "DPO_REVIEW",
                "ACTIVE",
                "SUSPENDED",
                "ARCHIVED",
                "RETIRED",
                name="processinglifecyclestate",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "dpo_approval_status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "SUPERSEDED",
                name="privacyapprovalstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        # Cross-Module Lineage
        sa.Column(
            "business_process_id",
            sa.Integer(),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "ai_system_id",
            sa.Integer(),
            sa.ForeignKey("ai_systems.id", ondelete="SET NULL"),
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
        sa.Column("data_controller_name", sa.String(length=255), nullable=True),
        # Ownership & Approval
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "approved_by_dpo_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "activity_code", name="uq_processing_activity_org_code"),
    )

    # ── 3. dpia_assessments ──────────────────────────────────────────────────
    op.create_table(
        "dpia_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("assessment_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "processing_activity_id",
            sa.Integer(),
            sa.ForeignKey("processing_activities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("necessity_proportionality_score", sa.Numeric(5, 2), nullable=False, server_default="100.00"),
        sa.Column("data_subject_rights_score", sa.Numeric(5, 2), nullable=False, server_default="100.00"),
        sa.Column("safeguards_mitigation_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("inherent_risk_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("residual_risk_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "risk_band",
            sa.Enum(
                "LOW",
                "MODERATE",
                "HIGH",
                "VERY_HIGH",
                "CRITICAL",
                name="dpiariskband",
            ),
            nullable=False,
            server_default="LOW",
        ),
        sa.Column("automated_decision_making_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("large_scale_monitoring_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("vulnerable_subjects_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "dpo_consultation_status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "SUPERSEDED",
                name="privacyapprovalstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("dpo_recommendation_notes", sa.Text(), nullable=True),
        sa.Column(
            "dpo_reviewed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("dpo_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prior_consultation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "assessment_code", name="uq_dpia_assessment_org_code"),
        sa.CheckConstraint("inherent_risk_score >= 0.00 AND inherent_risk_score <= 100.00", name="chk_dpia_irs_bounds"),
        sa.CheckConstraint("residual_risk_score >= 0.00 AND residual_risk_score <= 100.00", name="chk_dpia_rrs_bounds"),
        sa.CheckConstraint("dpo_reviewed_by_id IS NULL OR created_by_id != dpo_reviewed_by_id", name="chk_dpia_approval_sod"),
    )

    # ── 4. data_transfer_assessments ─────────────────────────────────────────
    op.create_table(
        "data_transfer_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("transfer_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "processing_activity_id",
            sa.Integer(),
            sa.ForeignKey("processing_activities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_country", sa.String(length=64), nullable=False, server_default="EU_EEA"),
        sa.Column("destination_country", sa.String(length=64), nullable=False),
        sa.Column(
            "destination_jurisdiction_tier",
            sa.Enum(
                "ADEQUATE_LOW_RISK",
                "MODERATE_SAFEGUARDS_REQUIRED",
                "HIGH_RISK_SURVEILLANCE",
                "PROHIBITED_TRANSFERS",
                name="jurisdictionrisktier",
            ),
            nullable=False,
            server_default="MODERATE_SAFEGUARDS_REQUIRED",
        ),
        sa.Column(
            "transfer_mechanism",
            sa.Enum(
                "ADEQUACY_DECISION",
                "STANDARD_CONTRACTUAL_CLAUSES_SCC",
                "BINDING_CORPORATE_RULES_BCR",
                "DEROGATION_EXPLICIT_CONSENT",
                "NONE_INTRA_EEA",
                name="transfermechanism",
            ),
            nullable=False,
            server_default="STANDARD_CONTRACTUAL_CLAUSES_SCC",
        ),
        sa.Column("supplementary_safeguards_description", sa.Text(), nullable=True),
        sa.Column("supplementary_measures_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("government_access_risk_score", sa.Numeric(5, 2), nullable=False, server_default="50.00"),
        sa.Column("legal_remedies_score", sa.Numeric(5, 2), nullable=False, server_default="50.00"),
        sa.Column("transfer_risk_index", sa.Numeric(5, 2), nullable=False, server_default="50.00"),
        sa.Column(
            "approval_status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "SUPERSEDED",
                name="privacyapprovalstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "requested_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audit_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "transfer_code", name="uq_transfer_assessment_org_code"),
        sa.CheckConstraint("transfer_risk_index >= 0.00 AND transfer_risk_index <= 100.00", name="chk_transfer_tri_bounds"),
        sa.CheckConstraint("approved_by_id IS NULL OR requested_by_id != approved_by_id", name="chk_transfer_approval_sod"),
    )


def downgrade() -> None:
    op.drop_table("data_transfer_assessments")
    op.drop_table("dpia_assessments")
    op.drop_table("processing_activities")
    op.drop_table("data_assets")
