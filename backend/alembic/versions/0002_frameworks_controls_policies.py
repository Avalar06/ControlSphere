"""frameworks_controls_policies

Revision ID: 0002_frameworks_controls_policies
Revises: 0001_initial
Create Date: 2026-08-25 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_frameworks_controls_policies'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Framework Catalog Tables
    op.create_table(
        'frameworks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=20), server_default='2.0', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_frameworks_id'), 'frameworks', ['id'], unique=False)
    op.create_index(op.f('ix_frameworks_identifier'), 'frameworks', ['identifier'], unique=True)

    op.create_table(
        'framework_functions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('framework_id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['framework_id'], ['frameworks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_framework_functions_id'), 'framework_functions', ['id'], unique=False)
    op.create_index(op.f('ix_framework_functions_framework_id'), 'framework_functions', ['framework_id'], unique=False)
    op.create_index(op.f('ix_framework_functions_identifier'), 'framework_functions', ['identifier'], unique=False)

    op.create_table(
        'framework_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('function_id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['function_id'], ['framework_functions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_framework_categories_id'), 'framework_categories', ['id'], unique=False)
    op.create_index(op.f('ix_framework_categories_function_id'), 'framework_categories', ['function_id'], unique=False)
    op.create_index(op.f('ix_framework_categories_identifier'), 'framework_categories', ['identifier'], unique=False)

    op.create_table(
        'framework_subcategories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['framework_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_framework_subcategories_id'), 'framework_subcategories', ['id'], unique=False)
    op.create_index(op.f('ix_framework_subcategories_category_id'), 'framework_subcategories', ['category_id'], unique=False)
    op.create_index(op.f('ix_framework_subcategories_identifier'), 'framework_subcategories', ['identifier'], unique=True)

    # 2. Organization Controls Table
    impl_status_enum = sa.Enum(
        'NOT_STARTED', 'IN_PROGRESS', 'PARTIALLY_IMPLEMENTED', 'IMPLEMENTED', 'NOT_APPLICABLE', 'NEEDS_REVIEW',
        name='implementationstatusenum'
    )
    priority_enum = sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='priorityenum')

    op.create_table(
        'organization_controls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('subcategory_id', sa.Integer(), nullable=False),
        sa.Column('status', impl_status_enum, server_default='NOT_STARTED', nullable=False),
        sa.Column('priority', priority_enum, server_default='MEDIUM', nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('implementation_statement', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subcategory_id'], ['framework_subcategories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'subcategory_id', name='uq_org_control_org_subcat')
    )
    op.create_index(op.f('ix_organization_controls_id'), 'organization_controls', ['id'], unique=False)
    op.create_index(op.f('ix_organization_controls_organization_id'), 'organization_controls', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_controls_subcategory_id'), 'organization_controls', ['subcategory_id'], unique=False)
    op.create_index(op.f('ix_organization_controls_status'), 'organization_controls', ['status'], unique=False)
    op.create_index(op.f('ix_organization_controls_owner_id'), 'organization_controls', ['owner_id'], unique=False)

    # 3. Policy Tables
    policy_status_enum = sa.Enum('DRAFT', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED', name='policystatusenum')
    policy_type_enum = sa.Enum(
        'ACCESS_CONTROL', 'INFORMATION_SECURITY', 'INCIDENT_RESPONSE', 'DATA_PROTECTION',
        'RISK_MANAGEMENT', 'BUSINESS_CONTINUITY', 'VENDOR_MANAGEMENT', 'ACCEPTABLE_USE',
        'CRYPTOGRAPHY', 'CHANGE_MANAGEMENT', 'OTHER',
        name='policytypeenum'
    )

    op.create_table(
        'policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('policy_type', policy_type_enum, server_default='INFORMATION_SECURITY', nullable=False),
        sa.Column('status', policy_status_enum, server_default='DRAFT', nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('review_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policies_id'), 'policies', ['id'], unique=False)
    op.create_index(op.f('ix_policies_organization_id'), 'policies', ['organization_id'], unique=False)
    op.create_index(op.f('ix_policies_title'), 'policies', ['title'], unique=False)
    op.create_index(op.f('ix_policies_policy_type'), 'policies', ['policy_type'], unique=False)
    op.create_index(op.f('ix_policies_status'), 'policies', ['status'], unique=False)
    op.create_index(op.f('ix_policies_owner_id'), 'policies', ['owner_id'], unique=False)

    op.create_table(
        'policy_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('change_summary', sa.String(length=255), server_default='Initial version', nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'version_number', name='uq_policy_version_number')
    )
    op.create_index(op.f('ix_policy_versions_id'), 'policy_versions', ['id'], unique=False)
    op.create_index(op.f('ix_policy_versions_policy_id'), 'policy_versions', ['policy_id'], unique=False)

    op.create_table(
        'policy_control_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('subcategory_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subcategory_id'], ['framework_subcategories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'policy_id', 'subcategory_id', name='uq_org_policy_control_mapping')
    )
    op.create_index(op.f('ix_policy_control_mappings_id'), 'policy_control_mappings', ['id'], unique=False)
    op.create_index(op.f('ix_policy_control_mappings_organization_id'), 'policy_control_mappings', ['organization_id'], unique=False)
    op.create_index(op.f('ix_policy_control_mappings_policy_id'), 'policy_control_mappings', ['policy_id'], unique=False)
    op.create_index(op.f('ix_policy_control_mappings_subcategory_id'), 'policy_control_mappings', ['subcategory_id'], unique=False)


def downgrade() -> None:
    op.drop_table('policy_control_mappings')
    op.drop_table('policy_versions')
    op.drop_table('policies')
    op.drop_table('organization_controls')
    op.execute('DROP TYPE policystatusenum')
    op.execute('DROP TYPE policytypeenum')
    op.execute('DROP TYPE implementationstatusenum')
    op.execute('DROP TYPE priorityenum')
    op.drop_table('framework_subcategories')
    op.drop_table('framework_categories')
    op.drop_table('framework_functions')
    op.drop_table('frameworks')