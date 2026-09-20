"""0023_kri_and_risk_appetite_governance - Batch 2 (KRI-APPETITE-GRC)

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create risk_appetite_statements ─────────────────────────────────────
    op.create_table(
        "risk_appetite_statements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("statement_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False, index=True),
        sa.Column("category_appetites", sa.JSON(), nullable=False),
        sa.Column(
            "financial_risk_appetite_id",
            sa.Integer(),
            sa.ForeignKey("financial_risk_appetites.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
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
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False, index=True),
        sa.Column("review_cadence_months", sa.Integer(), server_default="12", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "statement_code", name="uq_appetite_statement_code_per_tenant"),
    )

    # ── 2. Create key_risk_indicators ─────────────────────────────────────────
    op.create_table(
        "key_risk_indicators",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kri_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_category", sa.String(length=64), nullable=False, index=True),
        sa.Column("unit_of_measure", sa.String(length=32), nullable=False),
        sa.Column("frequency", sa.String(length=32), server_default="DAILY", nullable=False, index=True),
        sa.Column("direction", sa.String(length=32), server_default="LOWER_IS_BETTER", nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False, index=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("latest_value", sa.Float(), nullable=True),
        sa.Column("latest_observed_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("latest_evaluation_status", sa.String(length=32), server_default="NORMAL", nullable=False, index=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "kri_code", name="uq_kri_code_per_tenant"),
    )

    # ── 3. Create kri_thresholds ──────────────────────────────────────────────
    op.create_table(
        "kri_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "kri_id",
            sa.Integer(),
            sa.ForeignKey("key_risk_indicators.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False, index=True),
        sa.Column("warning_threshold", sa.Float(), nullable=False),
        sa.Column("critical_threshold", sa.Float(), nullable=False),
        sa.Column("range_min_warning", sa.Float(), nullable=True),
        sa.Column("range_max_warning", sa.Float(), nullable=True),
        sa.Column("range_min_critical", sa.Float(), nullable=True),
        sa.Column("range_max_critical", sa.Float(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kri_id", "version", name="uq_kri_threshold_version"),
    )

    # ── 4. Create kri_observations ────────────────────────────────────────────
    op.create_table(
        "kri_observations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "kri_id",
            sa.Integer(),
            sa.ForeignKey("key_risk_indicators.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("source_type", sa.String(length=64), server_default="MANUAL_ENTRY", nullable=False, index=True),
        sa.Column("source_identifier", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True, index=True),
        sa.Column("data_hash_sha256", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── 5. Create kri_breach_records ──────────────────────────────────────────
    op.create_table(
        "kri_breach_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "kri_id",
            sa.Integer(),
            sa.ForeignKey("key_risk_indicators.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("breach_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "threshold_id",
            sa.Integer(),
            sa.ForeignKey("kri_thresholds.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "trigger_observation_id",
            sa.Integer(),
            sa.ForeignKey("kri_observations.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "latest_observation_id",
            sa.Integer(),
            sa.ForeignKey("kri_observations.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(length=32), server_default="DETECTED", nullable=False, index=True),
        sa.Column("breach_value", sa.Float(), nullable=False),
        sa.Column("peak_value", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "escalated_finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "closed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("closure_notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("organization_id", "breach_code", name="uq_kri_breach_code_per_tenant"),
    )

    # ── 6. Create kri_risk_links ──────────────────────────────────────────────
    op.create_table(
        "kri_risk_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "kri_id",
            sa.Integer(),
            sa.ForeignKey("key_risk_indicators.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "risk_id",
            sa.Integer(),
            sa.ForeignKey("risks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("correlation_weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kri_id", "risk_id", name="uq_kri_risk_link"),
        sa.CheckConstraint(
            "correlation_weight >= -1.0 AND correlation_weight <= 1.0",
            name="chk_kri_risk_correlation_weight",
        ),
    )


def downgrade() -> None:
    op.drop_table("kri_risk_links")
    op.drop_table("kri_breach_records")
    op.drop_table("kri_observations")
    op.drop_table("kri_thresholds")
    op.drop_table("key_risk_indicators")
    op.drop_table("risk_appetite_statements")
