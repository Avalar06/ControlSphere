"""tprm lifecycle subprocessor sla offboarding

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-27 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend security_exceptions with linked_vendor_id
    with op.batch_alter_table("security_exceptions") as batch_op:
        batch_op.add_column(sa.Column("linked_vendor_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_security_exceptions_linked_vendor_id",
            ["linked_vendor_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_security_exceptions_linked_vendor_id_vendors",
            "vendors",
            ["linked_vendor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 2. Extend vendor_assessment_items with closed-loop Finding/CAPA/Risk linkage
    with op.batch_alter_table("vendor_assessment_items") as batch_op:
        batch_op.add_column(sa.Column("linked_finding_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("linked_remediation_plan_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("linked_risk_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("escalated_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            "ix_vendor_assessment_items_linked_finding_id",
            ["linked_finding_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_vendor_assessment_items_linked_remediation_plan_id",
            ["linked_remediation_plan_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_vendor_assessment_items_linked_risk_id",
            ["linked_risk_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_vendor_assessment_items_linked_finding_id_findings",
            "findings",
            ["linked_finding_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_vendor_assessment_items_linked_remediation_plan_id_remediation_plans",
            "remediation_plans",
            ["linked_remediation_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_vendor_assessment_items_linked_risk_id_risks",
            "risks",
            ["linked_risk_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_vendor_assessment_items_escalated_by_id_users",
            "users",
            ["escalated_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 3. Extend vendors with Batch 6 telemetry counters
    with op.batch_alter_table("vendors") as batch_op:
        batch_op.add_column(
            sa.Column(
                "open_sla_breaches_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "approved_subprocessors_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "offboarding_completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    # 4. Create vendor_contracts
    op.create_table(
        "vendor_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("engagement_id", sa.Integer(), nullable=True),
        sa.Column("contract_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "contract_type",
            sa.Enum(
                "MSA",
                "DPA",
                "SLA_ADDENDUM",
                "SOW",
                "NDA",
                "BAA",
                "DORA_ICT_CONTRACT",
                name="vendorcontracttypeenum",
            ),
            nullable=False,
            server_default="MSA",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "UNDER_REVIEW",
                "APPROVED",
                "REJECTED",
                "ACTIVE",
                "EXPIRED",
                "TERMINATED",
                "SUPERSEDED",
                name="vendorcontractstatusenum",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "notice_period_days", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("dpa_included", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "right_to_audit_clause", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "subprocessor_authorization_clause",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "exit_strategy_clause", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "incident_notification_hours_clause", sa.Integer(), nullable=True
        ),
        sa.Column("governing_jurisdiction", sa.String(length=120), nullable=True),
        sa.Column(
            "regulatory_mandates_applicable", sa.String(length=255), nullable=True
        ),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("evidence_sha256_snapshot", sa.String(length=64), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["engagement_id"], ["vendor_engagements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "vendor_id",
            "contract_code",
            name="uq_vendor_contract_org_vendor_code",
        ),
        sa.CheckConstraint(
            "expiry_date IS NULL OR expiry_date > effective_date",
            name="chk_vendor_contract_dates",
        ),
        sa.CheckConstraint(
            "notice_period_days >= 0", name="chk_vendor_contract_notice_non_neg"
        ),
        sa.CheckConstraint(
            "approved_by_id IS NULL OR ((created_by_id IS NULL OR approved_by_id != created_by_id) "
            "AND (submitted_by_id IS NULL OR approved_by_id != submitted_by_id))",
            name="chk_vendor_contract_four_eyes",
        ),
    )
    op.create_index("ix_vendor_contracts_id", "vendor_contracts", ["id"], unique=False)
    op.create_index(
        "ix_vendor_contracts_organization_id",
        "vendor_contracts",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_vendor_id", "vendor_contracts", ["vendor_id"], unique=False
    )
    op.create_index(
        "ix_vendor_contracts_engagement_id",
        "vendor_contracts",
        ["engagement_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_contract_code",
        "vendor_contracts",
        ["contract_code"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_contract_type",
        "vendor_contracts",
        ["contract_type"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_status", "vendor_contracts", ["status"], unique=False
    )
    op.create_index(
        "ix_vendor_contracts_effective_date",
        "vendor_contracts",
        ["effective_date"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_expiry_date",
        "vendor_contracts",
        ["expiry_date"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_evidence_id",
        "vendor_contracts",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_created_by_id",
        "vendor_contracts",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_submitted_by_id",
        "vendor_contracts",
        ["submitted_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_contracts_approved_by_id",
        "vendor_contracts",
        ["approved_by_id"],
        unique=False,
    )

    # 5. Create vendor_subprocessors
    op.create_table(
        "vendor_subprocessors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("engagement_id", sa.Integer(), nullable=True),
        sa.Column("subprocessor_vendor_id", sa.Integer(), nullable=True),
        sa.Column("subprocessor_code", sa.String(length=64), nullable=False),
        sa.Column("subprocessor_name", sa.String(length=255), nullable=False),
        sa.Column("subprocessor_domain", sa.String(length=255), nullable=True),
        sa.Column("service_function", sa.String(length=255), nullable=False),
        sa.Column("hosting_region", sa.String(length=120), nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=False),
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
        sa.Column(
            "status",
            sa.Enum(
                "REGISTERED",
                "UNDER_REVIEW",
                "APPROVED",
                "SUSPENDED",
                "REJECTED",
                "TERMINATED",
                name="vendorsubprocessorstatusenum",
            ),
            nullable=False,
            server_default="REGISTERED",
        ),
        sa.Column(
            "contractual_flowdown_verified",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("evidence_sha256_snapshot", sa.String(length=64), nullable=True),
        sa.Column("linked_risk_id", sa.Integer(), nullable=True),
        sa.Column("registered_by_id", sa.Integer(), nullable=True),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["engagement_id"], ["vendor_engagements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subprocessor_vendor_id"], ["vendors.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["linked_risk_id"], ["risks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["registered_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "vendor_id",
            "subprocessor_code",
            name="uq_vendor_subprocessor_org_vendor_code",
        ),
        sa.CheckConstraint(
            "subprocessor_vendor_id IS NULL OR subprocessor_vendor_id != vendor_id",
            name="chk_subprocessor_no_self_ref",
        ),
        sa.CheckConstraint(
            "approved_by_id IS NULL OR ((registered_by_id IS NULL OR approved_by_id != registered_by_id) "
            "AND (submitted_by_id IS NULL OR approved_by_id != submitted_by_id))",
            name="chk_subprocessor_four_eyes",
        ),
    )
    op.create_index(
        "ix_vendor_subprocessors_id", "vendor_subprocessors", ["id"], unique=False
    )
    op.create_index(
        "ix_vendor_subprocessors_organization_id",
        "vendor_subprocessors",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_vendor_id",
        "vendor_subprocessors",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_engagement_id",
        "vendor_subprocessors",
        ["engagement_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_subprocessor_vendor_id",
        "vendor_subprocessors",
        ["subprocessor_vendor_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_subprocessor_code",
        "vendor_subprocessors",
        ["subprocessor_code"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_subprocessor_name",
        "vendor_subprocessors",
        ["subprocessor_name"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_subprocessor_domain",
        "vendor_subprocessors",
        ["subprocessor_domain"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_hosting_region",
        "vendor_subprocessors",
        ["hosting_region"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_criticality",
        "vendor_subprocessors",
        ["criticality"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_status",
        "vendor_subprocessors",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_evidence_id",
        "vendor_subprocessors",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_linked_risk_id",
        "vendor_subprocessors",
        ["linked_risk_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_registered_by_id",
        "vendor_subprocessors",
        ["registered_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_submitted_by_id",
        "vendor_subprocessors",
        ["submitted_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_approved_by_id",
        "vendor_subprocessors",
        ["approved_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_subprocessors_reviewed_by_id",
        "vendor_subprocessors",
        ["reviewed_by_id"],
        unique=False,
    )

    # 6. Create vendor_sla_obligations
    op.create_table(
        "vendor_sla_obligations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("engagement_id", sa.Integer(), nullable=True),
        sa.Column("linked_organization_control_id", sa.Integer(), nullable=True),
        sa.Column("obligation_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metric_type",
            sa.Enum(
                "AVAILABILITY_PCT",
                "AVAILABILITY_UPTIME",
                "INCIDENT_NOTIFICATION_HOURS",
                "VULN_REMEDIATION_DAYS",
                "CRITICAL_VULN_REMEDIATION_DAYS",
                "HIGH_VULN_REMEDIATION_DAYS",
                "RTO_HOURS",
                "RPO_HOURS",
                "AUDIT_REPORT_DELIVERY_DAYS",
                "EVIDENCE_ATTESTATION_DAYS",
                "DATA_DELETION_DAYS",
                "DATA_DELETION_CERTIFICATION_DAYS",
                "CUSTOM_METRIC",
                name="vendorslametrictypeenum",
            ),
            nullable=False,
            server_default="AVAILABILITY_PCT",
        ),
        sa.Column(
            "comparison_operator",
            sa.Enum("GTE", "LTE", "EQ", name="vendorslacomparisonoperatorenum"),
            nullable=False,
            server_default="GTE",
        ),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("tolerance_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="PERCENT"),
        sa.Column(
            "measurement_window",
            sa.String(length=64),
            nullable=False,
            server_default="MONTHLY",
        ),
        sa.Column(
            "measurement_frequency_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "breach_severity_on_miss",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "MAJOR",
                "MINOR",
                name="vendorslabreachseverityenum",
            ),
            nullable=False,
            server_default="HIGH",
        ),
        sa.Column("contract_clause_ref", sa.String(length=120), nullable=True),
        sa.Column("penalty_clause_summary", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "SUSPENDED",
                "EXPIRED",
                "RETIRED",
                name="vendorslaobligationstatusenum",
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["contract_id"], ["vendor_contracts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["engagement_id"], ["vendor_engagements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["linked_organization_control_id"],
            ["organization_controls.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "vendor_id",
            "obligation_code",
            name="uq_vendor_sla_obligation_org_vendor_code",
        ),
        sa.CheckConstraint(
            "target_value >= 0.0", name="chk_sla_obligation_target_non_neg"
        ),
    )
    op.create_index(
        "ix_vendor_sla_obligations_id", "vendor_sla_obligations", ["id"], unique=False
    )
    op.create_index(
        "ix_vendor_sla_obligations_organization_id",
        "vendor_sla_obligations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_vendor_id",
        "vendor_sla_obligations",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_contract_id",
        "vendor_sla_obligations",
        ["contract_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_engagement_id",
        "vendor_sla_obligations",
        ["engagement_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_linked_organization_control_id",
        "vendor_sla_obligations",
        ["linked_organization_control_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_obligation_code",
        "vendor_sla_obligations",
        ["obligation_code"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_metric_type",
        "vendor_sla_obligations",
        ["metric_type"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_status",
        "vendor_sla_obligations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_obligations_created_by_id",
        "vendor_sla_obligations",
        ["created_by_id"],
        unique=False,
    )

    # 7. Create vendor_sla_breaches
    op.create_table(
        "vendor_sla_breaches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("obligation_id", sa.Integer(), nullable=False),
        sa.Column("breach_code", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_value_snapshot", sa.Float(), nullable=False),
        sa.Column("tolerance_value_snapshot", sa.Float(), nullable=True),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("variance_magnitude", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("service_credit_amount", sa.Float(), nullable=True),
        sa.Column(
            "comparison_operator_snapshot",
            sa.Enum("GTE", "LTE", "EQ", name="vendorslacomparisonoperatorenum"),
            nullable=False,
            server_default="GTE",
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "MAJOR",
                "MINOR",
                name="vendorslabreachseverityenum",
            ),
            nullable=False,
            server_default="HIGH",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "UNDER_INVESTIGATION",
                "ESCALATED",
                "ESCALATED_TO_FINDING",
                "WAIVED",
                "WAIVED_BY_EXCEPTION",
                "RESOLVED",
                "VERIFIED_CLOSED",
                name="vendorslabreachstatusenum",
            ),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("root_cause_summary", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("evidence_sha256_snapshot", sa.String(length=64), nullable=True),
        sa.Column("linked_finding_id", sa.Integer(), nullable=True),
        sa.Column("linked_remediation_plan_id", sa.Integer(), nullable=True),
        sa.Column("linked_risk_id", sa.Integer(), nullable=True),
        sa.Column("linked_exception_id", sa.Integer(), nullable=True),
        sa.Column("reported_by_id", sa.Integer(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_by_id", sa.Integer(), nullable=True),
        sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("closed_by_id", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closure_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["obligation_id"], ["vendor_sla_obligations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["linked_finding_id"], ["findings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["linked_remediation_plan_id"],
            ["remediation_plans.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["linked_risk_id"], ["risks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["linked_exception_id"],
            ["security_exceptions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["waived_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "vendor_id",
            "breach_code",
            name="uq_vendor_sla_breach_org_vendor_code",
        ),
        sa.CheckConstraint(
            "waived_by_id IS NULL OR reported_by_id IS NULL OR waived_by_id != reported_by_id",
            name="chk_sla_breach_waiver_four_eyes",
        ),
        sa.CheckConstraint(
            "closed_by_id IS NULL OR ((reported_by_id IS NULL OR closed_by_id != reported_by_id) "
            "AND (resolved_by_id IS NULL OR closed_by_id != resolved_by_id))",
            name="chk_sla_breach_close_four_eyes",
        ),
    )
    op.create_index(
        "ix_vendor_sla_breaches_id", "vendor_sla_breaches", ["id"], unique=False
    )
    op.create_index(
        "ix_vendor_sla_breaches_organization_id",
        "vendor_sla_breaches",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_vendor_id",
        "vendor_sla_breaches",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_obligation_id",
        "vendor_sla_breaches",
        ["obligation_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_breach_code",
        "vendor_sla_breaches",
        ["breach_code"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_occurred_at",
        "vendor_sla_breaches",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_severity",
        "vendor_sla_breaches",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_status",
        "vendor_sla_breaches",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_evidence_id",
        "vendor_sla_breaches",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_linked_finding_id",
        "vendor_sla_breaches",
        ["linked_finding_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_linked_remediation_plan_id",
        "vendor_sla_breaches",
        ["linked_remediation_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_linked_risk_id",
        "vendor_sla_breaches",
        ["linked_risk_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_linked_exception_id",
        "vendor_sla_breaches",
        ["linked_exception_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_reported_by_id",
        "vendor_sla_breaches",
        ["reported_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_resolved_by_id",
        "vendor_sla_breaches",
        ["resolved_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_waived_by_id",
        "vendor_sla_breaches",
        ["waived_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_sla_breaches_closed_by_id",
        "vendor_sla_breaches",
        ["closed_by_id"],
        unique=False,
    )

    # 8. Create vendor_offboarding_records
    op.create_table(
        "vendor_offboarding_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("offboarding_code", sa.String(length=64), nullable=False),
        sa.Column(
            "target_vendor_status",
            sa.Enum(
                "OFFBOARDED",
                "TERMINATED",
                name="vendoroffboardingtargetstatusenum",
            ),
            nullable=False,
            server_default="OFFBOARDED",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "INITIATED",
                "IN_PROGRESS",
                "PENDING_SIGNOFF",
                "PENDING_VERIFICATION",
                "APPROVED",
                "REJECTED",
                "COMPLETED",
                "CANCELLED",
                name="vendoroffboardingstatusenum",
            ),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.Column("initiation_reason", sa.Text(), nullable=False),
        sa.Column("target_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "requires_data_destruction_proof",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("data_destruction_evidence_id", sa.Integer(), nullable=True),
        sa.Column("initiated_by_id", sa.Integer(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_id", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("closure_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("signoff_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["data_destruction_evidence_id"],
            ["evidence_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "vendor_id",
            "offboarding_code",
            name="uq_vendor_offboarding_org_vendor_code",
        ),
        sa.CheckConstraint(
            "(verified_by_id IS NULL OR ((initiated_by_id IS NULL OR verified_by_id != initiated_by_id) "
            "AND (submitted_by_id IS NULL OR verified_by_id != submitted_by_id))) "
            "AND (approved_by_id IS NULL OR ((initiated_by_id IS NULL OR approved_by_id != initiated_by_id) "
            "AND (submitted_by_id IS NULL OR approved_by_id != submitted_by_id)))",
            name="chk_offboarding_four_eyes",
        ),
    )
    op.create_index(
        "ix_vendor_offboarding_records_id",
        "vendor_offboarding_records",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_organization_id",
        "vendor_offboarding_records",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_vendor_id",
        "vendor_offboarding_records",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_offboarding_code",
        "vendor_offboarding_records",
        ["offboarding_code"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_status",
        "vendor_offboarding_records",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_data_destruction_evidence_id",
        "vendor_offboarding_records",
        ["data_destruction_evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_initiated_by_id",
        "vendor_offboarding_records",
        ["initiated_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_submitted_by_id",
        "vendor_offboarding_records",
        ["submitted_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_approved_by_id",
        "vendor_offboarding_records",
        ["approved_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_verified_by_id",
        "vendor_offboarding_records",
        ["verified_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_records_cancelled_by_id",
        "vendor_offboarding_records",
        ["cancelled_by_id"],
        unique=False,
    )

    # 9. Create vendor_offboarding_items
    op.create_table(
        "vendor_offboarding_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("offboarding_record_id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("step_key", sa.String(length=64), nullable=False),
        sa.Column(
            "step_type",
            sa.Enum(
                "ACCESS_REVOCATION",
                "DATA_DESTRUCTION_OR_RETURN",
                "DATA_RETURN_OR_DESTRUCTION",
                "ENGAGEMENT_TERMINATION",
                "SUBPROCESSOR_DISCONNECT",
                "EVIDENCE_ARCHIVAL",
                "FINAL_RISK_ARCHIVE",
                "FINANCIAL_CONTRACT_CLOSEOUT",
                "CONTRACT_TERMINATION_NOTICE",
                name="vendoroffboardingsteptypeenum",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "COMPLETED",
                "WAIVED",
                "WAIVED_BY_EXCEPTION",
                name="vendoroffboardingitemstatusenum",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("evidence_sha256_snapshot", sa.String(length=64), nullable=True),
        sa.Column("linked_exception_id", sa.Integer(), nullable=True),
        sa.Column("attestation_notes", sa.Text(), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("completed_by_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_by_id", sa.Integer(), nullable=True),
        sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["offboarding_record_id"],
            ["vendor_offboarding_records.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["linked_exception_id"],
            ["security_exceptions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["completed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["waived_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "offboarding_record_id",
            "step_key",
            name="uq_vendor_offboarding_item_step_key",
        ),
    )
    op.create_index(
        "ix_vendor_offboarding_items_id",
        "vendor_offboarding_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_organization_id",
        "vendor_offboarding_items",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_offboarding_record_id",
        "vendor_offboarding_items",
        ["offboarding_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_step_type",
        "vendor_offboarding_items",
        ["step_type"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_status",
        "vendor_offboarding_items",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_evidence_id",
        "vendor_offboarding_items",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_linked_exception_id",
        "vendor_offboarding_items",
        ["linked_exception_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_completed_by_id",
        "vendor_offboarding_items",
        ["completed_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendor_offboarding_items_waived_by_id",
        "vendor_offboarding_items",
        ["waived_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vendor_offboarding_items_waived_by_id",
        table_name="vendor_offboarding_items",
    )
    op.drop_index(
        "ix_vendor_offboarding_items_completed_by_id",
        table_name="vendor_offboarding_items",
    )
    op.drop_index(
        "ix_vendor_offboarding_items_linked_exception_id",
        table_name="vendor_offboarding_items",
    )
    op.drop_index(
        "ix_vendor_offboarding_items_evidence_id",
        table_name="vendor_offboarding_items",
    )
    op.drop_index(
        "ix_vendor_offboarding_items_status", table_name="vendor_offboarding_items"
    )
    op.drop_index(
        "ix_vendor_offboarding_items_step_type", table_name="vendor_offboarding_items"
    )
    op.drop_index(
        "ix_vendor_offboarding_items_offboarding_record_id",
        table_name="vendor_offboarding_items",
    )
    op.drop_index(
        "ix_vendor_offboarding_items_organization_id",
        table_name="vendor_offboarding_items",
    )
    op.drop_index(
        "ix_vendor_offboarding_items_id", table_name="vendor_offboarding_items"
    )
    op.drop_table("vendor_offboarding_items")

    op.drop_index(
        "ix_vendor_offboarding_records_cancelled_by_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_verified_by_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_approved_by_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_submitted_by_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_initiated_by_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_data_destruction_evidence_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_status",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_offboarding_code",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_vendor_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_organization_id",
        table_name="vendor_offboarding_records",
    )
    op.drop_index(
        "ix_vendor_offboarding_records_id", table_name="vendor_offboarding_records"
    )
    op.drop_table("vendor_offboarding_records")

    op.drop_index(
        "ix_vendor_sla_breaches_closed_by_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_waived_by_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_resolved_by_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_reported_by_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_linked_exception_id",
        table_name="vendor_sla_breaches",
    )
    op.drop_index(
        "ix_vendor_sla_breaches_linked_risk_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_linked_remediation_plan_id",
        table_name="vendor_sla_breaches",
    )
    op.drop_index(
        "ix_vendor_sla_breaches_linked_finding_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_evidence_id", table_name="vendor_sla_breaches"
    )
    op.drop_index("ix_vendor_sla_breaches_status", table_name="vendor_sla_breaches")
    op.drop_index("ix_vendor_sla_breaches_severity", table_name="vendor_sla_breaches")
    op.drop_index(
        "ix_vendor_sla_breaches_occurred_at", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_breach_code", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_obligation_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_vendor_id", table_name="vendor_sla_breaches"
    )
    op.drop_index(
        "ix_vendor_sla_breaches_organization_id", table_name="vendor_sla_breaches"
    )
    op.drop_index("ix_vendor_sla_breaches_id", table_name="vendor_sla_breaches")
    op.drop_table("vendor_sla_breaches")

    op.drop_index(
        "ix_vendor_sla_obligations_created_by_id",
        table_name="vendor_sla_obligations",
    )
    op.drop_index(
        "ix_vendor_sla_obligations_status", table_name="vendor_sla_obligations"
    )
    op.drop_index(
        "ix_vendor_sla_obligations_metric_type", table_name="vendor_sla_obligations"
    )
    op.drop_index(
        "ix_vendor_sla_obligations_obligation_code",
        table_name="vendor_sla_obligations",
    )
    op.drop_index(
        "ix_vendor_sla_obligations_linked_organization_control_id",
        table_name="vendor_sla_obligations",
    )
    op.drop_index(
        "ix_vendor_sla_obligations_engagement_id", table_name="vendor_sla_obligations"
    )
    op.drop_index(
        "ix_vendor_sla_obligations_contract_id",
        table_name="vendor_sla_obligations",
    )
    op.drop_index(
        "ix_vendor_sla_obligations_vendor_id", table_name="vendor_sla_obligations"
    )
    op.drop_index(
        "ix_vendor_sla_obligations_organization_id",
        table_name="vendor_sla_obligations",
    )
    op.drop_index("ix_vendor_sla_obligations_id", table_name="vendor_sla_obligations")
    op.drop_table("vendor_sla_obligations")

    op.drop_index(
        "ix_vendor_subprocessors_reviewed_by_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_approved_by_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_submitted_by_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_registered_by_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_linked_risk_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_evidence_id", table_name="vendor_subprocessors"
    )
    op.drop_index("ix_vendor_subprocessors_status", table_name="vendor_subprocessors")
    op.drop_index(
        "ix_vendor_subprocessors_criticality", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_hosting_region", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_subprocessor_domain",
        table_name="vendor_subprocessors",
    )
    op.drop_index(
        "ix_vendor_subprocessors_subprocessor_name", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_subprocessor_code", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_subprocessor_vendor_id",
        table_name="vendor_subprocessors",
    )
    op.drop_index(
        "ix_vendor_subprocessors_engagement_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_vendor_id", table_name="vendor_subprocessors"
    )
    op.drop_index(
        "ix_vendor_subprocessors_organization_id", table_name="vendor_subprocessors"
    )
    op.drop_index("ix_vendor_subprocessors_id", table_name="vendor_subprocessors")
    op.drop_table("vendor_subprocessors")

    op.drop_index(
        "ix_vendor_contracts_approved_by_id", table_name="vendor_contracts"
    )
    op.drop_index(
        "ix_vendor_contracts_submitted_by_id", table_name="vendor_contracts"
    )
    op.drop_index(
        "ix_vendor_contracts_created_by_id", table_name="vendor_contracts"
    )
    op.drop_index("ix_vendor_contracts_evidence_id", table_name="vendor_contracts")
    op.drop_index("ix_vendor_contracts_expiry_date", table_name="vendor_contracts")
    op.drop_index(
        "ix_vendor_contracts_effective_date", table_name="vendor_contracts"
    )
    op.drop_index("ix_vendor_contracts_status", table_name="vendor_contracts")
    op.drop_index(
        "ix_vendor_contracts_contract_type", table_name="vendor_contracts"
    )
    op.drop_index(
        "ix_vendor_contracts_contract_code", table_name="vendor_contracts"
    )
    op.drop_index(
        "ix_vendor_contracts_engagement_id", table_name="vendor_contracts"
    )
    op.drop_index("ix_vendor_contracts_vendor_id", table_name="vendor_contracts")
    op.drop_index(
        "ix_vendor_contracts_organization_id", table_name="vendor_contracts"
    )
    op.drop_index("ix_vendor_contracts_id", table_name="vendor_contracts")
    op.drop_table("vendor_contracts")

    with op.batch_alter_table("vendors") as batch_op:
        batch_op.drop_column("offboarding_completed_at")
        batch_op.drop_column("approved_subprocessors_count")
        batch_op.drop_column("open_sla_breaches_count")

    with op.batch_alter_table("vendor_assessment_items") as batch_op:
        batch_op.drop_constraint(
            "fk_vendor_assessment_items_escalated_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_vendor_assessment_items_linked_risk_id_risks", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_vendor_assessment_items_linked_remediation_plan_id_remediation_plans",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_vendor_assessment_items_linked_finding_id_findings",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_vendor_assessment_items_linked_risk_id")
        batch_op.drop_index("ix_vendor_assessment_items_linked_remediation_plan_id")
        batch_op.drop_index("ix_vendor_assessment_items_linked_finding_id")
        batch_op.drop_column("escalated_at")
        batch_op.drop_column("escalated_by_id")
        batch_op.drop_column("linked_risk_id")
        batch_op.drop_column("linked_remediation_plan_id")
        batch_op.drop_column("linked_finding_id")

    with op.batch_alter_table("security_exceptions") as batch_op:
        batch_op.drop_constraint(
            "fk_security_exceptions_linked_vendor_id_vendors", type_="foreignkey"
        )
        batch_op.drop_index("ix_security_exceptions_linked_vendor_id")
        batch_op.drop_column("linked_vendor_id")
