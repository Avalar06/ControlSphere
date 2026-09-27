"""0026_operational_resilience_continuity_and_testing - Batch 5 (RESILIENCE-CONTINUITY-GRC)

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── 1. Extend dependencytypeenum on PostgreSQL ──────────────────────────
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE dependencytypeenum ADD VALUE IF NOT EXISTS 'CLOUD_ASSET'")
        op.execute("ALTER TYPE dependencytypeenum ADD VALUE IF NOT EXISTS 'DATA_ASSET'")
        op.execute("ALTER TYPE dependencytypeenum ADD VALUE IF NOT EXISTS 'PROCESS'")

    # ── 2. Extend process_dependencies with typed target FKs & SPOF fields ──
    pd_cols = {c["name"] for c in inspector.get_columns("process_dependencies")}
    pd_indexes = {i["name"] for i in inspector.get_indexes("process_dependencies")}

    with op.batch_alter_table("process_dependencies") as batch_op:
        if "vendor_id" not in pd_cols:
            batch_op.add_column(sa.Column("vendor_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_proc_dep_vendor_id",
                "vendors",
                ["vendor_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if "organization_control_id" not in pd_cols:
            batch_op.add_column(sa.Column("organization_control_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_proc_dep_org_ctrl_id",
                "organization_controls",
                ["organization_control_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if "cloud_asset_id" not in pd_cols:
            batch_op.add_column(sa.Column("cloud_asset_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_proc_dep_cloud_asset_id",
                "cloud_assets",
                ["cloud_asset_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if "data_asset_id" not in pd_cols:
            batch_op.add_column(sa.Column("data_asset_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_proc_dep_data_asset_id",
                "data_assets",
                ["data_asset_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if "depends_on_process_id" not in pd_cols:
            batch_op.add_column(sa.Column("depends_on_process_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_proc_dep_depends_on_proc_id",
                "business_processes",
                ["depends_on_process_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if "is_single_point_of_failure" not in pd_cols:
            batch_op.add_column(
                sa.Column(
                    "is_single_point_of_failure",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "failure_propagation_weight" not in pd_cols:
            batch_op.add_column(
                sa.Column(
                    "failure_propagation_weight",
                    sa.Float(),
                    nullable=False,
                    server_default="1.0",
                )
            )
        if "recovery_priority_order" not in pd_cols:
            batch_op.add_column(
                sa.Column(
                    "recovery_priority_order",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )
        if "criticality_notes" not in pd_cols:
            batch_op.add_column(sa.Column("criticality_notes", sa.Text(), nullable=True))

        if "ix_process_dependencies_vendor_id" not in pd_indexes:
            batch_op.create_index("ix_process_dependencies_vendor_id", ["vendor_id"])
        if "ix_process_dependencies_organization_control_id" not in pd_indexes:
            batch_op.create_index(
                "ix_process_dependencies_organization_control_id",
                ["organization_control_id"],
            )
        if "ix_process_dependencies_cloud_asset_id" not in pd_indexes:
            batch_op.create_index("ix_process_dependencies_cloud_asset_id", ["cloud_asset_id"])
        if "ix_process_dependencies_data_asset_id" not in pd_indexes:
            batch_op.create_index("ix_process_dependencies_data_asset_id", ["data_asset_id"])
        if "ix_process_dependencies_depends_on_process_id" not in pd_indexes:
            batch_op.create_index(
                "ix_process_dependencies_depends_on_process_id",
                ["depends_on_process_id"],
            )

    # Backfill typed FK columns on any pre-existing rows before adding check constraints
    op.execute(
        "UPDATE process_dependencies SET vendor_id = dependency_id "
        "WHERE dependency_type = 'VENDOR' AND vendor_id IS NULL"
    )
    op.execute(
        "UPDATE process_dependencies SET organization_control_id = dependency_id "
        "WHERE dependency_type = 'CONTROL' AND organization_control_id IS NULL"
    )

    with op.batch_alter_table("process_dependencies") as batch_op:
        batch_op.create_check_constraint(
            "chk_process_dependency_no_self_ref",
            "depends_on_process_id IS NULL OR depends_on_process_id != process_id",
        )
        batch_op.create_check_constraint(
            "chk_dependency_single_target",
            """(
                (CASE WHEN vendor_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN organization_control_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN cloud_asset_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN data_asset_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN depends_on_process_id IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1""",
        )
        batch_op.create_check_constraint(
            "chk_dep_propagation_weight",
            "failure_propagation_weight > 0.0 AND failure_propagation_weight <= 1.0",
        )
        batch_op.create_check_constraint(
            "chk_dep_recovery_priority",
            "recovery_priority_order >= 1",
        )

    # ── 3. Create continuity_plans ──────────────────────────────────────────
    existing_tables = set(inspector.get_table_names())
    if "continuity_plans" not in existing_tables:
        op.create_table(
            "continuity_plans",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "process_id",
                sa.Integer(),
                sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "bia_id",
                sa.Integer(),
                sa.ForeignKey("business_impact_analyses.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("plan_code", sa.String(length=64), nullable=False, index=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("version_major", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("version_minor", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("version_label", sa.String(length=32), nullable=False, server_default="1.0"),
            sa.Column(
                "status",
                sa.Enum(
                    "DRAFT",
                    "PENDING_APPROVAL",
                    "APPROVED",
                    "SUPERSEDED",
                    "ARCHIVED",
                    name="continuityplanstatusenum",
                ),
                nullable=False,
                server_default="DRAFT",
                index=True,
            ),
            sa.Column(
                "strategy_type",
                sa.Enum(
                    "ACTIVE_ACTIVE",
                    "ACTIVE_ACTIVE_FAILOVER",
                    "ACTIVE_PASSIVE_FAILOVER",
                    "HOT_STANDBY",
                    "WARM_STANDBY",
                    "COLD_SITE",
                    "COLD_RESTORE_BACKUP",
                    "MANUAL_WORKAROUND",
                    "SUPPLIER_SUBSTITUTION",
                    "ALTERNATE_VENDOR_SWITCH",
                    name="continuitystrategytypeenum",
                ),
                nullable=False,
                index=True,
            ),
            sa.Column("activation_triggers", sa.Text(), nullable=False),
            sa.Column("communication_plan", sa.Text(), nullable=True),
            sa.Column("fallback_location_or_region", sa.String(length=255), nullable=True),
            sa.Column("estimated_recovery_hours", sa.Float(), nullable=False),
            sa.Column("estimated_rpo_hours", sa.Float(), nullable=False),
            sa.Column("review_frequency_days", sa.Integer(), nullable=False, server_default="365"),
            sa.Column("next_review_due_at", sa.DateTime(timezone=True), nullable=True, index=True),
            sa.Column("plan_hash_sha256", sa.String(length=64), nullable=True, index=True),
            sa.Column(
                "created_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "submitted_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "approved_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "superseded_by_plan_id",
                sa.Integer(),
                sa.ForeignKey("continuity_plans.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.UniqueConstraint(
                "organization_id",
                "process_id",
                "plan_code",
                "version_label",
                name="uq_cp_org_proc_code_ver",
            ),
            sa.CheckConstraint("version_major >= 1", name="chk_cp_version_major_pos"),
            sa.CheckConstraint("version_minor >= 0", name="chk_cp_version_minor_nonneg"),
            sa.CheckConstraint(
                "estimated_recovery_hours >= 0", name="chk_cp_est_recovery_nonneg"
            ),
            sa.CheckConstraint("estimated_rpo_hours >= 0", name="chk_cp_est_rpo_nonneg"),
            sa.CheckConstraint(
                "review_frequency_days >= 1 AND review_frequency_days <= 1825",
                name="chk_cp_review_freq_range",
            ),
        )
        op.create_index(
            "ix_cp_org_process_status",
            "continuity_plans",
            ["organization_id", "process_id", "status"],
        )

    # ── 4. Create continuity_recovery_steps ─────────────────────────────────
    if "continuity_recovery_steps" not in existing_tables:
        op.create_table(
            "continuity_recovery_steps",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "continuity_plan_id",
                sa.Integer(),
                sa.ForeignKey("continuity_plans.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("step_order", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("responsible_role_or_team", sa.String(length=128), nullable=True),
            sa.Column(
                "responsible_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "estimated_duration_minutes",
                sa.Integer(),
                nullable=False,
                server_default="15",
            ),
            sa.Column(
                "cloud_asset_id",
                sa.Integer(),
                sa.ForeignKey("cloud_assets.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "data_asset_id",
                sa.Integer(),
                sa.ForeignKey("data_assets.id", ondelete="SET NULL"),
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
            sa.Column(
                "organization_control_id",
                sa.Integer(),
                sa.ForeignKey("organization_controls.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("verification_criteria", sa.Text(), nullable=True),
            sa.Column(
                "is_automated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.UniqueConstraint(
                "continuity_plan_id",
                "step_order",
                name="uq_crs_plan_step_order",
            ),
            sa.CheckConstraint("step_order >= 1", name="chk_crs_step_order_pos"),
            sa.CheckConstraint(
                "estimated_duration_minutes >= 0", name="chk_crs_duration_nonneg"
            ),
        )
        op.create_index(
            "ix_crs_org_plan",
            "continuity_recovery_steps",
            ["organization_id", "continuity_plan_id"],
        )

    # ── 5. Create resilience_exercises ──────────────────────────────────────
    if "resilience_exercises" not in existing_tables:
        op.create_table(
            "resilience_exercises",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "process_id",
                sa.Integer(),
                sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "continuity_plan_id",
                sa.Integer(),
                sa.ForeignKey("continuity_plans.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "bia_id",
                sa.Integer(),
                sa.ForeignKey("business_impact_analyses.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("exercise_code", sa.String(length=64), nullable=False, index=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column(
                "exercise_type",
                sa.Enum(
                    "TABLETOP",
                    "FUNCTIONAL_FAILOVER",
                    "FULL_INTERRUPTION",
                    "BACKUP_RESTORATION",
                    "THIRD_PARTY_RESILIENCE",
                    name="exercisetypeenum",
                ),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "status",
                sa.Enum(
                    "PLANNED",
                    "IN_PROGRESS",
                    "COMPLETED",
                    "REVIEWED",
                    "CANCELLED",
                    name="exercisestatusenum",
                ),
                nullable=False,
                server_default="PLANNED",
                index=True,
            ),
            sa.Column("scenario_description", sa.Text(), nullable=False),
            sa.Column("scope_notes", sa.Text(), nullable=True),
            sa.Column(
                "scheduled_start_at",
                sa.DateTime(timezone=True),
                nullable=False,
                index=True,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("target_rto_hours_snapshot", sa.Float(), nullable=False),
            sa.Column("target_rpo_hours_snapshot", sa.Float(), nullable=False),
            sa.Column("target_mtd_hours_snapshot", sa.Float(), nullable=False),
            sa.Column("actual_rto_hours", sa.Float(), nullable=True),
            sa.Column("actual_rpo_hours", sa.Float(), nullable=True),
            sa.Column("rto_variance_hours", sa.Float(), nullable=True),
            sa.Column("rpo_variance_hours", sa.Float(), nullable=True),
            sa.Column(
                "rto_breached",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "rpo_breached",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "mtd_breached",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "control_deficiency_observed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "outcome",
                sa.Enum(
                    "PASS",
                    "PASS_WITH_MINOR_EXCEPTIONS",
                    "FAIL_RTO_BREACH",
                    "FAIL_RPO_BREACH",
                    "FAIL_MTD_BREACH",
                    "FAIL_CONTROL_DEFICIENCY",
                    name="exerciseoutcomeenum",
                ),
                nullable=True,
                index=True,
            ),
            sa.Column("lessons_learned", sa.Text(), nullable=True),
            sa.Column("executive_summary", sa.Text(), nullable=True),
            sa.Column("review_notes", sa.Text(), nullable=True),
            sa.Column("result_hash_sha256", sa.String(length=64), nullable=True, index=True),
            sa.Column(
                "planned_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "executed_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "reviewed_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "finding_id",
                sa.Integer(),
                sa.ForeignKey("findings.id", ondelete="SET NULL"),
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
            sa.Column(
                "risk_id",
                sa.Integer(),
                sa.ForeignKey("risks.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "triggered_by_incident_id",
                sa.Integer(),
                sa.ForeignKey("security_incidents.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.UniqueConstraint(
                "organization_id",
                "exercise_code",
                name="uq_re_org_exercise_code",
            ),
            sa.CheckConstraint(
                "target_rto_hours_snapshot >= 0", name="chk_re_target_rto_nonneg"
            ),
            sa.CheckConstraint(
                "target_rpo_hours_snapshot >= 0", name="chk_re_target_rpo_nonneg"
            ),
            sa.CheckConstraint(
                "target_mtd_hours_snapshot >= target_rto_hours_snapshot",
                name="chk_re_target_mtd_ge_rto",
            ),
            sa.CheckConstraint(
                "actual_rto_hours IS NULL OR actual_rto_hours >= 0",
                name="chk_re_actual_rto_nonneg",
            ),
            sa.CheckConstraint(
                "actual_rpo_hours IS NULL OR actual_rpo_hours >= 0",
                name="chk_re_actual_rpo_nonneg",
            ),
        )
        op.create_index(
            "ix_re_org_process_status",
            "resilience_exercises",
            ["organization_id", "process_id", "status"],
        )
        op.create_index(
            "ix_re_org_outcome",
            "resilience_exercises",
            ["organization_id", "outcome"],
        )

    # ── 6. Create resilience_evidence_links ─────────────────────────────────
    if "resilience_evidence_links" not in existing_tables:
        op.create_table(
            "resilience_evidence_links",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "continuity_plan_id",
                sa.Integer(),
                sa.ForeignKey("continuity_plans.id", ondelete="CASCADE"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "exercise_id",
                sa.Integer(),
                sa.ForeignKey("resilience_exercises.id", ondelete="CASCADE"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "evidence_item_id",
                sa.Integer(),
                sa.ForeignKey("evidence_items.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "evidence_type_context",
                sa.Enum(
                    "CONTINUITY_RUNBOOK",
                    "RUNBOOK_DOCUMENT",
                    "ARCHITECTURE_DIAGRAM",
                    "EXERCISE_LOG",
                    "FAILOVER_LOG",
                    "FAILOVER_TELEMETRY",
                    "BACKUP_RESTORE_PROOF",
                    "RESTORATION_SCREENSHOT",
                    "OBSERVER_SIGN_OFF",
                    "SIGN_OFF_ARTIFACT",
                    "POST_MORTEM_REPORT",
                    "POST_EXERCISE_REPORT",
                    "VENDOR_DR_ATTESTATION",
                    name="resilienceevidencecontextenum",
                ),
                nullable=False,
            ),
            sa.Column("evidence_sha256_snapshot", sa.String(length=64), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "linked_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.CheckConstraint(
                """(
                    (CASE WHEN continuity_plan_id IS NOT NULL THEN 1 ELSE 0 END) +
                    (CASE WHEN exercise_id IS NOT NULL THEN 1 ELSE 0 END)
                ) = 1""",
                name="chk_resilience_evidence_single_subject",
            ),
            sa.UniqueConstraint(
                "organization_id",
                "continuity_plan_id",
                "evidence_item_id",
                name="uq_rel_org_plan_evidence",
            ),
            sa.UniqueConstraint(
                "organization_id",
                "exercise_id",
                "evidence_item_id",
                name="uq_rel_org_exercise_evidence",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "resilience_evidence_links" in existing_tables:
        op.drop_table("resilience_evidence_links")

    if "resilience_exercises" in existing_tables:
        op.drop_table("resilience_exercises")

    if "continuity_recovery_steps" in existing_tables:
        op.drop_table("continuity_recovery_steps")

    if "continuity_plans" in existing_tables:
        op.drop_table("continuity_plans")

    pd_cols = {c["name"] for c in inspector.get_columns("process_dependencies")}
    pd_indexes = {i["name"] for i in inspector.get_indexes("process_dependencies")}

    with op.batch_alter_table("process_dependencies") as batch_op:
        for idx_name in [
            "ix_process_dependencies_depends_on_process_id",
            "ix_process_dependencies_data_asset_id",
            "ix_process_dependencies_cloud_asset_id",
            "ix_process_dependencies_organization_control_id",
            "ix_process_dependencies_vendor_id",
        ]:
            if idx_name in pd_indexes:
                batch_op.drop_index(idx_name)

        for col_name in [
            "criticality_notes",
            "recovery_priority_order",
            "failure_propagation_weight",
            "is_single_point_of_failure",
            "depends_on_process_id",
            "data_asset_id",
            "cloud_asset_id",
            "organization_control_id",
            "vendor_id",
        ]:
            if col_name in pd_cols:
                batch_op.drop_column(col_name)
