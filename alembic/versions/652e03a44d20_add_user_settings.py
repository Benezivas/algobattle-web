"""add user settings

Revision ID: 652e03a44d20
Revises: 9ca7b9f247bc
Create Date: 2022-11-06 12:25:39.057128

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import create_engine, TypeDecorator, Unicode
from sqlalchemy.orm import sessionmaker, Session
from algobattle_web.config import SQLALCHEMY_DATABASE_URL

from algobattle_web.models import User, UserSettings


# revision identifiers, used by Alembic.
revision = '652e03a44d20'
down_revision = '9ca7b9f247bc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db: Session = SessionLocal()
    for user in db.query(User).all():
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()
    db.close()

def downgrade() -> None:
    pass
