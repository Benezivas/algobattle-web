"""Adds the upload limit setting

Revision ID: 1791b4c03b50
Revises: 6aee42c9b57d
Create Date: 2023-10-30 21:02:09.232407

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1791b4c03b50"
down_revision = "6aee42c9b57d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("serversettingss", sa.Column("upload_file_limit", sa.Integer(), nullable=False))


def downgrade() -> None:
    op.drop_column("serversettingss", "upload_file_limit")
