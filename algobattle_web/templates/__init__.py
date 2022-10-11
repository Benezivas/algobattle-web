from __future__ import annotations
from pathlib import Path
from typing import Any, Awaitable, Callable, Concatenate, ParamSpec, Tuple, TypeVar
from fastapi import Request, Response, Depends
from fastapi.templating import Jinja2Templates
from inspect import Parameter, Signature, get_annotations, signature

from algobattle_web.models.user import User, curr_user

templates = Jinja2Templates(directory=Path(__file__).parent)


P = ParamSpec("P")
def templated(fn: Callable[P, Awaitable[Tuple[str, dict[str, Any]] | str]]) -> Callable[Concatenate[Request, User, P], Awaitable[Response]]:
    """Adds the `request: Request` and `user: User = Depends(curr_user)` parameters and passes them to the context of the tempalte."""
    async def inner(request: Request, user: User, *args: P.args, **kwargs: P.kwargs) -> Response:
        ret = await fn(*args, **kwargs)
        if isinstance(ret, tuple):
            template_file, context = ret
        else:
            template_file, context = ret, {}

        new_context: dict[str, Any] = {"request": request, "user": user}
        return templates.TemplateResponse(template_file, new_context | context)

    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name]) for p in signature(fn).parameters.values()]
    new_parameters = []
    if "request" not in annotations:
        new_parameters.append(Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request))
    if "user" not in annotations:
        new_parameters.append(Parameter("user", Parameter.POSITIONAL_OR_KEYWORD, annotation=User, default=Depends(curr_user)))
    inner.__signature__ = Signature(
        parameters = [*new_parameters, *parameters],
        return_annotation = signature(inner).return_annotation,
    )

    return inner

def templated_sync(fn: Callable[P, Tuple[str, dict[str, Any]] | str]) -> Callable[Concatenate[Request, P], Response]:
    def inner(request: Request, *args: P.args, **kwargs: P.kwargs):
        ret = fn(*args, **kwargs)
        if isinstance(ret, tuple):
            template_file, context = ret
        else:
            template_file, context = ret, {}

        new_context: dict[str, Any] = {"request": request}
        if "user" in kwargs:
            new_context["user"] = kwargs["user"]
            
        return templates.TemplateResponse(template_file, new_context | context)

    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name]) for p in signature(fn).parameters.values()]
    inner.__signature__ = Signature(
        parameters = [
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            *parameters,
        ],
        return_annotation = signature(inner).return_annotation,
    )

    return inner

def _make_template(request: Request, user: User, ret: Tuple[str, dict[str, Any]] | str) -> Response:
    if isinstance(ret, tuple):
        template_file, context = ret
    else:
        template_file, context = ret, {}

    new_context: dict[str, Any] = {"request": request, "user": user}
    return templates.TemplateResponse(template_file, new_context | context)

T = TypeVar("T")
R = TypeVar("R")
U = TypeVar("U")
V = TypeVar("V")
def _fix_signature(inner: Callable[[T], R], fn: Callable[[T], R]) -> Callable[[T], R]:
    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name]) for p in signature(fn).parameters.values()]
    new_parameters = []
    if "request" not in annotations:
        new_parameters.append(Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request))
    if "user" not in annotations:
        new_parameters.append(Parameter("user", Parameter.POSITIONAL_OR_KEYWORD, annotation=User, default=Depends(curr_user)))
    inner.__signature__ = Signature(
        parameters = [*new_parameters, *parameters],
        return_annotation = signature(inner).return_annotation,
    )

    return inner



