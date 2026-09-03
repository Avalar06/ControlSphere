"""0020_regulatory_integration_continuous_grc - Phase 21 (REGULATORY-GRC), Phase 22 (INTEGRATION-GRC), Phase 23 (CONTINUOUS-GRC)

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Phase 21: Regulatory-GRC Tables ───────────────────────────────────────

    # 1. regulatory_sources
    op.create_table(
        "regulatory_sources",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("authority_type", sa.String(length=50), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("trust_tier", sa.String(length=50), nullable=False, server_default="OFFICIAL"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "source_code", name="uq_reg_source_org_code"),
    )
    op.create_index("ix_regulatory_sources_id", "regulatory_sources", ["id"])
    op.create_index("ix_regulatory_sources_org_id", "regulatory_sources", ["organization_id"])
    op.create_index("ix_regulatory_sources_source_code", "regulatory_sources", ["source_code"])

    # 2. regulatory_mandates
    op.create_table(
        "regulatory_mandates",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("regulatory_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mandate_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=False),
        sa.Column("legal_citation", sa.String(length=255), nullable=True),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("enforceability_level", sa.String(length=50), nullable=False, server_default="MANDATORY"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("frameworks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("sunset_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "mandate_code", name="uq_reg_mandate_org_code"),
    )
    op.create_index("ix_regulatory_mandates_id", "regulatory_mandates", ["id"])
    op.create_index("ix_regulatory_mandates_org_id", "regulatory_mandates", ["organization_id"])
    op.create_index("ix_regulatory_mandates_mandate_code", "regulatory_mandates", ["mandate_code"])

    # 3. regulatory_versions
    op.create_table(
        "regulatory_versions",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mandate_id", sa.Integer(), sa.ForeignKey("regulatory_mandates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("sunset_date", sa.Date(), nullable=True),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "mandate_id", "version_code", name="uq_reg_version_org_mandate_code"),
    )
    op.create_index("ix_regulatory_versions_id", "regulatory_versions", ["id"])
    op.create_index("ix_regulatory_versions_org_id", "regulatory_versions", ["organization_id"])
    op.create_index("ix_regulatory_versions_mandate_id", "regulatory_versions", ["mandate_id"])

    # 4. regulatory_obligations
    op.create_table(
        "regulatory_obligations",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mandate_id", sa.Integer(), sa.ForeignKey("regulatory_mandates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("regulatory_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("obligation_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("article_reference", sa.String(length=100), nullable=True),
        sa.Column("applicability", sa.String(length=50), nullable=False, server_default="APPLICABLE"),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("compliance_status", sa.String(length=50), nullable=False, server_default="NEEDS_REVIEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "mandate_id", "obligation_code", name="uq_reg_obligation_org_mandate_code"),
    )
    op.create_index("ix_regulatory_obligations_id", "regulatory_obligations", ["id"])
    op.create_index("ix_regulatory_obligations_org_id", "regulatory_obligations", ["organization_id"])
    op.create_index("ix_regulatory_obligations_mandate_id", "regulatory_obligations", ["mandate_id"])
    op.create_index("ix_regulatory_obligations_control_id", "regulatory_obligations", ["organization_control_id"])

    # 5. regulatory_change_events
    op.create_table(
        "regulatory_change_events",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mandate_id", sa.Integer(), sa.ForeignKey("regulatory_mandates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False, server_default="AMENDMENT"),
        sa.Column("severity", sa.String(length=50), nullable=False, server_default="MAJOR"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="STAGED"),
        sa.Column("official_publication_date", sa.Date(), nullable=False),
        sa.Column("enforcement_date", sa.Date(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("content_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("raw_summary", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("dismissal_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "change_code", name="uq_reg_change_org_code"),
        sa.UniqueConstraint("organization_id", "content_hash_sha256", name="uq_reg_change_org_hash"),
    )
    op.create_index("ix_regulatory_change_events_id", "regulatory_change_events", ["id"])
    op.create_index("ix_regulatory_change_events_org_id", "regulatory_change_events", ["organization_id"])
    op.create_index("ix_regulatory_change_events_mandate_id", "regulatory_change_events", ["mandate_id"])
    op.create_index("ix_regulatory_change_events_hash", "regulatory_change_events", ["content_hash_sha256"])

    # 6. regulatory_impact_assessments
    op.create_table(
        "regulatory_impact_assessments",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_event_id", sa.Integer(), sa.ForeignKey("regulatory_change_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("impact_level", sa.String(length=50), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("impacted_control_ids", sa.Text(), nullable=True),
        sa.Column("impacted_policy_ids", sa.Text(), nullable=True),
        sa.Column("gap_analysis_summary", sa.Text(), nullable=False),
        sa.Column("action_plan", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "assessment_code", name="uq_reg_impact_org_code"),
    )
    op.create_index("ix_regulatory_impact_assessments_id", "regulatory_impact_assessments", ["id"])
    op.create_index("ix_regulatory_impact_assessments_org_id", "regulatory_impact_assessments", ["organization_id"])
    op.create_index("ix_regulatory_impact_assessments_change_id", "regulatory_impact_assessments", ["change_event_id"])

    # ── Phase 22: Integration-GRC Tables ──────────────────────────────────────

    # 7. integration_providers (Global catalog)
    op.create_table(
        "integration_providers",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("provider_type", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("supported_scopes", sa.Text(), nullable=False),
        sa.Column("allowed_domains", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_integration_providers_id", "integration_providers", ["id"])
    op.create_index("ix_integration_providers_provider_type", "integration_providers", ["provider_type"])

    # 8. integration_connections
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("integration_providers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("connection_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("granted_scopes", sa.Text(), nullable=False),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_status", sa.String(length=50), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "connection_code", name="uq_intg_conn_org_code"),
    )
    op.create_index("ix_integration_connections_id", "integration_connections", ["id"])
    op.create_index("ix_integration_connections_org_id", "integration_connections", ["organization_id"])
    op.create_index("ix_integration_connections_provider_id", "integration_connections", ["provider_id"])

    # 9. integration_credentials
    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_integration_credentials_id", "integration_credentials", ["id"])
    op.create_index("ix_integration_credentials_org_id", "integration_credentials", ["organization_id"])
    op.create_index("ix_integration_credentials_connection_id", "integration_credentials", ["connection_id"])

    # 10. evidence_collection_jobs
    op.create_table(
        "evidence_collection_jobs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_requirement_id", sa.Integer(), sa.ForeignKey("evidence_requirements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("collector_type", sa.String(length=100), nullable=False),
        sa.Column("collection_parameters", sa.Text(), nullable=True),
        sa.Column("frequency_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_payload_bytes", sa.Integer(), nullable=False, server_default="10485760"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(length=50), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "job_code", name="uq_evid_job_org_code"),
    )
    op.create_index("ix_evidence_collection_jobs_id", "evidence_collection_jobs", ["id"])
    op.create_index("ix_evidence_collection_jobs_org_id", "evidence_collection_jobs", ["organization_id"])
    op.create_index("ix_evidence_collection_jobs_connection_id", "evidence_collection_jobs", ["connection_id"])
    op.create_index("ix_evidence_collection_jobs_control_id", "evidence_collection_jobs", ["organization_control_id"])

    # 11. evidence_collection_runs
    op.create_table(
        "evidence_collection_runs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("evidence_collection_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_item_id", sa.Integer(), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_system", sa.String(length=50), nullable=False),
        sa.Column("source_identifier", sa.String(length=255), nullable=False),
        sa.Column("source_version", sa.String(length=50), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("records_collected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_payload_storage_key", sa.String(length=500), nullable=True),
        sa.Column("validation_status", sa.String(length=50), nullable=False, server_default="UNVALIDATED"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("provenance_manifest", sa.Text(), nullable=True),
        sa.Column("triggered_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "run_code", name="uq_evid_run_org_code"),
    )
    op.create_index("ix_evidence_collection_runs_id", "evidence_collection_runs", ["id"])
    op.create_index("ix_evidence_collection_runs_org_id", "evidence_collection_runs", ["organization_id"])
    op.create_index("ix_evidence_collection_runs_job_id", "evidence_collection_runs", ["job_id"])

    # ── Phase 23: Continuous-GRC Tables ───────────────────────────────────────

    # 12. continuous_compliance_profiles
    op.create_table(
        "continuous_compliance_profiles",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("profile_name", sa.String(length=100), nullable=False, server_default="Default Enterprise Assurance Profile"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("evaluation_cadence_hours", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("drift_critical_threshold", sa.Float(), nullable=False, server_default="20.0"),
        sa.Column("drift_high_threshold", sa.Float(), nullable=False, server_default="15.0"),
        sa.Column("min_control_health_score", sa.Float(), nullable=False, server_default="70.0"),
        sa.Column("max_evidence_age_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("max_open_finding_sla_breach_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_trigger_capa_on_critical_drift", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_continuous_compliance_profiles_id", "continuous_compliance_profiles", ["id"])
    op.create_index("ix_continuous_compliance_profiles_org_id", "continuous_compliance_profiles", ["organization_id"])

    # 13. compliance_drift_records
    op.create_table(
        "compliance_drift_records",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_control_id", sa.Integer(), sa.ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=True),
        sa.Column("drift_code", sa.String(length=64), nullable=False),
        sa.Column("drift_vector", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("root_cause_metric", sa.String(length=255), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("observed_value", sa.Float(), nullable=True),
        sa.Column("remediation_plan_id", sa.Integer(), sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "drift_code", name="uq_comp_drift_org_code"),
    )
    op.create_index("ix_compliance_drift_records_id", "compliance_drift_records", ["id"])
    op.create_index("ix_compliance_drift_records_org_id", "compliance_drift_records", ["organization_id"])
    op.create_index("ix_compliance_drift_records_drift_vector", "compliance_drift_records", ["drift_vector"])
    op.create_index("ix_compliance_drift_records_severity", "compliance_drift_records", ["severity"])
    op.create_index("ix_compliance_drift_records_status", "compliance_drift_records", ["status"])

    # 14. continuous_assurance_snapshots
    op.create_table(
        "continuous_assurance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_code", sa.String(length=64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("overall_assurance_score", sa.Float(), nullable=False),
        sa.Column("controls_assurance_score", sa.Float(), nullable=False),
        sa.Column("evidence_pipeline_score", sa.Float(), nullable=False),
        sa.Column("regulatory_compliance_score", sa.Float(), nullable=False),
        sa.Column("remediation_sla_score", sa.Float(), nullable=False),
        sa.Column("cloud_identity_posture_score", sa.Float(), nullable=False),
        sa.Column("harmonized_frameworks_score", sa.Float(), nullable=False),
        sa.Column("active_drift_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_drift_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pillar_breakdown", sa.Text(), nullable=False),
        sa.Column("framework_compliance_breakdown", sa.Text(), nullable=False),
        sa.Column("data_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("calculation_version", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("organization_id", "snapshot_code", name="uq_assur_snap_org_code"),
    )
    op.create_index("ix_continuous_assurance_snapshots_id", "continuous_assurance_snapshots", ["id"])
    op.create_index("ix_continuous_assurance_snapshots_org_id", "continuous_assurance_snapshots", ["organization_id"])
    op.create_index("ix_continuous_assurance_snapshots_code", "continuous_assurance_snapshots", ["snapshot_code"])


def downgrade() -> None:
    op.drop_table("continuous_assurance_snapshots")
    op.drop_table("compliance_drift_records")
    op.drop_table("continuous_compliance_profiles")
    op.drop_table("evidence_collection_runs")
    op.drop_table("evidence_collection_jobs")
    op.drop_table("integration_credentials")
    op.drop_table("integration_connections")
    op.drop_table("integration_providers")
    op.drop_table("regulatory_impact_assessments")
    op.drop_table("regulatory_change_events")
    op.drop_table("regulatory_obligations")
    op.drop_table("regulatory_versions")
    op.drop_table("regulatory_mandates")
    op.drop_table("regulatory_sources")
