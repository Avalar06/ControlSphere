"""0011_remediation_orchestration - Phase 11 Governed Remediation Orchestration, Corrective Action Plans (CAPA) & Closed-Loop Assurance
Revision ID: 0011
Revises: 0010
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. remediation_plans ──────────────────────────────────────────────────
    op.create_table(
        "remediation_plans",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("plan_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column(
            "root_cause_classification",
            sa.Enum(
                "CONTROL_DEFICIENCY",
                "CONFIGURATION_DRIFT",
                "HUMAN_ERROR",
                "VENDOR_DEFAULT",
                "ARCHITECTURAL_GAP",
                name="remediationrootcauseclassificationenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_type",
            sa.Enum(
                "FINDING",
                "CCM_DRIFT",
                "SECURITY_INCIDENT",
                "TPRM_ASSESSMENT",
                "AUDIT",
                name="remediationsourcetypeenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "compliance_drift_alert_id",
            sa.Integer(),
            sa.ForeignKey("compliance_drift_alerts.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "security_incident_id",
            sa.Integer(),
            sa.ForeignKey("security_incidents.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "vendor_assessment_id",
            sa.Integer(),
            sa.ForeignKey("vendor_assessments.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audits.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                name="remediationseverityenum",
            ),
            nullable=False,
            server_default="MEDIUM",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "APPROVED",
                "IN_EXECUTION",
                "PENDING_VALIDATION",
                "VERIFIED_CLOSED",
                "CANCELLED",
                name="remediationstatusenum",
            ),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column(
            "plan_owner_id",
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_completion_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column(
            "verified_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_notes", sa.Text(), nullable=True),
        sa.Column("validation_attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rei_score", sa.Float(), nullable=True),
        sa.Column("ttr_hours", sa.Float(), nullable=True),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.UniqueConstraint("organization_id", "plan_code", name="uq_remediation_org_plan_code"),
        sa.CheckConstraint(
            """(
                (CASE WHEN finding_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN compliance_drift_alert_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN security_incident_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN vendor_assessment_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN audit_id IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1""",
            name="chk_remediation_single_source",
        ),
        sa.CheckConstraint(
            "validation_attempts_count >= 0", name="chk_remediation_validation_attempts_positive"
        ),
        sa.CheckConstraint(
            "rei_score IS NULL OR (rei_score >= 0.0 AND rei_score <= 100.0)",
            name="chk_remediation_rei_range",
        ),
        sa.CheckConstraint(
            "ttr_hours IS NULL OR ttr_hours >= 0.0", name="chk_remediation_ttr_positive"
        ),
    )

    # ── 2. remediation_tasks ──────────────────────────────────────────────────
    op.create_table(
        "remediation_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("task_seq", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "assignee_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
                name="taskstatusenum",
            ),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implementation_notes", sa.Text(), nullable=True),
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
            "remediation_plan_id", "task_seq", name="uq_remediation_task_plan_seq"
        ),
        sa.CheckConstraint("task_seq >= 1", name="chk_remediation_task_seq_positive"),
    )

    # ── 3. remediation_evidence_links ─────────────────────────────────────────
    op.create_table(
        "remediation_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "remediation_task_id",
            sa.Integer(),
            sa.ForeignKey("remediation_tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "verification_status",
            sa.Enum(
                "SUBMITTED",
                "VALIDATED",
                "REJECTED",
                name="evidenceverificationstatusenum",
            ),
            nullable=False,
            server_default="SUBMITTED",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "remediation_task_id", "evidence_id", name="uq_remediation_task_evidence"
        ),
    )

    # ── 4. remediation_retest_records ─────────────────────────────────────────
    op.create_table(
        "remediation_retest_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("test_executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tester_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "test_result",
            sa.Enum(
                "PASS",
                "FAIL",
                "INCONCLUSIVE",
                name="retestresultenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("metric_observed_value", sa.Float(), nullable=True),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("validation_narrative", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("remediation_retest_records")
    op.drop_table("remediation_evidence_links")
    op.drop_table("remediation_tasks")
    op.drop_table("remediation_plans")

    # Drop enum types on PostgreSQL
    for enum_type in [
        "retestresultenum",
        "evidenceverificationstatusenum",
        "taskstatusenum",
        "remediationstatusenum",
        "remediationseverityenum",
        "remediationsourcetypeenum",
        "remediationrootcauseclassificationenum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_type}")
