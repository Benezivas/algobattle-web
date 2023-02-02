"""Util functions."""
from typing import Any, Never, Self, TypeGuard, TypeVar
from inspect import Parameter, Signature, signature
from uuid import UUID

from pydantic import BaseModel
from fastapi import UploadFile, File, Form


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True

    @classmethod
    def from_form(cls: type[Self]):
        """Constructs a a function that can be used as a dependency for parsing this schema from form data."""

        def builder(**kwargs) -> Self:
            return cls(**{key: val for key, val in kwargs.items() if present(val)})

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


class Missing(BaseSchema):
    """Marker class for fields that weren't present in the parsed json."""

    @classmethod
    def __get_validators__(cls):
        yield cls._validate

    @classmethod
    def _validate(cls, obj: Any) -> Never:
        raise ValueError


missing = Missing()


T = TypeVar("T")
def present(_obj: T | Missing) -> TypeGuard[T]:
    return not isinstance(_obj, Missing)


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
        elif isinstance(obj, str):
            return UUID(obj)
        else:
            raise TypeError

    def __repr__(self) -> str:
        return f"ObjID({super().__repr__()})"

def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")



T = TypeVar("T")
def unwrap(arg: T | None) -> T:
    """Returns the argument if it is not `None`, otherwise raises an exception."""
    if arg is None:
        raise ValueError
    else:
        return arg
