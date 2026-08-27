"""0012_quantum_grc - Phase 12 Cyber Risk Quantification, Loss Modeling & Return on Security Investment (ROSI)
Revision ID: 0012
Revises: 0011
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. quant_risk_scenarios ───────────────────────────────────────────────
    op.create_table(
        "quant_risk_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("scenario_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "FROZEN",
                "ARCHIVED",
                name="scenariostatusenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "threat_actor_category",
            sa.Enum(
                "CYBERCRIMINAL",
                "NATION_STATE",
                "INSIDER",
                "HACKTIVIST",
                "ACCIDENTAL",
                name="threatactorcategoryenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "risk_id",
            sa.Integer(),
            sa.ForeignKey("risks.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "organization_control_id",
            sa.Integer(),
            sa.ForeignKey("organization_controls.id", ondelete="SET NULL"),
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
        sa.Column("tef_min", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tef_mode", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("tef_max", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("tcap", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("pl_min", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pl_mode", sa.Float(), nullable=False, server_default="10000.0"),
        sa.Column("pl_max", sa.Float(), nullable=False, server_default="50000.0"),
        sa.Column("sl_min", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("sl_mode", sa.Float(), nullable=False, server_default="5000.0"),
        sa.Column("sl_max", sa.Float(), nullable=False, server_default="20000.0"),
        sa.Column("slop", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("control_strength", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("vulnerability_factor", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("loss_event_frequency", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("single_loss_expectancy", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("annualized_loss_expectancy", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("var_95_parametric", sa.Float(), nullable=True),
        sa.Column("var_99_parametric", sa.Float(), nullable=True),
        sa.Column("var_95_empirical", sa.Float(), nullable=True),
        sa.Column("var_99_empirical", sa.Float(), nullable=True),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_ccm_stale", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("calculation_version", sa.String(length=32), nullable=False, server_default="2026.12.1"),
        sa.Column("input_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
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
            "scenario_code",
            name="uq_quant_scenario_code_per_tenant",
        ),
        sa.CheckConstraint(
            "tef_min >= 0 AND tef_min <= tef_mode AND tef_mode <= tef_max",
            name="chk_tef_pert_order",
        ),
        sa.CheckConstraint(
            "pl_min >= 0 AND pl_min <= pl_mode AND pl_mode <= pl_max",
            name="chk_pl_pert_order",
        ),
        sa.CheckConstraint(
            "sl_min >= 0 AND sl_min <= sl_mode AND sl_mode <= sl_max",
            name="chk_sl_pert_order",
        ),
        sa.CheckConstraint("tcap >= 0.0 AND tcap <= 1.0", name="chk_tcap_range"),
        sa.CheckConstraint("slop >= 0.0 AND slop <= 1.0", name="chk_slop_range"),
        sa.CheckConstraint(
            "control_strength >= 0.0 AND control_strength <= 1.0",
            name="chk_cs_range",
        ),
        sa.CheckConstraint(
            "vulnerability_factor >= 0.0 AND vulnerability_factor <= 1.0",
            name="chk_vuln_range",
        ),
        sa.CheckConstraint("loss_event_frequency >= 0.0", name="chk_lef_non_negative"),
        sa.CheckConstraint("single_loss_expectancy >= 0.0", name="chk_sle_non_negative"),
        sa.CheckConstraint("annualized_loss_expectancy >= 0.0", name="chk_ale_non_negative"),
    )

    # ── 2. quant_simulation_runs ──────────────────────────────────────────────
    op.create_table(
        "quant_simulation_runs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "scenario_id",
            sa.Integer(),
            sa.ForeignKey("quant_risk_scenarios.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("trial_count", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("simulation_seed", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False, server_default="SIM_PERT_V1"),
        sa.Column("mean_loss", sa.Float(), nullable=False),
        sa.Column("variance_loss", sa.Float(), nullable=False),
        sa.Column("std_dev_loss", sa.Float(), nullable=False),
        sa.Column("percentile_10", sa.Float(), nullable=False),
        sa.Column("percentile_50", sa.Float(), nullable=False),
        sa.Column("percentile_90", sa.Float(), nullable=False),
        sa.Column("percentile_95", sa.Float(), nullable=False),
        sa.Column("percentile_99", sa.Float(), nullable=False),
        sa.Column(
            "simulated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "simulated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.CheckConstraint(
            "trial_count >= 100 AND trial_count <= 50000",
            name="chk_simulation_trial_count_bounds",
        ),
        sa.CheckConstraint("mean_loss >= 0.0", name="chk_sim_mean_non_negative"),
        sa.CheckConstraint(
            "percentile_10 >= 0.0 AND percentile_10 <= percentile_50 AND percentile_50 <= percentile_90 AND percentile_90 <= percentile_95 AND percentile_95 <= percentile_99",
            name="chk_sim_percentiles_order",
        ),
    )

    # ── 3. rosi_analyses ──────────────────────────────────────────────────────
    op.create_table(
        "rosi_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "scenario_id",
            sa.Integer(),
            sa.ForeignKey("quant_risk_scenarios.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("remediation_cost", sa.Float(), nullable=False),
        sa.Column("current_ale", sa.Float(), nullable=False),
        sa.Column("projected_ale", sa.Float(), nullable=False),
        sa.Column("risk_reduction_ale", sa.Float(), nullable=False),
        sa.Column("net_economic_benefit", sa.Float(), nullable=False),
        sa.Column("rosi_percentage", sa.Float(), nullable=False),
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
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.CheckConstraint("remediation_cost > 0.0", name="chk_rosi_remediation_cost_positive"),
        sa.CheckConstraint("current_ale >= 0.0", name="chk_rosi_current_ale_non_negative"),
        sa.CheckConstraint("projected_ale >= 0.0", name="chk_rosi_projected_ale_non_negative"),
    )

    # ── 4. financial_risk_appetites ───────────────────────────────────────────
    op.create_table(
        "financial_risk_appetites",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ale_limit", sa.Float(), nullable=False),
        sa.Column("var_95_limit", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "APPROVED",
                "SUPERSEDED",
                name="appetitestatusenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "organization_id",
            "version",
            name="uq_appetite_version_per_tenant",
        ),
        sa.CheckConstraint("ale_limit >= 0.0", name="chk_appetite_ale_limit_non_negative"),
        sa.CheckConstraint("var_95_limit >= 0.0", name="chk_appetite_var_limit_non_negative"),
    )


def downgrade() -> None:
    op.drop_table("financial_risk_appetites")
    op.drop_table("rosi_analyses")
    op.drop_table("quant_simulation_runs")
    op.drop_table("quant_risk_scenarios")
