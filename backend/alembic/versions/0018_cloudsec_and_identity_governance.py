"""0018_cloudsec_and_identity_governance - Phase 18 (CLOUDSEC-GRC) & Phase 19 (IDENTITY-GRC)
Revision ID: 0018
Revises: 0017
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. cloud_assets ───────────────────────────────────────────────────────
    op.create_table(
        "cloud_assets",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("asset_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "provider",
            sa.Enum("AWS", "AZURE", "GCP", "OCI", "ALIBABA", name="cloudproviderenum"),
            nullable=False,
            server_default="AWS",
            index=True,
        ),
        sa.Column("account_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column(
            "resource_type",
            sa.Enum(
                "S3_BUCKET",
                "IAM_ROLE",
                "EC2_INSTANCE",
                "KUBERNETES_CLUSTER",
                "RDS_DATABASE",
                "KEY_VAULT",
                "SECURITY_GROUP",
                "SERVERLESS_FUNCTION",
                "CONTAINER_REGISTRY",
                "VIRTUAL_NETWORK",
                name="cloudassettypeenum",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("resource_arn", sa.String(length=512), nullable=False, index=True),
        sa.Column("resource_name", sa.String(length=255), nullable=False),
        sa.Column(
            "environment",
            sa.Enum("PRODUCTION", "STAGING", "DEVELOPMENT", "SANDBOX", name="cloudenvironmentenum"),
            nullable=False,
            server_default="PRODUCTION",
            index=True,
        ),
        sa.Column(
            "criticality",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="cloudcriticalityenum"),
            nullable=False,
            server_default="HIGH",
        ),
        sa.Column(
            "posture_status",
            sa.Enum("COMPLIANT", "NON_COMPLIANT", "DEVIATED", "UNASSESSED", name="cloudposturestatusenum"),
            nullable=False,
            server_default="UNASSESSED",
            index=True,
        ),
        sa.Column("posture_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column("blast_radius_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column(
            "lifecycle_state",
            sa.Enum("ACTIVE", "PROVISIONING", "MAINTENANCE", "DECOMMISSIONED", name="cloudlifecyclestateenum"),
            nullable=False,
            server_default="ACTIVE",
            index=True,
        ),
        sa.Column("is_internet_facing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("encryption_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "software_product_id",
            sa.Integer(),
            sa.ForeignKey("software_products.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("configuration_metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "asset_code", name="uq_cloud_asset_tenant_code"),
        sa.UniqueConstraint("organization_id", "resource_arn", name="uq_cloud_asset_tenant_arn"),
        sa.CheckConstraint("posture_score >= 0.00 AND posture_score <= 100.00", name="chk_cloud_asset_posture_score"),
        sa.CheckConstraint("blast_radius_score >= 0.00 AND blast_radius_score <= 100.00", name="chk_cloud_asset_blast_radius_score"),
    )

    # ── 2. cloud_security_benchmarks ──────────────────────────────────────────
    op.create_table(
        "cloud_security_benchmarks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("benchmark_code", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column(
            "framework",
            sa.Enum("CIS_AWS_FOUNDATIONS", "CIS_AZURE_FOUNDATIONS", "CIS_GCP_FOUNDATIONS", "NIST_SP_800_53_CLOUD", "SOC2_CLOUD_SECURITY", name="benchmarkframeworkenum"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "provider",
            sa.Enum("AWS", "AZURE", "GCP", "OCI", "ALIBABA", name="cloudproviderenum"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("total_rules_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 3. cloud_benchmark_rules ──────────────────────────────────────────────
    op.create_table(
        "cloud_benchmark_rules",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "benchmark_id",
            sa.Integer(),
            sa.ForeignKey("cloud_security_benchmarks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rule_code", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("section", sa.String(length=128), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="ruleseverityenum"),
            nullable=False,
            server_default="HIGH",
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("remediation_guidance", sa.Text(), nullable=True),
        sa.Column(
            "control_id",
            sa.Integer(),
            sa.ForeignKey("framework_subcategories.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── 4. cloud_security_findings ────────────────────────────────────────────
    op.create_table(
        "cloud_security_findings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("finding_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "cloud_asset_id",
            sa.Integer(),
            sa.ForeignKey("cloud_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("cloud_benchmark_rules.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evaluation_status",
            sa.Enum("PASSED", "FAILED", "SUPPRESSED", "REMEDIATED", name="evaluationstatusenum"),
            nullable=False,
            server_default="FAILED",
            index=True,
        ),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="ruleseverityenum"),
            nullable=False,
            server_default="HIGH",
            index=True,
        ),
        sa.Column("risk_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="50.00"),
        sa.Column("actual_value", sa.Text(), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "finding_code", name="uq_cloud_finding_tenant_code"),
        sa.CheckConstraint("risk_score >= 0.00 AND risk_score <= 100.00", name="chk_cloud_finding_risk_score"),
    )

    # ── 5. cloud_configuration_drifts ─────────────────────────────────────────
    op.create_table(
        "cloud_configuration_drifts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("drift_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "cloud_asset_id",
            sa.Integer(),
            sa.ForeignKey("cloud_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("attribute_path", sa.String(length=255), nullable=False),
        sa.Column("baseline_value", sa.Text(), nullable=False),
        sa.Column("drifted_value", sa.Text(), nullable=False),
        sa.Column(
            "drift_severity",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="driftseverityenum"),
            nullable=False,
            server_default="HIGH",
            index=True,
        ),
        sa.Column("drift_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="50.00"),
        sa.Column(
            "status",
            sa.Enum("DETECTED", "ACCEPTED_CHANGE", "REMEDIATING", "REVERTED", name="driftstatusenum"),
            nullable=False,
            server_default="DETECTED",
            index=True,
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "drift_code", name="uq_cloud_drift_tenant_code"),
        sa.CheckConstraint("drift_score >= 0.00 AND drift_score <= 100.00", name="chk_cloud_drift_score"),
    )

    # ── 6. cloud_iam_blast_radii ──────────────────────────────────────────────
    op.create_table(
        "cloud_iam_blast_radii",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("analysis_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "cloud_asset_id",
            sa.Integer(),
            sa.ForeignKey("cloud_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("iam_principal_arn", sa.String(length=512), nullable=False),
        sa.Column("effective_permissions_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("admin_privilege_granted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cross_account_access", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "data_access_scope",
            sa.Enum("FULL_DATASTORE", "RESTRICTED_READ", "METADATA_ONLY", name="dataaccessscopeenum"),
            nullable=False,
            server_default="RESTRICTED_READ",
        ),
        sa.Column("blast_radius_index", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column(
            "risk_band",
            sa.Enum("CRITICAL", "HIGH", "MODERATE", "LOW", name="blastradiusbandenum"),
            nullable=False,
            server_default="LOW",
        ),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "analysis_code", name="uq_cloud_blast_radius_tenant_code"),
        sa.CheckConstraint("blast_radius_index >= 0.00 AND blast_radius_index <= 100.00", name="chk_cloud_blast_radius_index"),
    )

    # ── 7. governed_identities ────────────────────────────────────────────────
    op.create_table(
        "governed_identities",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("identity_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("email", sa.String(length=255), nullable=False, index=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "identity_type",
            sa.Enum("WORKFORCE_EMPLOYEE", "CONTRACTOR", "SERVICE_ACCOUNT", "MACHINE_WORKLOAD", "EXTERNAL_PARTNER", name="identitytypeenum"),
            nullable=False,
            server_default="WORKFORCE_EMPLOYEE",
            index=True,
        ),
        sa.Column("department", sa.String(length=128), nullable=True),
        sa.Column(
            "employment_status",
            sa.Enum("ACTIVE", "LEAVE", "TERMINATED", "SUSPENDED", name="employmentstatusenum"),
            nullable=False,
            server_default="ACTIVE",
            index=True,
        ),
        sa.Column("risk_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column(
            "risk_band",
            sa.Enum("CRITICAL", "HIGH", "MODERATE", "LOW", name="identityriskbandenum"),
            nullable=False,
            server_default="LOW",
            index=True,
        ),
        sa.Column("is_privileged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "cloud_asset_id",
            sa.Integer(),
            sa.ForeignKey("cloud_assets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "identity_code", name="uq_governed_identity_tenant_code"),
        sa.UniqueConstraint("organization_id", "email", name="uq_governed_identity_tenant_email"),
        sa.CheckConstraint("risk_score >= 0.00 AND risk_score <= 100.00", name="chk_governed_identity_risk_score"),
    )

    # ── 8. identity_entitlements ──────────────────────────────────────────────
    op.create_table(
        "identity_entitlements",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("entitlement_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "system_type",
            sa.Enum("ACTIVE_DIRECTORY", "OKTA", "AWS_IAM", "AZURE_RBAC", "DATABASE_ROLE", "SAAS_APPLICATION", name="systemtypeenum"),
            nullable=False,
            server_default="AWS_IAM",
            index=True,
        ),
        sa.Column("resource_name", sa.String(length=255), nullable=False),
        sa.Column("permission_scope", sa.String(length=128), nullable=False),
        sa.Column("is_privileged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_high_risk", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("risk_weight", sa.Numeric(precision=3, scale=2), nullable=False, server_default="1.00"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "entitlement_code", name="uq_identity_entitlement_tenant_code"),
        sa.CheckConstraint("risk_weight >= 1.00 AND risk_weight <= 5.00", name="chk_identity_entitlement_risk_weight"),
    )

    # ── 9. identity_entitlement_assignments ───────────────────────────────────
    op.create_table(
        "identity_entitlement_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "identity_id",
            sa.Integer(),
            sa.ForeignKey("governed_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entitlement_id",
            sa.Integer(),
            sa.ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "assignment_type",
            sa.Enum("DIRECT", "ROLE_INHERITED", "JIT_ELEVATION", name="assignmenttypeenum"),
            nullable=False,
            server_default="DIRECT",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("organization_id", "identity_id", "entitlement_id", name="uq_identity_entitlement_assignment"),
    )

    # ── 10. access_certification_campaigns ────────────────────────────────────
    op.create_table(
        "access_certification_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("campaign_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "campaign_type",
            sa.Enum("PERIODIC_USER_ACCESS_REVIEW", "PRIVILEGED_ACCESS_CERTIFICATION", "SOD_CONFLICT_REVIEW", "TERMINATION_AUDIT", name="campaigntypeenum"),
            nullable=False,
            server_default="PERIODIC_USER_ACCESS_REVIEW",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "IN_REVIEW", "FINALIZED", "CANCELLED", name="campaignstatusenum"),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column("total_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("certified_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "campaign_code", name="uq_access_campaign_tenant_code"),
    )

    # ── 11. access_certification_items ────────────────────────────────────────
    op.create_table(
        "access_certification_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("access_certification_campaigns.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "identity_id",
            sa.Integer(),
            sa.ForeignKey("governed_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entitlement_id",
            sa.Integer(),
            sa.ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "decision",
            sa.Enum("PENDING", "CERTIFIED", "REVOKED", "EXCEPTION_APPROVED", name="certificationdecisionenum"),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("decision_justification", sa.Text(), nullable=True),
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_sod_violation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.UniqueConstraint("organization_id", "campaign_id", "identity_id", "entitlement_id", name="uq_access_cert_item"),
    )

    # ── 12. jit_access_requests ───────────────────────────────────────────────
    op.create_table(
        "jit_access_requests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("request_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "identity_id",
            sa.Integer(),
            sa.ForeignKey("governed_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entitlement_id",
            sa.Integer(),
            sa.ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("requested_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("business_justification", sa.Text(), nullable=False),
        sa.Column(
            "approval_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "EXPIRED", "REVOKED", name="jitapprovalstatusenum"),
            nullable=False,
            server_default="PENDING",
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
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "request_code", name="uq_jit_request_tenant_code"),
        sa.CheckConstraint("requested_duration_minutes >= 15 AND requested_duration_minutes <= 480", name="chk_jit_duration_bounds"),
    )

    # ── 13. zero_trust_assessments ────────────────────────────────────────────
    op.create_table(
        "zero_trust_assessments",
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
            "identity_id",
            sa.Integer(),
            sa.ForeignKey("governed_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("device_health_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column("auth_strength_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column("context_risk_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("behavioral_anomaly_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("zero_trust_assurance_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column(
            "trust_level",
            sa.Enum("HIGH_TRUST", "CONDITIONAL_TRUST", "LOW_TRUST", "UNTRUSTED", name="trustlevelenum"),
            nullable=False,
            server_default="HIGH_TRUST",
            index=True,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "assessment_code", name="uq_zt_assessment_tenant_code"),
        sa.CheckConstraint("zero_trust_assurance_score >= 0.00 AND zero_trust_assurance_score <= 100.00", name="chk_zt_assurance_score"),
    )

    # ── 14. sod_conflict_policies ─────────────────────────────────────────────
    op.create_table(
        "sod_conflict_policies",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("policy_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "entitlement_a_id",
            sa.Integer(),
            sa.ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "entitlement_b_id",
            sa.Integer(),
            sa.ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", name="sodpolicyseverityenum"),
            nullable=False,
            server_default="HIGH",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "policy_code", name="uq_sod_policy_tenant_code"),
    )

    # ── 15. sod_conflict_violations ───────────────────────────────────────────
    op.create_table(
        "sod_conflict_violations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "identity_id",
            sa.Integer(),
            sa.ForeignKey("governed_identities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "policy_id",
            sa.Integer(),
            sa.ForeignKey("sod_conflict_policies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE_VIOLATION", "EXCEPTION_GRANTED", "REMEDIATED", name="sodviolationstatusenum"),
            nullable=False,
            server_default="ACTIVE_VIOLATION",
            index=True,
        ),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "identity_id", "policy_id", name="uq_sod_violation_instance"),
    )


def downgrade() -> None:
    op.drop_table("sod_conflict_violations")
    op.drop_table("sod_conflict_policies")
    op.drop_table("zero_trust_assessments")
    op.drop_table("jit_access_requests")
    op.drop_table("access_certification_items")
    op.drop_table("access_certification_campaigns")
    op.drop_table("identity_entitlement_assignments")
    op.drop_table("identity_entitlements")
    op.drop_table("governed_identities")
    op.drop_table("cloud_iam_blast_radii")
    op.drop_table("cloud_configuration_drifts")
    op.drop_table("cloud_security_findings")
    op.drop_table("cloud_benchmark_rules")
    op.drop_table("cloud_security_benchmarks")
    op.drop_table("cloud_assets")
