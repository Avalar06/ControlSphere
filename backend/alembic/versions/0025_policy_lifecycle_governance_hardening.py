"""0025_policy_lifecycle_governance_hardening - Batch 4 (POLICY-LIFECYCLE-GRC)

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── 1. Ensure approval metadata columns on policy_versions ──────────────
    pv_cols = {c["name"] for c in inspector.get_columns("policy_versions")}
    if "approved_by_id" not in pv_cols or "approved_at" not in pv_cols:
        with op.batch_alter_table("policy_versions") as batch_op:
            if "approved_by_id" not in pv_cols:
                batch_op.add_column(
                    sa.Column(
                        "approved_by_id",
                        sa.Integer(),
                        sa.ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True,
                    )
                )
            if "approved_at" not in pv_cols:
                batch_op.add_column(
                    sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
                )

    # ── 2. Extend user_attestation_records with exemption governance ─────────
    uar_cols = {c["name"] for c in inspector.get_columns("user_attestation_records")}
    uar_indexes = {i["name"] for i in inspector.get_indexes("user_attestation_records")}
    with op.batch_alter_table("user_attestation_records") as batch_op:
        if "exemption_exception_id" not in uar_cols:
            batch_op.add_column(
                sa.Column(
                    "exemption_exception_id",
                    sa.Integer(),
                    sa.ForeignKey(
                        "security_exceptions.id",
                        name="fk_user_att_exemption_exc_id",
                        ondelete="SET NULL",
                    ),
                    nullable=True,
                )
            )
        if "exemption_reason" not in uar_cols:
            batch_op.add_column(
                sa.Column("exemption_reason", sa.Text(), nullable=True)
            )
        if "exempted_by_id" not in uar_cols:
            batch_op.add_column(
                sa.Column(
                    "exempted_by_id",
                    sa.Integer(),
                    sa.ForeignKey(
                        "users.id",
                        name="fk_user_att_exempted_by_id",
                        ondelete="SET NULL",
                    ),
                    nullable=True,
                )
            )
        if "exempted_at" not in uar_cols:
            batch_op.add_column(
                sa.Column("exempted_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "ix_user_att_org_camp_status" not in uar_indexes:
            batch_op.create_index(
                "ix_user_att_org_camp_status",
                ["organization_id", "campaign_id", "status"],
            )

    # ── 3. Extend policy_attestation_campaigns with overdue & reminder state ─
    pac_cols = {c["name"] for c in inspector.get_columns("policy_attestation_campaigns")}
    pac_indexes = {i["name"] for i in inspector.get_indexes("policy_attestation_campaigns")}
    with op.batch_alter_table("policy_attestation_campaigns") as batch_op:
        if "overdue_count" not in pac_cols:
            batch_op.add_column(
                sa.Column(
                    "overdue_count",
                    sa.Integer(),
                    server_default="0",
                    nullable=False,
                )
            )
        if "reminder_sent_at" not in pac_cols:
            batch_op.add_column(
                sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "ix_pol_camp_org_pol_status" not in pac_indexes:
            batch_op.create_index(
                "ix_pol_camp_org_pol_status",
                ["organization_id", "policy_id", "status"],
            )

    # ── 4. Extend policy_review_workflows with updated_at & status index ─────
    prw_cols = {c["name"] for c in inspector.get_columns("policy_review_workflows")}
    prw_indexes = {i["name"] for i in inspector.get_indexes("policy_review_workflows")}
    with op.batch_alter_table("policy_review_workflows") as batch_op:
        if "updated_at" not in prw_cols:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=True,
                )
            )
        if "ix_pol_rev_wf_org_ver_status" not in prw_indexes:
            batch_op.create_index(
                "ix_pol_rev_wf_org_ver_status",
                ["organization_id", "version_id", "status"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    prw_cols = {c["name"] for c in inspector.get_columns("policy_review_workflows")}
    prw_indexes = {i["name"] for i in inspector.get_indexes("policy_review_workflows")}
    with op.batch_alter_table("policy_review_workflows") as batch_op:
        if "ix_pol_rev_wf_org_ver_status" in prw_indexes:
            batch_op.drop_index("ix_pol_rev_wf_org_ver_status")
        if "updated_at" in prw_cols:
            batch_op.drop_column("updated_at")

    pac_cols = {c["name"] for c in inspector.get_columns("policy_attestation_campaigns")}
    pac_indexes = {i["name"] for i in inspector.get_indexes("policy_attestation_campaigns")}
    with op.batch_alter_table("policy_attestation_campaigns") as batch_op:
        if "ix_pol_camp_org_pol_status" in pac_indexes:
            batch_op.drop_index("ix_pol_camp_org_pol_status")
        if "reminder_sent_at" in pac_cols:
            batch_op.drop_column("reminder_sent_at")
        if "overdue_count" in pac_cols:
            batch_op.drop_column("overdue_count")

    uar_cols = {c["name"] for c in inspector.get_columns("user_attestation_records")}
    uar_indexes = {i["name"] for i in inspector.get_indexes("user_attestation_records")}
    op.execute(
        "UPDATE user_attestation_records SET status = 'PENDING' WHERE status = 'EXEMPTED'"
    )
    with op.batch_alter_table("user_attestation_records") as batch_op:
        if "ix_user_att_org_camp_status" in uar_indexes:
            batch_op.drop_index("ix_user_att_org_camp_status")
        if "exempted_at" in uar_cols:
            batch_op.drop_column("exempted_at")
        if "exempted_by_id" in uar_cols:
            batch_op.drop_column("exempted_by_id")
        if "exemption_reason" in uar_cols:
            batch_op.drop_column("exemption_reason")
        if "exemption_exception_id" in uar_cols:
            batch_op.drop_column("exemption_exception_id")

