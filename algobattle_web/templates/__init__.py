from __future__ import annotations
from pathlib import Path
from typing import Any, Awaitable, Callable, Concatenate, ParamSpec, Tuple, TypeVar
from fastapi import Request, Response, Depends
from fastapi.templating import Jinja2Templates
from inspect import Parameter, Signature, get_annotations, signature

from algobattle_web.models.user import User, curr_user

templates = Jinja2Templates(directory=Path(__file__).parent)


P = ParamSpec("P")
R = ParamSpec("R")
S = TypeVar("S")

def templated(fn: Callable[P, Awaitable[Tuple[str, dict[str, Any]] | str]]) -> Callable[Concatenate[Request, User, P], Awaitable[Response]]:
    """Adds the `request: Request` and `user: User = Depends(curr_user)` parameters and passes them to the context of the template."""
    async def inner(request: Request, user: User, *args: P.args, **kwargs: P.kwargs) -> Response:
        ret = await fn(*args, **kwargs)
        return _make_template(request, user, ret)

    return _fix_signature(inner, fn)

def templated_sync(fn: Callable[P, Tuple[str, dict[str, Any]] | str]) -> Callable[Concatenate[Request, User, P], Response]:
    """Adds the `request: Request` and `user: User = Depends(curr_user)` parameters and passes them to the context of the template."""
    def inner(request: Request, user: User, *args: P.args, **kwargs: P.kwargs) -> Response:
        ret = fn(*args, **kwargs)
        return _make_template(request, user, ret)

    return _fix_signature(inner, fn)

def _make_template(request: Request, user: User, ret: Tuple[str, dict[str, Any]] | str) -> Response:
    if isinstance(ret, tuple):
        template_file, context = ret
    else:
        template_file, context = ret, {}

    new_context: dict[str, Any] = {"request": request, "user": user}
    return templates.TemplateResponse(template_file, new_context | context)

def _fix_signature(inner: Callable[P, S], fn: Callable[R, Any]) -> Callable[P, S]:
    # we need to get the annotations as actual objects and not strings,
    # get_annotations will eval all annotated ones but misses args that aren't annotated
    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name]) for p in signature(fn).parameters.values()]

    # add new parameters if they aren't already present
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



