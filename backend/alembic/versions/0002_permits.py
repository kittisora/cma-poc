"""permits (building permits and site records)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('permit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('record_id', sa.String(length=40), nullable=False),
    sa.Column('pin', sa.String(length=30), nullable=True),
    sa.Column('app_type', sa.String(length=120), nullable=True),
    sa.Column('project_name', sa.String(length=300), nullable=True),
    sa.Column('status', sa.String(length=80), nullable=True),
    sa.Column('status_date', sa.Date(), nullable=True),
    sa.Column('submitted_date', sa.Date(), nullable=True),
    sa.Column('issued_date', sa.Date(), nullable=True),
    sa.Column('closed_date', sa.Date(), nullable=True),
    sa.Column('address', sa.String(length=200), nullable=True),
    sa.Column('zip', sa.String(length=10), nullable=True),
    sa.Column('link_url', sa.String(length=500), nullable=True),
    sa.Column('raw', sa.JSON(), nullable=False),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_run_id', sa.Integer(), nullable=True),
    sa.Column('in_latest_source', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['last_seen_run_id'], ['refresh_run.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider', 'kind', 'record_id', name='uq_permit_record')
    )
    with op.batch_alter_table('permit', schema=None) as batch_op:
        batch_op.create_index('ix_permit_status', ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_permit_pin'), ['pin'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('permit', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_permit_pin'))
        batch_op.drop_index('ix_permit_status')
    op.drop_table('permit')
