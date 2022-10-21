"Module specifying the login page."
from __future__ import annotations
from typing import Any, Iterator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from algobattle_web.util import config



