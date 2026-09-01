"""0017_supply_chain_governance - Phase 17 Supply Chain Risk & SBOM Governance (SUPPLYCHAIN-GRC)
Revision ID: 0017
Revises: 0016
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. software_products ──────────────────────────────────────────────────
    op.create_table(
        "software_products",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("product_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "product_type",
            sa.Enum(
                "INTERNAL_APPLICATION",
                "MICROSERVICE",
                "COMMERCIAL_COTS",
                "FIRMWARE_IOT",
                "AI_MODEL_PIPELINE",
                "OPEN_SOURCE_LIBRARY",
                name="softwareproducttypeenum",
            ),
            nullable=False,
            server_default="INTERNAL_APPLICATION",
        ),
        sa.Column(
            "criticality_tier",
            sa.Enum(
                "TIER_1_CRITICAL",
                "TIER_2_MAJOR",
                "TIER_3_MODERATE",
                "TIER_4_LOW",
                name="productcriticalitytierenum",
            ),
            nullable=False,
            server_default="TIER_3_MODERATE",
        ),
        sa.Column(
            "lifecycle_state",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "DEPRECATED",
                "RETIRED",
                name="productlifecyclestateenum",
            ),
            nullable=False,
            server_default="DRAFT",
            index=True,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        # Cross-Module Lineage
        sa.Column(
            "business_process_id",
            sa.Integer(),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "ai_system_id",
            sa.Integer(),
            sa.ForeignKey("ai_systems.id", ondelete="SET NULL"),
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
        # Metrics
        sa.Column("supply_chain_exposure_index", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("total_components_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vulnerable_components_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("policy_violations_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "product_code", name="uq_software_product_code_per_org"),
        sa.CheckConstraint("supply_chain_exposure_index >= 0.0 AND supply_chain_exposure_index <= 100.0", name="chk_product_scei_range"),
    )

    # ── 2. sbom_documents ─────────────────────────────────────────────────────
    op.create_table(
        "sbom_documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "software_product_id",
            sa.Integer(),
            sa.ForeignKey("software_products.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sbom_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column(
            "format_standard",
            sa.Enum(
                "CYCLONEDX_JSON",
                "CYCLONEDX_XML",
                "SPDX_JSON",
                "SPDX_TAG_VALUE",
                "CUSTOM_JSON",
                name="sbomformatstandardenum",
            ),
            nullable=False,
            server_default="CYCLONEDX_JSON",
        ),
        sa.Column("spec_version", sa.String(length=16), nullable=False, server_default="1.5"),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("tool_name", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "SUPERSEDED",
                "ARCHIVED",
                name="sbomstatusenum",
            ),
            nullable=False,
            server_default="ACTIVE",
            index=True,
        ),
        sa.Column("component_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "sbom_code", name="uq_sbom_code_per_org"),
    )

    # ── 3. software_components ────────────────────────────────────────────────
    op.create_table(
        "software_components",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "sbom_document_id",
            sa.Integer(),
            sa.ForeignKey("sbom_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("component_name", sa.String(length=255), nullable=False, index=True),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("purl", sa.String(length=512), nullable=False, index=True),
        sa.Column(
            "ecosystem",
            sa.Enum(
                "NPM",
                "PYPI",
                "MAVEN",
                "GO",
                "CARGO",
                "NUGET",
                "DOCKER",
                "COMPOSER",
                "GENERIC",
                name="componentecosystemenum",
            ),
            nullable=False,
            server_default="GENERIC",
        ),
        sa.Column("dependency_depth", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("declared_license", sa.String(length=128), nullable=False, server_default="UNKNOWN"),
        sa.Column(
            "license_category",
            sa.Enum(
                "PERMISSIVE",
                "WEAK_COPYLEFT",
                "STRONG_COPYLEFT",
                "PROHIBITED",
                "UNCLASSIFIED",
                name="licensecategoryenum",
            ),
            nullable=False,
            server_default="UNCLASSIFIED",
        ),
        sa.Column("is_license_prohibited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("component_risk_index", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("max_vulnerability_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("vulnerabilities_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_exempted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("dependency_depth >= 1", name="chk_component_depth_positive"),
        sa.CheckConstraint("component_risk_index >= 0.0 AND component_risk_index <= 100.0", name="chk_component_cri_range"),
    )

    # ── 4. component_vulnerability_links ──────────────────────────────────────
    op.create_table(
        "component_vulnerability_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "component_id",
            sa.Integer(),
            sa.ForeignKey("software_components.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "vulnerability_id",
            sa.Integer(),
            sa.ForeignKey("vulnerability_exposures.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("cve_identifier", sa.String(length=64), nullable=False, index=True),
        sa.Column("severity_score", sa.Numeric(precision=4, scale=2), nullable=False, server_default="0.00"),
        sa.Column("is_exploitable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_reachable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fix_version", sa.String(length=64), nullable=True),
        sa.Column(
            "remediation_plan_id",
            sa.Integer(),
            sa.ForeignKey("remediation_plans.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity_score >= 0.0 AND severity_score <= 10.0", name="chk_vuln_link_cvss_range"),
    )

    # ── 5. license_compliance_policies ────────────────────────────────────────
    op.create_table(
        "license_compliance_policies",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("license_identifier", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "PERMISSIVE",
                "WEAK_COPYLEFT",
                "STRONG_COPYLEFT",
                "PROHIBITED",
                "UNCLASSIFIED",
                name="licensecategoryenum_policy",
            ),
            nullable=False,
            server_default="PERMISSIVE",
        ),
        sa.Column("is_prohibited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("risk_penalty_points", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "license_identifier", name="uq_license_policy_per_org"),
        sa.CheckConstraint("risk_penalty_points >= 0.0 AND risk_penalty_points <= 30.0", name="chk_license_risk_penalty_range"),
    )

    # ── 6. supply_chain_exemptions ────────────────────────────────────────────
    op.create_table(
        "supply_chain_exemptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("exemption_code", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "software_product_id",
            sa.Integer(),
            sa.ForeignKey("software_products.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "component_id",
            sa.Integer(),
            sa.ForeignKey("software_components.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("compensating_controls", sa.Text(), nullable=False),
        sa.Column(
            "requested_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "reviewed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "approval_status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "REVOKED",
                "EXPIRED",
                name="exemptionapprovalstatusenum",
            ),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "exemption_code", name="uq_sc_exemption_code_per_org"),
    )


def downgrade() -> None:
    op.drop_table("supply_chain_exemptions")
    op.drop_table("license_compliance_policies")
    op.drop_table("component_vulnerability_links")
    op.drop_table("software_components")
    op.drop_table("sbom_documents")
    op.drop_table("software_products")
