"Module specifying the login page."
from __future__ import annotations
from abc import ABC
from dataclasses import InitVar, dataclass
from datetime import datetime
import functools
from inspect import iscoroutinefunction, signature
import json
from pathlib import Path
from typing import Annotated, Any, AsyncIterable, Callable, Concatenate, ParamSpec, Sequence, Type, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import create_engine, TypeDecorator, Unicode, DateTime, select
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, registry, mapped_column, Mapped, MappedAsDataclass
from sqlalchemy_utils import UUIDType
from sqlalchemy_media import StoreManager, FileSystemStore, File as SqlFile, Attachable
from starlette.datastructures import UploadFile
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from algobattle_web.base_classes import BaseSchema
from algobattle_web.config import SQLALCHEMY_DATABASE_URL, STORAGE_PATH

ID = Annotated[UUID, mapped_column(default=uuid4)]

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autoflush=False, bind=engine)
StoreManager.register("fs", functools.partial(FileSystemStore, STORAGE_PATH, ""), True)


async def get_db() -> AsyncIterable[Session]:
    with SessionLocal() as db, StoreManager(db):
        yield db


P = ParamSpec("P")
R = TypeVar("R")


def autocommit(fn: Callable[P, R]) -> Callable[P, R]:
    """Automatically commits the database transaction."""
    if iscoroutinefunction(fn):
        async def inner_async(*args: P.args, **kwargs: P.kwargs) -> R:
            db = kwargs["db"]
            assert isinstance(db, Session)
            with StoreManager(db):
                res = await fn(*args, **kwargs)
                db.commit()
                return res
        inner_async.__annotations__ = fn.__annotations__
        inner_async.__signature__ = signature(fn)
        return cast(Callable[P, R], inner_async)
    else:
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            db = kwargs["db"]
            assert isinstance(db, Session)
            with StoreManager(db):
                res = fn(*args, **kwargs)
                db.commit()
                return res
        inner.__annotations__ = fn.__annotations__
        inner.__signature__ = signature(fn)
        return inner


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
    ) -> DbFile:
        if isinstance(attachable, UploadFile):
            attachable, original_filename = attachable.file, attachable.filename
        return super().attach(
            attachable,
            content_type,   # type: ignore
            original_filename,   # type: ignore
            extension,  # type: ignore
            store_id,   # type: ignore
            overwrite,
            suppress_pre_process,
            suppress_validation,
            **kwargs,
        )

    @classmethod
    def create_from(cls, *args, **kwargs) -> DbFile:
        return cast(DbFile, super().create_from(*args, **kwargs))
    
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
                name = value.original_filename if value.original_filename is not None else ""
                return cls(name=name)
            else:
                raise TypeError

DbFile.associate_with(Json)


P = ParamSpec("P")
T = TypeVar("T")
def with_store_manager(func: Callable[Concatenate[Any, Session, P], T]) -> Callable[Concatenate[Any, Session, P], T]:
    def inner(obj, db: Session, *args: P.args, **kwargs: P.kwargs) -> T:
        with StoreManager(db):
            return func(obj, db, *args, **kwargs)
    return inner


@dataclass
class BaseNoID(MappedAsDataclass, DeclarativeBase):
    registry = registry(
        type_annotation_map={
            UUID: UUIDType,
            datetime: DateTime,
            DbFile: Json,
        }
    )

    db: InitVar[Session]

    def __post_init__(self, db: Session) -> None:
        db.add(self)

    class Schema(BaseSchema, ABC):
        pass

    @classmethod
    @property
    def __tablename__(cls):
        return cls.__name__.lower() + "s"

    def delete(self, db: Session):
        db.delete(self)
        db.commit()

    def encode(self) -> dict[str, Any]:
        return jsonable_encoder(self.Schema.from_orm(self))

    @classmethod
    def get_all(cls: Type[T], db: Session) -> Sequence[T]:
        """Get all database entries of this type."""
        return db.scalars(select(cls)).unique().all()

    def as_schema(self) -> Any:
        """Converts the database object into a pydantic schema."""
        return self.Schema.from_orm(self)


class Base(BaseNoID, unsafe_hash=True):
    __abstract__ = True
    id: Mapped[ID] = mapped_column(default_factory=uuid4, primary_key=True, init=False)

    class Schema(BaseNoID.Schema, ABC):
        id: ID

    @classmethod
    def get(cls: Type[T], db: Session, identifier: ID) -> T | None:
        """Queries the database for the object with the given id."""
        return db.query(cls).filter(cls.id == identifier).first()   # type: ignore

class WithFiles(Base):
    __abstract__ = True

    def delete(self, db: Session):
        with StoreManager(db):
            return super().delete(db)
