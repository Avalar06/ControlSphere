"""0006_audit_management - Phase 6 Audit Management & Assurance Readiness

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── audits ──────────────────────────────────────────────────────────────
    op.create_table(
        "audits",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False, index=True),
        sa.Column("audit_type", sa.Enum("INTERNAL", "EXTERNAL", "REGULATORY", "COMPLIANCE", "OPERATIONAL", "TECHNICAL", "THIRD_PARTY", name="audittypeenum"), nullable=False, server_default="INTERNAL", index=True),
        sa.Column("audit_reference", sa.String(100), nullable=True, index=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("scope_description", sa.Text(), nullable=True),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("frameworks.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("lead_auditor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("audit_team_notes", sa.Text(), nullable=True),
        sa.Column("planned_start_date", sa.Date(), nullable=True, index=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True, index=True),
        sa.Column("actual_start_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum("PLANNED", "INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED", "CLOSED", name="auditstatusenum"), nullable=False, server_default="PLANNED", index=True),
        sa.Column("opinion", sa.Enum("UNISSUED", "UNQUALIFIED", "QUALIFIED", "ADVERSE", "DISCLAIMER", name="auditopinionenum"), nullable=False, server_default="UNISSUED", index=True),
        sa.Column("opinion_issued_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opinion_issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opinion_notes", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closure_notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── audit_scope_controls ─────────────────────────────────────────────────
    op.create_table(
        "audit_scope_controls",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scope_notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("audit_id", "organization_control_id", name="uq_audit_scope_control"),
    )

    # ── audit_procedures ─────────────────────────────────────────────────────
    op.create_table(
        "audit_procedures",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("title", sa.String(255), nullable=False, index=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("test_steps", sa.Text(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("actual_result", sa.Text(), nullable=True),
        sa.Column("assessment_method", sa.String(100), nullable=True),
        sa.Column("result", sa.Enum("NOT_STARTED", "IN_PROGRESS", "PASSED", "PARTIALLY_PASSED", "FAILED", "NOT_APPLICABLE", name="procedureresultenum"), nullable=False, server_default="NOT_STARTED", index=True),
        sa.Column("execution_notes", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("tester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("execution_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── audit_procedure_evidence ──────────────────────────────────────────────
    op.create_table(
        "audit_procedure_evidence",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("procedure_id", sa.Integer(), sa.ForeignKey("audit_procedures.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("link_notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("procedure_id", "evidence_id", name="uq_audit_procedure_evidence"),
    )

    # ── audit_finding_links ───────────────────────────────────────────────────
    op.create_table(
        "audit_finding_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("audit_id", sa.Integer(), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_procedure_id", sa.Integer(), sa.ForeignKey("audit_procedures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("link_notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("audit_id", "finding_id", name="uq_audit_finding_link"),
    )


def downgrade() -> None:
    op.drop_table("audit_finding_links")
    op.drop_table("audit_procedure_evidence")
    op.drop_table("audit_procedures")
    op.drop_table("audit_scope_controls")
    op.drop_table("audits")
