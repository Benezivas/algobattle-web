"""adds the extra points model

Revision ID: 9ce0127fdc78
Revises: 1791b4c03b50
Create Date: 2023-11-22 13:42:13.481491

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9ce0127fdc78'
down_revision = '1791b4c03b50'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('extrapoints',
    sa.Column('tag', sa.String(length=32), nullable=False),
    sa.Column('points', sa.Float(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('team_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name=op.f('fk_extrapoints_team_id_teams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extrapoints'))
    )


def downgrade() -> None:
    op.drop_table('extrapoints')
