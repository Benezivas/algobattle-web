"""Module for base classes that can be imported everywhere else."""
from __future__ import annotations
from abc import ABC
from inspect import Parameter, Signature, signature
from typing import Any
from uuid import UUID
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column as SqlColumn
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_utils import UUIDType
from fastapi import UploadFile, File, Form
from fastapi.encoders import jsonable_encoder


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True

    @classmethod
    def from_form(cls):
        """Constructs a a function that can be used as a dependency for parsing this schema from form data."""

        def builder(**kwargs):
            return cls(**kwargs)

        new_sig = []
        for param in signature(cls).parameters.values():
            default = param.default if param.default is not Parameter.empty else None
            getter = File if param.annotation == UploadFile else Form
            new_sig.append(
                Parameter(
                    param.name, Parameter.POSITIONAL_OR_KEYWORD, annotation=param.annotation, default=getter(default=default)
                )
            )

        builder.__signature__ = Signature(new_sig)
        return builder


def Column(*args, **kwargs) -> Any:
    return SqlColumn(*args, **kwargs)


class Common:
    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)

    class Schema(BaseSchema, ABC):
        id: UUID

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    @classmethod
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + "s"

    def delete(self, db: Session):
        db.delete(self)
        db.commit()

    def encode(self) -> dict[str, Any]:
        return jsonable_encoder(self.Schema.from_orm(self))


class DbBase(Common):
    metadata: Any


class ObjID(UUID):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, obj: Any) -> UUID:
        if isinstance(obj, UUID):
            return obj
        elif isinstance(obj, (BaseSchema, Common)) and hasattr(obj, "id"):
            assert hasattr(obj, "id")
            if isinstance(obj.id, UUID):  # type: ignore
                return obj.id  # type: ignore
            else:
                raise ValueError
        else:
            raise TypeError

    def __repr__(self) -> str:
        return f"ObjID({super().__repr__()})"
