"""add resume_documents table (Phase 13 — resume builder)

Revision ID: d4e5f6a7b8c9
Revises: c7d2e9f4a1b8
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c7d2e9f4a1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resume_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('template_id', sa.String(length=50), nullable=False),
        sa.Column('theme', sa.JSON(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_documents_id'), 'resume_documents', ['id'], unique=False)
    op.create_index(op.f('ix_resume_documents_user_id'), 'resume_documents', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_resume_documents_user_id'), table_name='resume_documents')
    op.drop_index(op.f('ix_resume_documents_id'), table_name='resume_documents')
    op.drop_table('resume_documents')
