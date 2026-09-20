"""0021_policy_lifecycle_and_attestation - Phase 24 (POLICY-ATTESTATION-GRC)

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Enhance policy_versions table ────────────────────────────────────
    with op.batch_alter_table("policy_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("content_hash_sha256", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=50),
                server_default="DRAFT",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "approved_by_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("effective_date", sa.Date(), nullable=True)
        )
        batch_op.create_index("ix_policy_versions_org_id", ["organization_id"])
        batch_op.create_index("ix_policy_versions_content_hash", ["content_hash_sha256"])
        batch_op.create_index("ix_policy_versions_status", ["status"])

    # Backfill organization_id from policies for existing Phase 2 versions
    op.execute(
        "UPDATE policy_versions SET organization_id = ("
        "    SELECT organization_id FROM policies WHERE policies.id = policy_versions.policy_id"
        ") WHERE organization_id IS NULL"
    )

    # Enforce NOT NULL on organization_id
    with op.batch_alter_table("policy_versions") as batch_op:
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # ── 2. Create policy_review_workflows table ─────────────────────────────
    op.create_table(
        "policy_review_workflows",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_id",
            sa.Integer(),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("policy_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workflow_code", sa.String(length=64), nullable=False),
        sa.Column("review_stage", sa.String(length=50), server_default="LEGAL_REVIEW", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="PENDING", nullable=False),
        sa.Column(
            "assigned_reviewer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "workflow_code", name="uq_pol_rev_wf_code"),
    )
    op.create_index("ix_policy_review_workflows_id", "policy_review_workflows", ["id"])
    op.create_index("ix_policy_review_workflows_org_id", "policy_review_workflows", ["organization_id"])
    op.create_index("ix_policy_review_workflows_policy_id", "policy_review_workflows", ["policy_id"])
    op.create_index("ix_policy_review_workflows_version_id", "policy_review_workflows", ["version_id"])
    op.create_index("ix_policy_review_workflows_status", "policy_review_workflows", ["status"])

    # ── 3. Create policy_attestation_campaigns table ─────────────────────────
    op.create_table(
        "policy_attestation_campaigns",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campaign_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "policy_id",
            sa.Integer(),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("policy_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("policy_version_hash", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=50), server_default="ALL_USERS", nullable=False),
        sa.Column("target_role", sa.String(length=50), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grace_period_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            sa.ForeignKey("assessments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("total_targeted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "campaign_code", name="uq_pol_att_camp_code"),
    )
    op.create_index("ix_policy_attestation_campaigns_id", "policy_attestation_campaigns", ["id"])
    op.create_index("ix_policy_attestation_campaigns_org_id", "policy_attestation_campaigns", ["organization_id"])
    op.create_index("ix_policy_attestation_campaigns_policy_id", "policy_attestation_campaigns", ["policy_id"])
    op.create_index("ix_policy_attestation_campaigns_version_id", "policy_attestation_campaigns", ["version_id"])
    op.create_index("ix_policy_attestation_campaigns_status", "policy_attestation_campaigns", ["status"])

    # ── 4. Create user_attestation_records table ─────────────────────────────
    op.create_table(
        "user_attestation_records",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("policy_attestation_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_id",
            sa.Integer(),
            sa.ForeignKey("policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("policy_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), server_default="PENDING", nullable=False),
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("acknowledgement_text", sa.Text(), nullable=True),
        sa.Column("comprehension_passed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("attestation_receipt_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "evidence_item_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "campaign_id", "user_id", name="uq_camp_user_attestation"),
    )
    op.create_index("ix_user_attestation_records_id", "user_attestation_records", ["id"])
    op.create_index("ix_user_attestation_records_org_id", "user_attestation_records", ["organization_id"])
    op.create_index("ix_user_attestation_records_campaign_id", "user_attestation_records", ["campaign_id"])
    op.create_index("ix_user_attestation_records_user_id", "user_attestation_records", ["user_id"])
    op.create_index("ix_user_attestation_records_status", "user_attestation_records", ["status"])


def downgrade() -> None:
    op.drop_table("user_attestation_records")
    op.drop_table("policy_attestation_campaigns")
    op.drop_table("policy_review_workflows")
    with op.batch_alter_table("policy_versions") as batch_op:
        batch_op.drop_index("ix_policy_versions_status")
        batch_op.drop_index("ix_policy_versions_content_hash")
        batch_op.drop_index("ix_policy_versions_org_id")
        batch_op.drop_column("effective_date")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approved_by_id")
        batch_op.drop_column("status")
        batch_op.drop_column("content_hash_sha256")
        batch_op.drop_column("organization_id")
