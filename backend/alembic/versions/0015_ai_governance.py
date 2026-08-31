"""0015_ai_governance - Phase 15 Artificial Intelligence Governance & Algorithmic Risk Management (AI-GRC)
Revision ID: 0015
Revises: 0014
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. ai_systems ────────────────────────────────────────────────────────
    op.create_table(
        "ai_systems",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("system_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "system_type",
            sa.Enum(
                "LLM_APPLICATION",
                "AGENTIC_WORKFLOW",
                "EMBEDDED_ML",
                "COMPUTER_VISION",
                "RECOMMENDER",
                "PREDICTIVE_ANALYTICS",
                name="aisystemtypeenum",
            ),
            nullable=False,
        ),
        sa.Column(
            "lifecycle_state",
            sa.Enum(
                "DEVELOPMENT",
                "VALIDATION",
                "ETHICAL_REVIEW",
                "APPROVED_STAGING",
                "PRODUCTION",
                "DECOMMISSIONED",
                "REJECTED",
                name="ailifecyclestateenum",
            ),
            nullable=False,
            server_default="DEVELOPMENT",
        ),
        sa.Column(
            "regulatory_tier",
            sa.Enum(
                "PROHIBITED",
                "HIGH_RISK",
                "GPAI_SYSTEMIC_RISK",
                "LIMITED_RISK",
                "MINIMAL_RISK",
                name="airegulatorytierenum",
            ),
            nullable=False,
        ),
        sa.Column(
            "autonomy_level",
            sa.Enum(
                "NO_AUTONOMY",
                "HUMAN_IN_THE_LOOP",
                "HUMAN_ON_THE_LOOP",
                "FULL_AUTONOMY",
                name="aiautonomylevelenum",
            ),
            nullable=False,
            server_default="HUMAN_IN_THE_LOOP",
        ),
        sa.Column(
            "data_sensitivity",
            sa.Enum(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "RESTRICTED_PII_PHI",
                name="aidatasensitivityenum",
            ),
            nullable=False,
            server_default="INTERNAL",
        ),
        sa.Column(
            "hosting_type",
            sa.Enum(
                "CLOUD_THIRD_PARTY",
                "ON_PREMISE_SELF_HOSTED",
                "HYBRID_VPC",
                "EDGE_DEVICE",
                name="aihostingtypeenum",
            ),
            nullable=False,
        ),
        # Technical Telemetry
        sa.Column("foundation_model_name", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("training_data_cutoff", sa.String(length=32), nullable=True),
        sa.Column("parameters_billion", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("context_window_tokens", sa.Integer(), nullable=True),
        sa.Column("compute_flops_exponent", sa.Numeric(precision=5, scale=2), nullable=True),
        # Authoritative Governance & Risk Scores
        sa.Column("algorithmic_risk_index", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("eu_compliance_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("is_prohibited_practice", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("requires_conformity_assessment", sa.Boolean(), nullable=False, server_default="0"),
        # Cross-Module Lineage
        sa.Column("business_process_id", sa.Integer(), sa.ForeignKey("business_processes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("remediation_plan_id", sa.Integer(), sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"), nullable=True, index=True),
        # Ownership & Audit
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "system_code", name="uq_ai_system_org_code"),
        sa.CheckConstraint("algorithmic_risk_index >= 0.00 AND algorithmic_risk_index <= 100.00", name="chk_ai_ari_bounds"),
        sa.CheckConstraint("eu_compliance_score >= 0.00 AND eu_compliance_score <= 100.00", name="chk_ai_eu_score_bounds"),
    )

    # ── 2. ai_model_cards ────────────────────────────────────────────────────
    op.create_table(
        "ai_model_cards",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ai_system_id",
            sa.Integer(),
            sa.ForeignKey("ai_systems.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("intended_use", sa.Text(), nullable=False),
        sa.Column("out_of_scope_uses", sa.Text(), nullable=True),
        sa.Column("bias_mitigation_notes", sa.Text(), nullable=True),
        sa.Column("training_data_provenance", sa.Text(), nullable=True),
        sa.Column("synthetic_data_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        # Safety & Accuracy Telemetry
        sa.Column("hallucination_rate_percent", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("prompt_injection_resistance_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column("toxicity_filter_efficiency_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column("benchmark_eval_dataset", sa.String(length=255), nullable=True),
        sa.Column("benchmark_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("ai_system_id", "version", name="uq_model_card_system_version"),
        sa.CheckConstraint("synthetic_data_percentage >= 0.00 AND synthetic_data_percentage <= 100.00", name="chk_synthetic_data_bounds"),
        sa.CheckConstraint("hallucination_rate_percent >= 0.00 AND hallucination_rate_percent <= 100.00", name="chk_hallucination_bounds"),
        sa.CheckConstraint("prompt_injection_resistance_score >= 0.00 AND prompt_injection_resistance_score <= 100.00", name="chk_prompt_injection_bounds"),
        sa.CheckConstraint("toxicity_filter_efficiency_score >= 0.00 AND toxicity_filter_efficiency_score <= 100.00", name="chk_toxicity_filter_bounds"),
    )

    # ── 3. ai_deployment_approvals ───────────────────────────────────────────
    op.create_table(
        "ai_deployment_approvals",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ai_system_id",
            sa.Integer(),
            sa.ForeignKey("ai_systems.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("target_environment", sa.String(length=32), nullable=False),
        sa.Column(
            "approval_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "WITHDRAWN", name="aiapprovalstatusenum"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("risk_acceptance_justification", sa.Text(), nullable=False),
        sa.Column("human_oversight_measures", sa.Text(), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("reviewed_by_id IS NULL OR requested_by_id != reviewed_by_id", name="chk_ai_approval_sod"),
    )


def downgrade() -> None:
    op.drop_table("ai_deployment_approvals")
    op.drop_table("ai_model_cards")
    op.drop_table("ai_systems")

    # Drop enums if using Postgres
    bind = op.get_bind()
    if bind.engine.name == "postgresql":
        sa.Enum(name="aiapprovalstatusenum").drop(bind, checkfirst=True)
        sa.Enum(name="aihostingtypeenum").drop(bind, checkfirst=True)
        sa.Enum(name="aidatasensitivityenum").drop(bind, checkfirst=True)
        sa.Enum(name="aiautonomylevelenum").drop(bind, checkfirst=True)
        sa.Enum(name="airegulatorytierenum").drop(bind, checkfirst=True)
        sa.Enum(name="ailifecyclestateenum").drop(bind, checkfirst=True)
        sa.Enum(name="aisystemtypeenum").drop(bind, checkfirst=True)
