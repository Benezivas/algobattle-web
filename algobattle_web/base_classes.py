"""Module for base classes that can be imported everywhere else."""
from __future__ import annotations
from inspect import Parameter, Signature, signature
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from fastapi import UploadFile, File, Form


class NoEdit:
    def __eq__(self, o: object) -> bool:
        return isinstance(o, NoEdit)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, val: Any):
        if isinstance(val, NoEdit):
            return val
        elif val == "__NO_EDIT__":
            return NoEdit()
        else:
            raise TypeError


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


class ObjID(UUID):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, obj: Any) -> UUID:
        if isinstance(obj, UUID):
            return obj
        elif hasattr(obj, "id"):
            if isinstance(obj.id, UUID):
                return obj.id
            else:
                raise ValueError
        else:
            raise TypeError

    def __repr__(self) -> str:
        return f"ObjID({super().__repr__()})"
