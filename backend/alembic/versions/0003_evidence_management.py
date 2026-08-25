"""0003_evidence_management

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-25 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create Enums
    evidence_type_enum = sa.Enum(
        'DOCUMENT',
        'CONFIGURATION',
        'LOG_EXPORT',
        'SCREENSHOT',
        'POLICY_DOCUMENT',
        'AUDIT_REPORT',
        'OTHER',
        name='evidencetypeenum'
    )
    evidence_status_enum = sa.Enum(
        'UPLOADED',
        'UNDER_REVIEW',
        'ACCEPTED',
        'REJECTED',
        'SUPERSEDED',
        name='evidencestatusenum'
    )
    review_decision_enum = sa.Enum(
        'ACCEPT',
        'REJECT',
        name='reviewdecisionenum'
    )

    # 2. Table: evidence_requirements
    op.create_table(
        'evidence_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('organization_control_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_type', evidence_type_enum, nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('guidance', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_control_id'], ['organization_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_requirements_id', 'evidence_requirements', ['id'])
    op.create_index('ix_evidence_requirements_organization_id', 'evidence_requirements', ['organization_id'])
    op.create_index('ix_evidence_requirements_organization_control_id', 'evidence_requirements', ['organization_control_id'])
    op.create_index('ix_evidence_requirements_evidence_type', 'evidence_requirements', ['evidence_type'])

    # 3. Table: evidence_items
    op.create_table(
        'evidence_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('organization_control_id', sa.Integer(), nullable=False),
        sa.Column('evidence_requirement_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('file_extension', sa.String(length=20), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('status', evidence_status_enum, nullable=False),
        sa.Column('superseded_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_control_id'], ['organization_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_requirement_id'], ['evidence_requirements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['evidence_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_items_id', 'evidence_items', ['id'])
    op.create_index('ix_evidence_items_organization_id', 'evidence_items', ['organization_id'])
    op.create_index('ix_evidence_items_organization_control_id', 'evidence_items', ['organization_control_id'])
    op.create_index('ix_evidence_items_evidence_requirement_id', 'evidence_items', ['evidence_requirement_id'])
    op.create_index('ix_evidence_items_uploaded_by_id', 'evidence_items', ['uploaded_by_id'])
    op.create_index('ix_evidence_items_title', 'evidence_items', ['title'])
    op.create_index('ix_evidence_items_sha256_hash', 'evidence_items', ['sha256_hash'])
    op.create_index('ix_evidence_items_status', 'evidence_items', ['status'])

    # 4. Table: evidence_reviews
    op.create_table(
        'evidence_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('decision', review_decision_enum, nullable=False),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_reviews_id', 'evidence_reviews', ['id'])
    op.create_index('ix_evidence_reviews_organization_id', 'evidence_reviews', ['organization_id'])
    op.create_index('ix_evidence_reviews_evidence_id', 'evidence_reviews', ['evidence_id'])
    op.create_index('ix_evidence_reviews_reviewer_id', 'evidence_reviews', ['reviewer_id'])
    op.create_index('ix_evidence_reviews_decision', 'evidence_reviews', ['decision'])


def downgrade() -> None:
    op.drop_table('evidence_reviews')
    op.drop_table('evidence_items')
    op.drop_table('evidence_requirements')
    op.execute('DROP TYPE IF EXISTS reviewdecisionenum;')
    op.execute('DROP TYPE IF EXISTS evidencestatusenum;')
    op.execute('DROP TYPE IF EXISTS evidencetypeenum;')