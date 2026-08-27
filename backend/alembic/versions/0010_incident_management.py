"""0010_incident_management - Phase 10 Security Incident Management & Regulatory Disclosure
Revision ID: 0010
Revises: 0009
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. security_incidents ──────────────────────────────────────────────────
    op.create_table(
        "security_incidents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("incident_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                name="incidentseverityenum",
            ),
            nullable=False,
            server_default="MEDIUM",
            index=True,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "RANSOMWARE",
                "DATA_BREACH",
                "UNAUTHORIZED_ACCESS",
                "DENIAL_OF_SERVICE",
                "INSIDER_THREAT",
                "SUPPLY_CHAIN_COMPROMISE",
                "OTHER",
                name="incidentcategoryenum",
            ),
            nullable=False,
            server_default="OTHER",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DECLARED",
                "TRIAGED",
                "CONTAINED",
                "ERADICATED",
                "RECOVERED",
                "POST_MORTEM",
                "CLOSED",
                name="incidentstatusenum",
            ),
            nullable=False,
            server_default="DECLARED",
            index=True,
        ),
        sa.Column(
            "incident_commander_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "business_owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "closed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eradicated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("post_mortem_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("affected_record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affected_systems_summary", sa.Text(), nullable=True),
        sa.Column("financial_impact_estimate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_material", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("materiality_determined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "materiality_determined_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "root_cause_classification",
            sa.Enum(
                "CONTROL_FAILURE",
                "HUMAN_ERROR",
                "ZERO_DAY",
                "THIRD_PARTY_FAILURE",
                "CONFIGURATION_DRIFT",
                name="rootcauseclassificationenum",
            ),
            nullable=True,
        ),
        sa.Column("root_cause_narrative", sa.Text(), nullable=True),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("closure_notes", sa.Text(), nullable=True),
        sa.Column(
            "compliance_drift_alert_id",
            sa.Integer(),
            sa.ForeignKey("compliance_drift_alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("organization_id", "incident_code", name="uq_tenant_incident_code"),
        sa.CheckConstraint("affected_record_count >= 0", name="ck_incident_affected_records_positive"),
        sa.CheckConstraint("financial_impact_estimate >= 0.0", name="ck_incident_financial_impact_positive"),
    )

    # ── 2. incident_disclosures ───────────────────────────────────────────────
    op.create_table(
        "incident_disclosures",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("security_incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "regulator",
            sa.Enum(
                "GDPR_DPA",
                "SEC_8K",
                "HHS_OCR",
                "PCI_SSC",
                "NYDFS",
                "STATE_AG",
                name="regulatorenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "NOT_APPLICABLE",
                "PENDING",
                "DUE",
                "NOTIFIED",
                "OVERDUE",
                name="disclosurestatusenum",
            ),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("rule_version", sa.String(length=16), nullable=False, server_default="1.0"),
        sa.Column("calculation_version", sa.String(length=16), nullable=False, server_default="1.0"),
        sa.Column(
            "trigger_type",
            sa.Enum(
                "INCIDENT_DETECTION",
                "MATERIALITY_DETERMINATION",
                "PHI_THRESHOLD_BREACH",
                "CDE_COMPROMISE",
                "LEGAL_DIRECTIVE",
                name="disclosuretriggertypeenum",
            ),
            nullable=False,
            server_default="INCIDENT_DETECTION",
        ),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "triggered_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "notified_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notification_reference_code", sa.String(length=128), nullable=True),
        sa.Column("exemption_reason", sa.Text(), nullable=True),
        sa.Column("disclosure_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "incident_id",
            "regulator",
            name="uq_tenant_incident_regulator",
        ),
    )

    # ── 3. incident_timeline_events ───────────────────────────────────────────
    op.create_table(
        "incident_timeline_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("security_incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "DETECTION",
                "CONTAINMENT_ACTION",
                "ERADICATION_STEP",
                "EVIDENCE_COLLECTED",
                "REGULATOR_NOTIFIED",
                "COMMAND_TRANSFER",
                "POST_MORTEM_NOTE",
                name="timelineeventtypeenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("event_occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "MANUAL_ENTRY",
                "SYSTEM_AUTOMATION",
                "CCM_DRIFT",
                "FORENSIC_LOG",
                name="timelineeventsourceenum",
            ),
            nullable=False,
            server_default="MANUAL_ENTRY",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── 4. incident_control_links ─────────────────────────────────────────────
    op.create_table(
        "incident_control_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("security_incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_control_id",
            sa.Integer(),
            sa.ForeignKey("organization_controls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "relationship_type",
            sa.Enum(
                "FAILED_CONTROL",
                "DEFICIENT_CONTROL",
                "CIRCUMVENTED_CONTROL",
                "DETECTING_CONTROL",
                name="incidentcontrolrelationshipenum",
            ),
            nullable=False,
            server_default="FAILED_CONTROL",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "incident_id",
            "organization_control_id",
            name="uq_tenant_incident_control",
        ),
    )

    # ── 5. incident_vendor_links ──────────────────────────────────────────────
    op.create_table(
        "incident_vendor_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("security_incidents.id", ondelete="CASCADE"),
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
            "vendor_engagement_id",
            sa.Integer(),
            sa.ForeignKey("vendor_engagements.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("is_vendor_originated", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "incident_id",
            "vendor_id",
            "vendor_engagement_id",
            name="uq_tenant_incident_vendor_engagement",
        ),
    )


def downgrade() -> None:
    op.drop_table("incident_vendor_links")
    op.drop_table("incident_control_links")
    op.drop_table("incident_timeline_events")
    op.drop_table("incident_disclosures")
    op.drop_table("security_incidents")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS incidentcontrolrelationshipenum CASCADE")
    op.execute("DROP TYPE IF EXISTS timelineeventsourceenum CASCADE")
    op.execute("DROP TYPE IF EXISTS timelineeventtypeenum CASCADE")
    op.execute("DROP TYPE IF EXISTS disclosuretriggertypeenum CASCADE")
    op.execute("DROP TYPE IF EXISTS disclosurestatusenum CASCADE")
    op.execute("DROP TYPE IF EXISTS regulatorenum CASCADE")
    op.execute("DROP TYPE IF EXISTS rootcauseclassificationenum CASCADE")
    op.execute("DROP TYPE IF EXISTS incidentstatusenum CASCADE")
    op.execute("DROP TYPE IF EXISTS incidentcategoryenum CASCADE")
    op.execute("DROP TYPE IF EXISTS incidentseverityenum CASCADE")
