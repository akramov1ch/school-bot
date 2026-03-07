"""add user language

Revision ID: 0002_user_lang
Revises: 0001_initial
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_user_lang'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('lang', sa.String(length=2), nullable=False, server_default='uz'))


def downgrade() -> None:
    op.drop_column('users', 'lang')
