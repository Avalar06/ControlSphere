"""0022_audit_fieldwork_and_sampling - Batch 1 (AUDIT-FIELDWORK-GRC)

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create audit_pbc_requests ──────────────────────────────────────────
    op.create_table(
        "audit_pbc_requests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "procedure_id",
            sa.Integer(),
            sa.ForeignKey("audit_procedures.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "organization_control_id",
            sa.Integer(),
            sa.ForeignKey("organization_controls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("request_identifier", sa.String(length=50), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="REQUESTED", nullable=False, index=True),
        sa.Column("priority", sa.String(length=50), server_default="MEDIUM", nullable=False),
        sa.Column(
            "assigned_to_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=False, index=True),
        sa.Column(
            "fulfilled_evidence_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("submission_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "request_identifier", name="uq_pbc_org_identifier"),
    )

    # ── 2. Create audit_sample_populations ────────────────────────────────────
    op.create_table(
        "audit_sample_populations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "procedure_id",
            sa.Integer(),
            sa.ForeignKey("audit_procedures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("population_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("population_source", sa.String(length=255), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_frozen", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "frozen_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("population_digest_sha256", sa.String(length=64), nullable=True),
        sa.Column("population_data_json", sa.Text(), nullable=True),
        sa.Column("sampling_method", sa.String(length=50), server_default="RANDOM", nullable=False),
        sa.Column("sampling_seed", sa.String(length=64), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("sample_parameters_json", sa.Text(), nullable=True),
        sa.Column("samples_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("procedure_id", "version_number", name="uq_population_proc_version"),
    )

    # ── 3. Create audit_sample_items ──────────────────────────────────────────
    op.create_table(
        "audit_sample_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "population_id",
            sa.Integer(),
            sa.ForeignKey("audit_sample_populations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("item_attributes_json", sa.Text(), nullable=False),
        sa.Column("test_result", sa.String(length=50), server_default="PENDING", nullable=False, index=True),
        sa.Column("testing_notes", sa.Text(), nullable=True),
        sa.Column(
            "tested_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "evidence_item_id",
            sa.Integer(),
            sa.ForeignKey("evidence_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "deficiency_finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("population_id", "item_index", name="uq_sample_pop_item"),
    )

    # ── 4. Create audit_workpaper_reviews ──────────────────────────────────────
    op.create_table(
        "audit_workpaper_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audits.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "procedure_id",
            sa.Integer(),
            sa.ForeignKey("audit_procedures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False, index=True),
        sa.Column("testing_summary", sa.Text(), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=False),
        sa.Column(
            "prepared_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reviewed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("workpaper_hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("procedure_id", "version_number", name="uq_workpaper_proc_version"),
    )

    # ── 5. Alter audit_procedures ─────────────────────────────────────────────
    with op.batch_alter_table("audit_procedures") as batch_op:
        batch_op.add_column(
            sa.Column("has_sampling", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )
        batch_op.add_column(
            sa.Column("workpaper_status", sa.String(length=50), server_default="DRAFT", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_procedures") as batch_op:
        batch_op.drop_column("workpaper_status")
        batch_op.drop_column("has_sampling")

    op.drop_table("audit_workpaper_reviews")
    op.drop_table("audit_sample_items")
    op.drop_table("audit_sample_populations")
    op.drop_table("audit_pbc_requests")
