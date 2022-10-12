"""add is_admin to users

Revision ID: bdff60268a39
Revises: 
Create Date: 2022-10-12 20:13:58.931811

"""
from alembic import op
from sqlalchemy import Column, Boolean


# revision identifiers, used by Alembic.
revision = 'bdff60268a39'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", Column("is_admin", Boolean, default=False))


def downgrade() -> None:
    pass
