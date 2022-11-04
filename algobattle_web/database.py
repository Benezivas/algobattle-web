"Module specifying the login page."
from __future__ import annotations
from abc import ABC
import functools
import json
from pathlib import Path
from typing import Any, Iterator, Type
from sqlalchemy import create_engine, TypeDecorator, Unicode
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_media import StoreManager, FileSystemStore, File as SqlFile, Attachable, Attachment
from algobattle_web.base_classes import BaseSchema, Common, DbBase
from starlette.datastructures import UploadFile
from fastapi.responses import FileResponse

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


class DbFile(SqlFile):
    def attach(
        self,
        attachable: Attachable | UploadFile,
        content_type: str | None = None,
        original_filename: str | None = None,
        extension: str | None = None,
        store_id: str | None = None,
        overwrite: bool = False,
        suppress_pre_process: bool = False,
        suppress_validation: bool = False,
        **kwargs,
    ) -> Attachment:
        if isinstance(attachable, UploadFile):
            file = attachable.file
            filename = attachable.filename
        else:
            file = attachable
            filename = None
        return super().attach(
            file,
            content_type,   # type: ignore
            filename,   # type: ignore
            extension,  # type: ignore
            store_id,   # type: ignore
            overwrite,
            suppress_pre_process,
            suppress_validation,
            **kwargs,
        )
    
    def response(self) -> FileResponse:
        """Creates a fastapi FileResponse that serves this file."""
        return FileResponse(Path(STORAGE_PATH) / self.path, filename=self.original_filename)
    
    class Schema(BaseSchema, ABC):
        name: str

        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, value: Any) -> DbFile.Schema:
            if isinstance(value, DbFile.Schema):
                return value
            elif isinstance(value, DbFile):
                return cls(name=value.filename)
            else:
                raise TypeError


DbFile.as_mutable(Json)
