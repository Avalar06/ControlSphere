"""0004_assessments_findings_remediation

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-25 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create Enums
    assessment_method_enum = sa.Enum(
        'EXAMINATION',
        'INTERVIEW',
        'TESTING',
        'AUTOMATED_VERIFICATION',
        'COMBINED',
        name='assessmentmethodenum'
    )
    assessment_status_enum = sa.Enum(
        'DRAFT',
        'IN_PROGRESS',
        'COMPLETED',
        'SUPERSEDED',
        name='assessmentstatusenum'
    )
    assessment_conclusion_enum = sa.Enum(
        'EFFECTIVE',
        'PARTIALLY_EFFECTIVE',
        'INEFFECTIVE',
        'NOT_ASSESSED',
        name='assessmentconclusionenum'
    )
    finding_type_enum = sa.Enum(
        'CONTROL_GAP',
        'EVIDENCE_GAP',
        'POLICY_GAP',
        'PROCESS_GAP',
        'TECHNICAL_GAP',
        'OTHER',
        name='findingtypeenum'
    )
    finding_severity_enum = sa.Enum(
        'CRITICAL',
        'HIGH',
        'MEDIUM',
        'LOW',
        'INFORMATIONAL',
        name='findingseverityenum'
    )
    finding_status_enum = sa.Enum(
        'OPEN',
        'IN_REMEDIATION',
        'PENDING_VALIDATION',
        'RESOLVED',
        'ACCEPTED_RISK',
        'CLOSED',
        name='findingstatusenum'
    )

    assessment_method_enum.create(op.get_bind(), checkfirst=True)
    assessment_status_enum.create(op.get_bind(), checkfirst=True)
    assessment_conclusion_enum.create(op.get_bind(), checkfirst=True)
    finding_type_enum.create(op.get_bind(), checkfirst=True)
    finding_severity_enum.create(op.get_bind(), checkfirst=True)
    finding_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create assessments table
    op.create_table(
        'assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('organization_control_id', sa.Integer(), nullable=False),
        sa.Column('assessor_id', sa.Integer(), nullable=True),
        sa.Column('assessment_method', assessment_method_enum, nullable=False, server_default='EXAMINATION'),
        sa.Column('assessment_scope', sa.Text(), nullable=True),
        sa.Column('assessment_date', sa.Date(), nullable=False),
        sa.Column('status', assessment_status_enum, nullable=False, server_default='DRAFT'),
        sa.Column('conclusion', assessment_conclusion_enum, nullable=False, server_default='NOT_ASSESSED'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('limitations', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['assessor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_control_id'], ['organization_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessments_id'), 'assessments', ['id'], unique=False)
    op.create_index(op.f('ix_assessments_organization_id'), 'assessments', ['organization_id'], unique=False)
    op.create_index(op.f('ix_assessments_organization_control_id'), 'assessments', ['organization_control_id'], unique=False)
    op.create_index(op.f('ix_assessments_assessor_id'), 'assessments', ['assessor_id'], unique=False)
    op.create_index(op.f('ix_assessments_status'), 'assessments', ['status'], unique=False)
    op.create_index(op.f('ix_assessments_conclusion'), 'assessments', ['conclusion'], unique=False)

    # 3. Create assessment_evidence association table
    op.create_table(
        'assessment_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'evidence_id', name='uq_assessment_evidence')
    )
    op.create_index(op.f('ix_assessment_evidence_id'), 'assessment_evidence', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_evidence_organization_id'), 'assessment_evidence', ['organization_id'], unique=False)
    op.create_index(op.f('ix_assessment_evidence_assessment_id'), 'assessment_evidence', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_assessment_evidence_evidence_id'), 'assessment_evidence', ['evidence_id'], unique=False)

    # 4. Create findings table
    op.create_table(
        'findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('organization_control_id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('finding_type', finding_type_enum, nullable=False, server_default='CONTROL_GAP'),
        sa.Column('severity', finding_severity_enum, nullable=False, server_default='MEDIUM'),
        sa.Column('impact', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('likelihood', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('risk_score', sa.Integer(), nullable=False, server_default='9'),
        sa.Column('risk_band', sa.String(length=20), nullable=False, server_default='MODERATE'),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', finding_status_enum, nullable=False, server_default='OPEN'),
        sa.Column('remediation_plan', sa.Text(), nullable=True),
        sa.Column('remediation_notes', sa.Text(), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_id', sa.Integer(), nullable=True),
        sa.Column('risk_acceptance_justification', sa.Text(), nullable=True),
        sa.Column('risk_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('risk_accepted_by_id', sa.Integer(), nullable=True),
        sa.Column('risk_acceptance_expiry', sa.Date(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_control_id'], ['organization_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['risk_accepted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_findings_id'), 'findings', ['id'], unique=False)
    op.create_index(op.f('ix_findings_organization_id'), 'findings', ['organization_id'], unique=False)
    op.create_index(op.f('ix_findings_organization_control_id'), 'findings', ['organization_control_id'], unique=False)
    op.create_index(op.f('ix_findings_assessment_id'), 'findings', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_findings_title'), 'findings', ['title'], unique=False)
    op.create_index(op.f('ix_findings_finding_type'), 'findings', ['finding_type'], unique=False)
    op.create_index(op.f('ix_findings_severity'), 'findings', ['severity'], unique=False)
    op.create_index(op.f('ix_findings_risk_score'), 'findings', ['risk_score'], unique=False)
    op.create_index(op.f('ix_findings_risk_band'), 'findings', ['risk_band'], unique=False)
    op.create_index(op.f('ix_findings_owner_id'), 'findings', ['owner_id'], unique=False)
    op.create_index(op.f('ix_findings_due_date'), 'findings', ['due_date'], unique=False)
    op.create_index(op.f('ix_findings_status'), 'findings', ['status'], unique=False)

    # 5. Create finding_evidence association table
    op.create_table(
        'finding_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('finding_id', 'evidence_id', name='uq_finding_evidence')
    )
    op.create_index(op.f('ix_finding_evidence_id'), 'finding_evidence', ['id'], unique=False)
    op.create_index(op.f('ix_finding_evidence_organization_id'), 'finding_evidence', ['organization_id'], unique=False)
    op.create_index(op.f('ix_finding_evidence_finding_id'), 'finding_evidence', ['finding_id'], unique=False)
    op.create_index(op.f('ix_finding_evidence_evidence_id'), 'finding_evidence', ['evidence_id'], unique=False)


def downgrade() -> None:
    op.drop_table('finding_evidence')
    op.drop_table('findings')
    op.drop_table('assessment_evidence')
    op.drop_table('assessments')

    op.execute('DROP TYPE IF EXISTS findingstatusenum CASCADE')
    op.execute('DROP TYPE IF EXISTS findingseverityenum CASCADE')
    op.execute('DROP TYPE IF EXISTS findingtypeenum CASCADE')
    op.execute('DROP TYPE IF EXISTS assessmentconclusionenum CASCADE')
    op.execute('DROP TYPE IF EXISTS assessmentstatusenum CASCADE')
    op.execute('DROP TYPE IF EXISTS assessmentmethodenum CASCADE')
