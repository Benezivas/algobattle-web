"""empty message

Revision ID: 6aee42c9b57d
Revises: 5602c700dd37
Create Date: 2023-10-24 00:41:36.815162

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '6aee42c9b57d'
down_revision = '5c12167db83e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('serversettingss', sa.Column('home_page_id', sa.Uuid(), nullable=True))
    op.add_column('serversettingss', sa.Column('home_page_compiled', sa.Text(), nullable=True))
    op.create_foreign_key(op.f('fk_serversettingss_home_page_id_files'), 'serversettingss', 'files', ['home_page_id'], ['id'])
    op.alter_column('serversettingss', 'secret_key',
               existing_type=mysql.TINYBLOB(),
               type_=sa.LargeBinary(length=64),
               existing_nullable=False)


def downgrade() -> None:
    op.drop_column('serversettingss', 'home_page_id')
    op.drop_column('serversettingss', 'home_page_compiled')
    op.drop_constraint(op.f('fk_serversettingss_home_page_id_files'), 'serversettingss', type_='foreignkey')
    op.alter_column('serversettingss', 'secret_key',
               existing_type=sa.LargeBinary(length=64),
               type_=mysql.TINYBLOB(),
               existing_nullable=False)
