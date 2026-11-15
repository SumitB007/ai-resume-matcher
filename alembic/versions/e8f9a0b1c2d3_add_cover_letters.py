"""add cover_letters table (Phase 14 — cover letters)

Revision ID: e8f9a0b1c2d3
Revises: d4e5f6a7b8c9
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cover_letters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('template_id', sa.String(length=50), nullable=False),
        sa.Column('theme', sa.JSON(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.Column('resume_document_id', sa.Integer(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['job_descriptions.id']),
        sa.ForeignKeyConstraint(['resume_document_id'], ['resume_documents.id']),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cover_letters_id'), 'cover_letters', ['id'], unique=False)
    op.create_index(op.f('ix_cover_letters_user_id'), 'cover_letters', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cover_letters_user_id'), table_name='cover_letters')
    op.drop_index(op.f('ix_cover_letters_id'), table_name='cover_letters')
    op.drop_table('cover_letters')
