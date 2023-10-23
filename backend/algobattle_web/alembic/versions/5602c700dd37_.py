"""empty message

Revision ID: 5602c700dd37
Revises: 5c12167db83e
Create Date: 2023-10-16 00:13:41.186990

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5602c700dd37"
down_revision = "5c12167db83e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("serversettingss", sa.Column("landing_page_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_serversettingss_landing_page_id_files"), "serversettingss", "files", ["landing_page_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_serversettingss_landing_page_id_files"), "serversettingss", type_="foreignkey")
    op.drop_column("serversettingss", "landing_page_id")
