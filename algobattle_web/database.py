"Module specifying the login page."
from __future__ import annotations
import functools
import json
from typing import Any, Iterator, Type
from sqlalchemy import create_engine, TypeDecorator, Unicode
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_media import StoreManager, FileSystemStore, File as SqlFile
from algobattle_web.base_classes import Common, DbBase

from algobattle_web.config import SQLALCHEMY_DATABASE_URL, STORAGE_PATH


engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base: Type[DbBase] = declarative_base(cls=Common)

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Json(TypeDecorator[Any]):
    impl = Unicode

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return json.loads(value)


StoreManager.register("fs", functools.partial(FileSystemStore, STORAGE_PATH, ""), True)
DbFile: Type[SqlFile] = SqlFile.as_mutable(Json)
File: Type[SqlFile] = SqlFile
