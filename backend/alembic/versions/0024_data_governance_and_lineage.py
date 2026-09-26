"""0024_data_governance_and_lineage - Batch 3 (DATA-GOVERNANCE-GRC)

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create data_classification_schemes ──────────────────────────────────
    op.create_table(
        "data_classification_schemes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("scheme_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False, index=True),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_by_id",
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "scheme_code", "version", name="uq_class_scheme_org_code_ver"),
        sa.CheckConstraint("version >= 1", name="ck_class_scheme_version_pos"),
        sa.CheckConstraint(
            "approved_by_id IS NULL OR created_by_id != approved_by_id",
            name="ck_class_scheme_sod",
        ),
    )

    # ── 2. Create data_classification_levels ───────────────────────────────────
    op.create_table(
        "data_classification_levels",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("data_classification_schemes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("level_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ordinal_rank", sa.Integer(), nullable=False),
        sa.Column(
            "mapped_sensitivity_level",
            sa.Enum(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "RESTRICTED_PII",
                "SPECIAL_CATEGORY_SENSITIVE_PHI",
                name="datasensitivitylevel",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("requires_encryption_at_rest", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("requires_encryption_in_transit", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("requires_four_eyes_approval", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("default_retention_months", sa.Integer(), nullable=True),
        sa.Column("required_disposal_method", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scheme_id", "level_code", name="uq_class_level_scheme_code"),
        sa.UniqueConstraint("scheme_id", "ordinal_rank", name="uq_class_level_scheme_rank"),
        sa.CheckConstraint("ordinal_rank >= 1 AND ordinal_rank <= 10", name="ck_class_level_rank_bounds"),
    )

    # ── 3. Extend existing data_assets table in-place ──────────────────────────
    with op.batch_alter_table("data_assets") as batch_op:
        batch_op.add_column(sa.Column("asset_type", sa.String(length=64), server_default="DATABASE_TABLE", nullable=False))
        batch_op.add_column(sa.Column("lifecycle_state", sa.String(length=32), server_default="ACTIVE", nullable=False))
        batch_op.add_column(sa.Column("steward_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cloud_asset_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("classification_scheme_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("classification_level_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("classification_status", sa.String(length=32), server_default="APPROVED", nullable=False))
        batch_op.add_column(sa.Column("classified_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("classification_approved_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("classification_approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("owner_transfer_status", sa.String(length=32), server_default="NONE", nullable=False))
        batch_op.add_column(sa.Column("pending_owner_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("owner_transfer_requested_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("owner_transfer_justification", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("deprecation_notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("disposal_method", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("retirement_requested_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("retired_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("retirement_notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("retirement_evidence_id", sa.Integer(), nullable=True))

        batch_op.create_index("ix_data_assets_asset_type", ["asset_type"])
        batch_op.create_index("ix_data_assets_lifecycle_state", ["lifecycle_state"])
        batch_op.create_index("ix_data_assets_steward_id", ["steward_id"])
        batch_op.create_index("ix_data_assets_cloud_asset_id", ["cloud_asset_id"])
        batch_op.create_index("ix_data_assets_classification_scheme_id", ["classification_scheme_id"])
        batch_op.create_index("ix_data_assets_classification_level_id", ["classification_level_id"])
        batch_op.create_index("ix_data_assets_classification_status", ["classification_status"])
        batch_op.create_index("ix_data_assets_retirement_evidence_id", ["retirement_evidence_id"])

        batch_op.create_foreign_key("fk_data_assets_steward_id", "users", ["steward_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_cloud_asset_id", "cloud_assets", ["cloud_asset_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(
            "fk_data_assets_class_scheme_id",
            "data_classification_schemes",
            ["classification_scheme_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_data_assets_class_level_id",
            "data_classification_levels",
            ["classification_level_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key("fk_data_assets_classified_by_id", "users", ["classified_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_class_approved_by_id", "users", ["classification_approved_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_pending_owner_id", "users", ["pending_owner_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_owner_req_by_id", "users", ["owner_transfer_requested_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_retire_req_by_id", "users", ["retirement_requested_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_retired_by_id", "users", ["retired_by_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_data_assets_retire_ev_id", "evidence_items", ["retirement_evidence_id"], ["id"], ondelete="SET NULL")

    # ── 4. Create data_classification_records ──────────────────────────────────
    op.create_table(
        "data_classification_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "scheme_id",
            sa.Integer(),
            sa.ForeignKey("data_classification_schemes.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "level_id",
            sa.Integer(),
            sa.ForeignKey("data_classification_levels.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "previous_level_id",
            sa.Integer(),
            sa.ForeignKey("data_classification_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "previous_sensitivity_level",
            sa.Enum(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "RESTRICTED_PII",
                "SPECIAL_CATEGORY_SENSITIVE_PHI",
                name="datasensitivitylevel",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "new_sensitivity_level",
            sa.Enum(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "RESTRICTED_PII",
                "SPECIAL_CATEGORY_SENSITIVE_PHI",
                name="datasensitivitylevel",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("change_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("justification", sa.Text(), nullable=False),
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
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("data_asset_id", "version", name="uq_class_record_asset_version"),
        sa.CheckConstraint("version >= 1", name="ck_class_record_version_pos"),
    )

    # ── 5. Create data_lineage_edges ───────────────────────────────────────────
    op.create_table(
        "data_lineage_edges",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("edge_code", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "source_data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("relationship_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("transformation_summary", sa.Text(), nullable=True),
        sa.Column("field_mapping_manifest", sa.JSON(), nullable=True),
        sa.Column("is_encrypted_in_transit", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_masked_or_anonymized", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "processing_activity_id",
            sa.Integer(),
            sa.ForeignKey("processing_activities.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "cloud_asset_id",
            sa.Integer(),
            sa.ForeignKey("cloud_assets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "created_by_id",
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
        sa.Column(
            "revoked_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "edge_code", "version", name="uq_lineage_edge_org_code_ver"),
        sa.CheckConstraint("source_data_asset_id != target_data_asset_id", name="ck_lineage_no_self_loop"),
        sa.CheckConstraint("version >= 1", name="ck_lineage_version_pos"),
    )

    # ── 6. Create data_asset_cloud_links ───────────────────────────────────────
    op.create_table(
        "data_asset_cloud_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "cloud_asset_id",
            sa.Integer(),
            sa.ForeignKey("cloud_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("hosting_role", sa.String(length=32), server_default="PRIMARY_STORE", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "linked_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "data_asset_id", "cloud_asset_id", name="uq_data_asset_cloud_link"),
    )

    # ── 7. Create data_asset_processing_links ──────────────────────────────────
    op.create_table(
        "data_asset_processing_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "processing_activity_id",
            sa.Integer(),
            sa.ForeignKey("processing_activities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("usage_role", sa.String(length=32), server_default="PRIMARY_SOURCE", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "linked_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "data_asset_id", "processing_activity_id", name="uq_data_asset_processing_link"),
    )

    # ── 8. Create data_asset_control_links ─────────────────────────────────────
    op.create_table(
        "data_asset_control_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="CASCADE"),
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
        sa.Column("control_objective", sa.String(length=32), server_default="ENCRYPTION_AT_REST", nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("coverage_notes", sa.Text(), nullable=True),
        sa.Column(
            "linked_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "data_asset_id", "organization_control_id", name="uq_data_asset_control_link"),
    )

    # ── 9. Create data_asset_evidence_links ────────────────────────────────────
    op.create_table(
        "data_asset_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_asset_id",
            sa.Integer(),
            sa.ForeignKey("data_assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evidence_item_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("evidence_purpose", sa.String(length=64), server_default="CLASSIFICATION_JUSTIFICATION", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "linked_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "data_asset_id",
            "evidence_item_id",
            "evidence_purpose",
            name="uq_data_asset_evidence_link",
        ),
    )


def downgrade() -> None:
    op.drop_table("data_asset_evidence_links")
    op.drop_table("data_asset_control_links")
    op.drop_table("data_asset_processing_links")
    op.drop_table("data_asset_cloud_links")
    op.drop_table("data_lineage_edges")
    op.drop_table("data_classification_records")

    with op.batch_alter_table("data_assets") as batch_op:
        batch_op.drop_constraint("fk_data_assets_retire_ev_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_retired_by_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_retire_req_by_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_owner_req_by_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_pending_owner_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_class_approved_by_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_classified_by_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_class_level_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_class_scheme_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_cloud_asset_id", type_="foreignkey")
        batch_op.drop_constraint("fk_data_assets_steward_id", type_="foreignkey")

        batch_op.drop_index("ix_data_assets_retirement_evidence_id")
        batch_op.drop_index("ix_data_assets_classification_status")
        batch_op.drop_index("ix_data_assets_classification_level_id")
        batch_op.drop_index("ix_data_assets_classification_scheme_id")
        batch_op.drop_index("ix_data_assets_cloud_asset_id")
        batch_op.drop_index("ix_data_assets_steward_id")
        batch_op.drop_index("ix_data_assets_lifecycle_state")
        batch_op.drop_index("ix_data_assets_asset_type")

        batch_op.drop_column("retirement_evidence_id")
        batch_op.drop_column("retirement_notes")
        batch_op.drop_column("retired_at")
        batch_op.drop_column("retired_by_id")
        batch_op.drop_column("retirement_requested_by_id")
        batch_op.drop_column("disposal_method")
        batch_op.drop_column("deprecation_notes")
        batch_op.drop_column("owner_transfer_justification")
        batch_op.drop_column("owner_transfer_requested_by_id")
        batch_op.drop_column("pending_owner_id")
        batch_op.drop_column("owner_transfer_status")
        batch_op.drop_column("last_reviewed_at")
        batch_op.drop_column("classification_approved_at")
        batch_op.drop_column("classification_approved_by_id")
        batch_op.drop_column("classified_by_id")
        batch_op.drop_column("classification_status")
        batch_op.drop_column("classification_level_id")
        batch_op.drop_column("classification_scheme_id")
        batch_op.drop_column("cloud_asset_id")
        batch_op.drop_column("steward_id")
        batch_op.drop_column("lifecycle_state")
        batch_op.drop_column("asset_type")

    op.drop_table("data_classification_levels")
    op.drop_table("data_classification_schemes")
