"""0007_continuous_control_monitoring - Phase 7 Continuous Control Monitoring & Health Telemetry

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── control_health_snapshots ─────────────────────────────────────────────
    op.create_table(
        "control_health_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("health_score", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("health_status", sa.Enum("HEALTHY", "DEGRADED", "AT_RISK", "FAILING", name="controlhealthstatusenum"), nullable=False, server_default="HEALTHY", index=True),
        sa.Column("evidence_freshness_score", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("assessment_currency_score", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("finding_penalty_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("exception_penalty_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("active_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_high_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_exceptions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("days_since_last_evidence", sa.Integer(), nullable=True),
        sa.Column("days_since_last_assessment", sa.Integer(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("evaluation_trigger", sa.Enum("SCHEDULED", "MANUAL", "EVENT_DRIVEN", name="evaluationtriggerenum"), nullable=False, server_default="MANUAL"),
    )

    # ── compliance_drift_alerts ──────────────────────────────────────────────
    op.create_table(
        "compliance_drift_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("alert_type", sa.Enum("EVIDENCE_EXPIRED", "EVIDENCE_MISSING", "ASSESSMENT_OVERDUE", "CRITICAL_FINDING_SLA_BREACH", "EXCEPTION_EXPIRING_SOON", "EXCEPTION_EXPIRED", "CONTROL_DEGRADED", name="driftalerttypeenum"), nullable=False, index=True),
        sa.Column("severity", sa.Enum("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="driftalertseverityenum"), nullable=False, index=True),
        sa.Column("status", sa.Enum("ACTIVE", "ACKNOWLEDGED", "RESOLVED", "DISMISSED", name="driftalertstatusenum"), nullable=False, server_default="ACTIVE", index=True),
        sa.Column("title", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("remediation_guidance", sa.Text(), nullable=True),
        sa.Column("acknowledged_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── monitoring_schedules ─────────────────────────────────────────────────
    op.create_table(
        "monitoring_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("frequency_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("evidence_max_age_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("assessment_max_age_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("exception_warning_window_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("finding_sla_critical_days", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("finding_sla_high_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("monitoring_schedules")
    op.drop_table("compliance_drift_alerts")
    op.drop_table("control_health_snapshots")
