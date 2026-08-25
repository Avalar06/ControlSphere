"""0005_risks_exceptions_governance

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-25 22:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create Enums
    risk_category_enum = sa.Enum(
        'CYBERSECURITY',
        'COMPLIANCE',
        'OPERATIONAL',
        'FINANCIAL',
        'STRATEGIC',
        'REPUTATIONAL',
        'THIRD_PARTY',
        'LEGAL',
        name='riskcategoryenum'
    )
    risk_source_enum = sa.Enum(
        'INTERNAL_AUDIT',
        'EXTERNAL_AUDIT',
        'THREAT_INTELLIGENCE',
        'VULNERABILITY_ASSESSMENT',
        'INCIDENT',
        'VENDOR_ASSESSMENT',
        'REGULATORY_CHANGE',
        'BUSINESS_OPERATION',
        name='risksourceenum'
    )
    risk_status_enum = sa.Enum(
        'IDENTIFIED',
        'ASSESSED',
        'TREATMENT_PLANNED',
        'MITIGATING',
        'MONITORING',
        'ACCEPTED',
        'CLOSED',
        name='riskstatusenum'
    )
    risk_treatment_strategy_enum = sa.Enum(
        'MITIGATE',
        'TRANSFER',
        'AVOID',
        'ACCEPT',
        'NOT_SPECIFIED',
        name='risktreatmentstrategyenum'
    )
    exception_type_enum = sa.Enum(
        'CONTROL_DEVIATION',
        'POLICY_EXCEPTION',
        'CONFIGURATION_STANDARD',
        'THIRD_PARTY_VENDOR',
        'ACCESS_CONTROL',
        'OTHER',
        name='exceptiontypeenum'
    )
    exception_status_enum = sa.Enum(
        'REQUESTED',
        'UNDER_REVIEW',
        'APPROVED',
        'ACTIVE',
        'EXPIRED',
        'REJECTED',
        'CLOSED',
        name='exceptionstatusenum'
    )

    risk_category_enum.create(op.get_bind(), checkfirst=True)
    risk_source_enum.create(op.get_bind(), checkfirst=True)
    risk_status_enum.create(op.get_bind(), checkfirst=True)
    risk_treatment_strategy_enum.create(op.get_bind(), checkfirst=True)
    exception_type_enum.create(op.get_bind(), checkfirst=True)
    exception_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create risks table
    op.create_table(
        'risks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('risk_category', risk_category_enum, nullable=False, server_default='CYBERSECURITY'),
        sa.Column('risk_source', risk_source_enum, nullable=False, server_default='INTERNAL_AUDIT'),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('inherent_impact', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('inherent_likelihood', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('inherent_score', sa.Integer(), nullable=False, server_default='9'),
        sa.Column('inherent_band', sa.String(length=20), nullable=False, server_default='MODERATE'),
        sa.Column('residual_impact', sa.Integer(), nullable=True),
        sa.Column('residual_likelihood', sa.Integer(), nullable=True),
        sa.Column('residual_score', sa.Integer(), nullable=True),
        sa.Column('residual_band', sa.String(length=20), nullable=True),
        sa.Column('target_risk_band', sa.String(length=20), nullable=False, server_default='MODERATE'),
        sa.Column('appetite_status', sa.String(length=20), nullable=False, server_default='WITHIN_APPETITE'),
        sa.Column('status', risk_status_enum, nullable=False, server_default='IDENTIFIED'),
        sa.Column('treatment_strategy', risk_treatment_strategy_enum, nullable=False, server_default='NOT_SPECIFIED'),
        sa.Column('treatment_plan', sa.Text(), nullable=True),
        sa.Column('treatment_owner_id', sa.Integer(), nullable=True),
        sa.Column('treatment_due_date', sa.Date(), nullable=True),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('risk_acceptance_justification', sa.Text(), nullable=True),
        sa.Column('risk_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('risk_accepted_by_id', sa.Integer(), nullable=True),
        sa.Column('risk_acceptance_expiry', sa.Date(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['risk_accepted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['treatment_owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risks_id'), 'risks', ['id'], unique=False)
    op.create_index(op.f('ix_risks_organization_id'), 'risks', ['organization_id'], unique=False)
    op.create_index(op.f('ix_risks_title'), 'risks', ['title'], unique=False)
    op.create_index(op.f('ix_risks_risk_category'), 'risks', ['risk_category'], unique=False)
    op.create_index(op.f('ix_risks_risk_source'), 'risks', ['risk_source'], unique=False)
    op.create_index(op.f('ix_risks_owner_id'), 'risks', ['owner_id'], unique=False)
    op.create_index(op.f('ix_risks_inherent_score'), 'risks', ['inherent_score'], unique=False)
    op.create_index(op.f('ix_risks_inherent_band'), 'risks', ['inherent_band'], unique=False)
    op.create_index(op.f('ix_risks_residual_score'), 'risks', ['residual_score'], unique=False)
    op.create_index(op.f('ix_risks_residual_band'), 'risks', ['residual_band'], unique=False)
    op.create_index(op.f('ix_risks_appetite_status'), 'risks', ['appetite_status'], unique=False)
    op.create_index(op.f('ix_risks_status'), 'risks', ['status'], unique=False)
    op.create_index(op.f('ix_risks_treatment_strategy'), 'risks', ['treatment_strategy'], unique=False)
    op.create_index(op.f('ix_risks_treatment_due_date'), 'risks', ['treatment_due_date'], unique=False)
    op.create_index(op.f('ix_risks_review_date'), 'risks', ['review_date'], unique=False)

    # 3. Create risk_control_links table
    op.create_table(
        'risk_control_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('risk_id', sa.Integer(), nullable=False),
        sa.Column('organization_control_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_control_id'], ['organization_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['risk_id'], ['risks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('risk_id', 'organization_control_id', name='uq_risk_control_link')
    )
    op.create_index(op.f('ix_risk_control_links_id'), 'risk_control_links', ['id'], unique=False)
    op.create_index(op.f('ix_risk_control_links_organization_id'), 'risk_control_links', ['organization_id'], unique=False)
    op.create_index(op.f('ix_risk_control_links_risk_id'), 'risk_control_links', ['risk_id'], unique=False)
    op.create_index(op.f('ix_risk_control_links_organization_control_id'), 'risk_control_links', ['organization_control_id'], unique=False)

    # 4. Create risk_finding_links table
    op.create_table(
        'risk_finding_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('risk_id', sa.Integer(), nullable=False),
        sa.Column('finding_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['risk_id'], ['risks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('risk_id', 'finding_id', name='uq_risk_finding_link')
    )
    op.create_index(op.f('ix_risk_finding_links_id'), 'risk_finding_links', ['id'], unique=False)
    op.create_index(op.f('ix_risk_finding_links_organization_id'), 'risk_finding_links', ['organization_id'], unique=False)
    op.create_index(op.f('ix_risk_finding_links_risk_id'), 'risk_finding_links', ['risk_id'], unique=False)
    op.create_index(op.f('ix_risk_finding_links_finding_id'), 'risk_finding_links', ['finding_id'], unique=False)

    # 5. Create security_exceptions table
    op.create_table(
        'security_exceptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('exception_type', exception_type_enum, nullable=False, server_default='CONTROL_DEVIATION'),
        sa.Column('status', exception_status_enum, nullable=False, server_default='REQUESTED'),
        sa.Column('requested_by_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('residual_risk_level', sa.String(length=20), nullable=False, server_default='MODERATE'),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('closure_notes', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_id', sa.Integer(), nullable=True),
        sa.Column('linked_organization_control_id', sa.Integer(), nullable=True),
        sa.Column('linked_policy_id', sa.Integer(), nullable=True),
        sa.Column('linked_finding_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['linked_finding_id'], ['findings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['linked_organization_control_id'], ['organization_controls.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['linked_policy_id'], ['policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_security_exceptions_id'), 'security_exceptions', ['id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_organization_id'), 'security_exceptions', ['organization_id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_title'), 'security_exceptions', ['title'], unique=False)
    op.create_index(op.f('ix_security_exceptions_exception_type'), 'security_exceptions', ['exception_type'], unique=False)
    op.create_index(op.f('ix_security_exceptions_status'), 'security_exceptions', ['status'], unique=False)
    op.create_index(op.f('ix_security_exceptions_requested_by_id'), 'security_exceptions', ['requested_by_id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_owner_id'), 'security_exceptions', ['owner_id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_reviewer_id'), 'security_exceptions', ['reviewer_id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_effective_date'), 'security_exceptions', ['effective_date'], unique=False)
    op.create_index(op.f('ix_security_exceptions_expiry_date'), 'security_exceptions', ['expiry_date'], unique=False)
    op.create_index(op.f('ix_security_exceptions_review_date'), 'security_exceptions', ['review_date'], unique=False)
    op.create_index(op.f('ix_security_exceptions_linked_organization_control_id'), 'security_exceptions', ['linked_organization_control_id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_linked_policy_id'), 'security_exceptions', ['linked_policy_id'], unique=False)
    op.create_index(op.f('ix_security_exceptions_linked_finding_id'), 'security_exceptions', ['linked_finding_id'], unique=False)

    # 6. Create exception_compensating_controls table
    op.create_table(
        'exception_compensating_controls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('exception_id', sa.Integer(), nullable=False),
        sa.Column('organization_control_id', sa.Integer(), nullable=False),
        sa.Column('implementation_notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['exception_id'], ['security_exceptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_control_id'], ['organization_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exception_id', 'organization_control_id', name='uq_exception_control')
    )
    op.create_index(op.f('ix_exception_compensating_controls_id'), 'exception_compensating_controls', ['id'], unique=False)
    op.create_index(op.f('ix_exception_compensating_controls_organization_id'), 'exception_compensating_controls', ['organization_id'], unique=False)
    op.create_index(op.f('ix_exception_compensating_controls_exception_id'), 'exception_compensating_controls', ['exception_id'], unique=False)
    op.create_index(op.f('ix_exception_compensating_controls_organization_control_id'), 'exception_compensating_controls', ['organization_control_id'], unique=False)


def downgrade() -> None:
    op.drop_table('exception_compensating_controls')
    op.drop_table('security_exceptions')
    op.drop_table('risk_finding_links')
    op.drop_table('risk_control_links')
    op.drop_table('risks')

    op.execute('DROP TYPE IF EXISTS exceptionstatusenum CASCADE')
    op.execute('DROP TYPE IF EXISTS exceptiontypeenum CASCADE')
    op.execute('DROP TYPE IF EXISTS risktreatmentstrategyenum CASCADE')
    op.execute('DROP TYPE IF EXISTS riskstatusenum CASCADE')
    op.execute('DROP TYPE IF EXISTS risksourceenum CASCADE')
    op.execute('DROP TYPE IF EXISTS riskcategoryenum CASCADE')
