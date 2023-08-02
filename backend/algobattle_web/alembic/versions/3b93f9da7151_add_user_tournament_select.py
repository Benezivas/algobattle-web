"""add user tournament select

Revision ID: 3b93f9da7151
Revises: 5c12167db83e
Create Date: 2023-08-02 19:40:42.672978

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3b93f9da7151"
down_revision = "5c12167db83e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usersettings", sa.Column("tournament_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_usersettings_tournament_id_tournaments"), "usersettings", "tournaments", ["tournament_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_usersettings_tournament_id_tournaments"), "usersettings", type_="foreignkey")
    op.drop_column("usersettings", "tournament_id")
