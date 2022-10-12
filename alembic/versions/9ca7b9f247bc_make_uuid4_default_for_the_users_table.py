"""make uuid4() default for the users table

Revision ID: 9ca7b9f247bc
Revises: bdff60268a39
Create Date: 2022-10-12 20:37:14.058705

"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ca7b9f247bc'
down_revision = 'bdff60268a39'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "id", default=uuid4, index=False)
    op.alter_column("users", "token_id", default=uuid4, index=False)
    op.alter_column("users", "email", index=False)
    op.alter_column("users", "name", index=False)


def downgrade() -> None:
    pass
