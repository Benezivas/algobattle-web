"Module specifying the login page."
from __future__ import annotations
from abc import ABC
from datetime import datetime
import functools
import json
from pathlib import Path
from typing import Annotated, Any, Callable, Concatenate, Iterator, ParamSpec, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import create_engine, TypeDecorator, Unicode, DateTime
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, registry, mapped_column, Mapped
from sqlalchemy_utils import UUIDType
from sqlalchemy_media import StoreManager, FileSystemStore, File as SqlFile, Attachable, Attachment
from starlette.datastructures import UploadFile
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from algobattle_web.base_classes import BaseSchema
from algobattle_web.config import SQLALCHEMY_DATABASE_URL, STORAGE_PATH

ID = Annotated[UUID, mapped_column(default=uuid4)]

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
StoreManager.register("fs", functools.partial(FileSystemStore, STORAGE_PATH, ""), True)


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
                return cls(name=value.original_filename)
            else:
                raise TypeError

DbFile.associate_with(Json)


P = ParamSpec("P")
T = TypeVar("T")
def with_store_manager(func: Callable[Concatenate[Any, Session, P], T]) -> Callable[Concatenate[Any, Session, P], T]:
    def inner(obj, db: Session, *args: P.args, **kwargs: P.kwargs) -> T:
        if obj.use_store_manager:
            with StoreManager(db):
                return func(obj, db, *args, **kwargs)
        else:
            return func(obj, db, *args, **kwargs)
    return inner

class Base(DeclarativeBase):
    registry = registry(
        type_annotation_map={
            UUID: UUIDType,
            datetime: DateTime,
            DbFile: Json,
        }
    )

    id: Mapped[ID] = mapped_column(primary_key=True)

    use_store_manager: bool = False

    class Schema(BaseSchema, ABC):
        id: ID

    @classmethod
    @property
    def __tablename__(cls):
        return cls.__name__.lower() + "s"

    @with_store_manager
    def delete(self, db: Session):
        db.delete(self)
        db.commit()

    def encode(self) -> dict[str, Any]:
        return jsonable_encoder(self.Schema.from_orm(self))
