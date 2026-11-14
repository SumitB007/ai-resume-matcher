"""add ats_check_results table (Phase 12 — standalone ATS checker)

Revision ID: c7d2e9f4a1b8
Revises: 5ac208bfc6b1
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d2e9f4a1b8'
down_revision: Union[str, None] = '5ac208bfc6b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ats_check_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ats_check_results_id'), 'ats_check_results', ['id'], unique=False)
    op.create_index(op.f('ix_ats_check_results_resume_id'), 'ats_check_results', ['resume_id'], unique=False)
    op.create_index(op.f('ix_ats_check_results_user_id'), 'ats_check_results', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ats_check_results_user_id'), table_name='ats_check_results')
    op.drop_index(op.f('ix_ats_check_results_resume_id'), table_name='ats_check_results')
    op.drop_index(op.f('ix_ats_check_results_id'), table_name='ats_check_results')
    op.drop_table('ats_check_results')
